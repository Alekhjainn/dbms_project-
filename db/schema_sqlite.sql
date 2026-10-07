-- db/schema_sqlite.sql

PRAGMA foreign_keys = ON;

CREATE TABLE Loan_Policy (
    member_type TEXT PRIMARY KEY CHECK(member_type IN ('Student', 'Faculty', 'Staff')),
    max_books INTEGER NOT NULL CHECK(max_books > 0),
    loan_days INTEGER NOT NULL CHECK(loan_days > 0),
    fine_per_day REAL NOT NULL CHECK(fine_per_day >= 0)
);

CREATE TABLE Member (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    member_type TEXT NOT NULL,
    join_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Suspended')),
    FOREIGN KEY(member_type) REFERENCES Loan_Policy(member_type) ON UPDATE CASCADE
);

CREATE TABLE Publisher (
    publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT
);

CREATE TABLE Author (
    author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bio TEXT
);

CREATE TABLE Category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE Book (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT
);

CREATE TABLE Edition (
    edition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    publisher_id INTEGER NOT NULL,
    edition_no INTEGER NOT NULL,
    publication_year INTEGER NOT NULL,
    isbn TEXT UNIQUE NOT NULL,
    FOREIGN KEY(book_id) REFERENCES Book(book_id) ON DELETE CASCADE,
    FOREIGN KEY(publisher_id) REFERENCES Publisher(publisher_id) ON DELETE CASCADE
);

CREATE TABLE Book_Author (
    book_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    PRIMARY KEY(book_id, author_id),
    FOREIGN KEY(book_id) REFERENCES Book(book_id) ON DELETE CASCADE,
    FOREIGN KEY(author_id) REFERENCES Author(author_id) ON DELETE CASCADE
);

CREATE TABLE Book_Category (
    book_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY(book_id, category_id),
    FOREIGN KEY(book_id) REFERENCES Book(book_id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES Category(category_id) ON DELETE CASCADE
);

CREATE TABLE Copy (
    copy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id INTEGER NOT NULL,
    accession_no TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Issued', 'Reserved', 'Lost', 'Withdrawn')),
    shelf_location TEXT,
    FOREIGN KEY(edition_id) REFERENCES Edition(edition_id) ON DELETE CASCADE
);

CREATE TABLE Issue (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    CHECK(due_date >= issue_date),
    CHECK(return_date IS NULL OR return_date >= issue_date),
    FOREIGN KEY(copy_id) REFERENCES Copy(copy_id) ON DELETE RESTRICT,
    FOREIGN KEY(member_id) REFERENCES Member(member_id) ON DELETE RESTRICT
);

-- Ensure only one active issue per copy
CREATE UNIQUE INDEX idx_issue_active_copy ON Issue(copy_id) WHERE return_date IS NULL;

CREATE TABLE Reservation (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    reserved_on DATE NOT NULL,
    queue_position INTEGER NOT NULL CHECK(queue_position > 0),
    status TEXT NOT NULL DEFAULT 'Waiting' CHECK(status IN ('Waiting', 'Fulfilled', 'Cancelled', 'Expired')),
    FOREIGN KEY(edition_id) REFERENCES Edition(edition_id) ON DELETE CASCADE,
    FOREIGN KEY(member_id) REFERENCES Member(member_id) ON DELETE CASCADE
);

-- Enforce unique queue position per edition among waiting reservations
CREATE UNIQUE INDEX idx_reservation_queue ON Reservation(edition_id, queue_position) WHERE status = 'Waiting';

CREATE TABLE Fine (
    fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    paid_flag INTEGER NOT NULL DEFAULT 0 CHECK(paid_flag IN (0, 1)),
    paid_date DATE,
    FOREIGN KEY(issue_id) REFERENCES Issue(issue_id) ON DELETE CASCADE
);

CREATE TABLE Digital_Resource (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url_or_path TEXT NOT NULL,
    license_type TEXT NOT NULL
);

CREATE TABLE Digital_Access_Log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    access_time DATETIME NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('View', 'Download')),
    FOREIGN KEY(member_id) REFERENCES Member(member_id) ON DELETE CASCADE,
    FOREIGN KEY(resource_id) REFERENCES Digital_Resource(resource_id) ON DELETE CASCADE
);

CREATE TABLE Staff_User (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Admin', 'Librarian'))
);

-- Indexes for frequently searched columns
CREATE INDEX idx_book_title ON Book(title);
CREATE INDEX idx_author_name ON Author(name);
CREATE INDEX idx_edition_isbn ON Edition(isbn);
CREATE INDEX idx_copy_accession ON Copy(accession_no);
CREATE INDEX idx_member_name ON Member(name);
CREATE INDEX idx_member_email ON Member(email);
CREATE INDEX idx_issue_member ON Issue(member_id);
CREATE INDEX idx_issue_return_date ON Issue(return_date);
CREATE INDEX idx_reservation_edition ON Reservation(edition_id);

-- TRIGGERS

-- 1. Block issuing if copy is not Available
CREATE TRIGGER trg_issue_check_available
BEFORE INSERT ON Issue
FOR EACH ROW
WHEN (SELECT status FROM Copy WHERE copy_id = NEW.copy_id) != 'Available'
BEGIN
    SELECT RAISE(ABORT, 'Copy is not available for issue');
END;

-- 2. Block issuing if member is suspended or has high unpaid fines (threshold = 100) or borrowing limit reached
CREATE TRIGGER trg_issue_check_member
BEFORE INSERT ON Issue
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Member is suspended')
    WHERE (SELECT status FROM Member WHERE member_id = NEW.member_id) = 'Suspended';
    
    SELECT RAISE(ABORT, 'Member has unpaid fines exceeding threshold')
    WHERE (
        SELECT COALESCE(SUM(amount), 0) FROM Fine f 
        JOIN Issue i ON f.issue_id = i.issue_id 
        WHERE i.member_id = NEW.member_id AND f.paid_flag = 0
    ) > 100;
    
    SELECT RAISE(ABORT, 'Member reached maximum borrowing limit')
    WHERE (
        SELECT COUNT(*) FROM Issue WHERE member_id = NEW.member_id AND return_date IS NULL
    ) >= (
        SELECT lp.max_books FROM Loan_Policy lp 
        JOIN Member m ON m.member_type = lp.member_type 
        WHERE m.member_id = NEW.member_id
    );
END;

-- 3. Update copy status to Issued after issue
CREATE TRIGGER trg_issue_update_copy
AFTER INSERT ON Issue
FOR EACH ROW
BEGIN
    UPDATE Copy SET status = 'Issued' WHERE copy_id = NEW.copy_id;
END;

-- 4. On return, update copy status, check reservations, calculate fine
CREATE TRIGGER trg_return_update_copy_and_fine
AFTER UPDATE OF return_date ON Issue
FOR EACH ROW
WHEN NEW.return_date IS NOT NULL AND OLD.return_date IS NULL
BEGIN
    -- Determine if there is a waiting reservation for the same edition
    UPDATE Copy SET status = 
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM Reservation r 
                WHERE r.edition_id = (SELECT edition_id FROM Copy WHERE copy_id = NEW.copy_id) 
                AND r.status = 'Waiting'
            ) THEN 'Reserved'
            ELSE 'Available'
        END
    WHERE copy_id = NEW.copy_id;
    
    -- Calculate fine if overdue (due_date and return_date are YYYY-MM-DD strings in SQLite typically)
    INSERT INTO Fine (issue_id, amount, paid_flag)
    SELECT NEW.issue_id, 
           CAST(julianday(NEW.return_date) - julianday(NEW.due_date) AS INTEGER) * lp.fine_per_day,
           0
    FROM Member m
    JOIN Loan_Policy lp ON m.member_type = lp.member_type
    WHERE m.member_id = NEW.member_id 
    AND julianday(NEW.return_date) > julianday(NEW.due_date);
END;

-- 5. Compact queue positions after reservation is no longer 'Waiting'
CREATE TRIGGER trg_reservation_compact
AFTER UPDATE OF status ON Reservation
FOR EACH ROW
WHEN OLD.status = 'Waiting' AND NEW.status != 'Waiting'
BEGIN
    UPDATE Reservation
    SET queue_position = queue_position - 1
    WHERE edition_id = NEW.edition_id AND status = 'Waiting' AND queue_position > OLD.queue_position;
END;

-- 6. Assign queue_position on new Reservation if not provided correctly
-- In SQLite BEFORE INSERT we can't easily modify NEW.queue_position using subquery, 
-- so we rely on the application to insert the correct next queue_position.
-- However, we can enforce it using a trigger that aborts if wrong.
CREATE TRIGGER trg_reservation_queue_check
BEFORE INSERT ON Reservation
FOR EACH ROW
WHEN NEW.status = 'Waiting' AND NEW.queue_position != (
    SELECT COALESCE(MAX(queue_position), 0) + 1 FROM Reservation 
    WHERE edition_id = NEW.edition_id AND status = 'Waiting'
)
BEGIN
    SELECT RAISE(ABORT, 'Invalid queue position for reservation');
END;
