-- db/schema_postgres.sql

CREATE TABLE Loan_Policy (
    member_type VARCHAR(50) PRIMARY KEY CHECK(member_type IN ('Student', 'Faculty', 'Staff')),
    max_books INT NOT NULL CHECK(max_books > 0),
    loan_days INT NOT NULL CHECK(loan_days > 0),
    fine_per_day NUMERIC(10,2) NOT NULL CHECK(fine_per_day >= 0)
);

CREATE TABLE Member (
    member_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    member_type VARCHAR(50) NOT NULL,
    join_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Suspended')),
    FOREIGN KEY(member_type) REFERENCES Loan_Policy(member_type) ON UPDATE CASCADE
);

CREATE TABLE Publisher (
    publisher_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact VARCHAR(255)
);

CREATE TABLE Author (
    author_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    bio TEXT
);

CREATE TABLE Category (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE Book (
    book_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE Edition (
    edition_id SERIAL PRIMARY KEY,
    book_id INT NOT NULL,
    publisher_id INT NOT NULL,
    edition_no INT NOT NULL,
    publication_year INT NOT NULL,
    isbn VARCHAR(50) UNIQUE NOT NULL,
    FOREIGN KEY(book_id) REFERENCES Book(book_id) ON DELETE CASCADE,
    FOREIGN KEY(publisher_id) REFERENCES Publisher(publisher_id) ON DELETE CASCADE
);

CREATE TABLE Book_Author (
    book_id INT NOT NULL,
    author_id INT NOT NULL,
    PRIMARY KEY(book_id, author_id),
    FOREIGN KEY(book_id) REFERENCES Book(book_id) ON DELETE CASCADE,
    FOREIGN KEY(author_id) REFERENCES Author(author_id) ON DELETE CASCADE
);

CREATE TABLE Book_Category (
    book_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY(book_id, category_id),
    FOREIGN KEY(book_id) REFERENCES Book(book_id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES Category(category_id) ON DELETE CASCADE
);

CREATE TABLE Copy (
    copy_id SERIAL PRIMARY KEY,
    edition_id INT NOT NULL,
    accession_no VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Issued', 'Reserved', 'Lost', 'Withdrawn')),
    shelf_location VARCHAR(100),
    FOREIGN KEY(edition_id) REFERENCES Edition(edition_id) ON DELETE CASCADE
);

CREATE TABLE Issue (
    issue_id SERIAL PRIMARY KEY,
    copy_id INT NOT NULL,
    member_id INT NOT NULL,
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
    reservation_id SERIAL PRIMARY KEY,
    edition_id INT NOT NULL,
    member_id INT NOT NULL,
    reserved_on DATE NOT NULL,
    queue_position INT NOT NULL CHECK(queue_position > 0),
    status VARCHAR(50) NOT NULL DEFAULT 'Waiting' CHECK(status IN ('Waiting', 'Fulfilled', 'Cancelled', 'Expired')),
    FOREIGN KEY(edition_id) REFERENCES Edition(edition_id) ON DELETE CASCADE,
    FOREIGN KEY(member_id) REFERENCES Member(member_id) ON DELETE CASCADE
);

-- Enforce unique queue position per edition among waiting reservations
CREATE UNIQUE INDEX idx_reservation_queue ON Reservation(edition_id, queue_position) WHERE status = 'Waiting';

CREATE TABLE Fine (
    fine_id SERIAL PRIMARY KEY,
    issue_id INT NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK(amount >= 0),
    paid_flag INT NOT NULL DEFAULT 0 CHECK(paid_flag IN (0, 1)),
    paid_date DATE,
    FOREIGN KEY(issue_id) REFERENCES Issue(issue_id) ON DELETE CASCADE
);

CREATE TABLE Digital_Resource (
    resource_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    url_or_path TEXT NOT NULL,
    license_type VARCHAR(100) NOT NULL
);

CREATE TABLE Digital_Access_Log (
    log_id SERIAL PRIMARY KEY,
    member_id INT NOT NULL,
    resource_id INT NOT NULL,
    access_time TIMESTAMP NOT NULL,
    action VARCHAR(50) NOT NULL CHECK(action IN ('View', 'Download')),
    FOREIGN KEY(member_id) REFERENCES Member(member_id) ON DELETE CASCADE,
    FOREIGN KEY(resource_id) REFERENCES Digital_Resource(resource_id) ON DELETE CASCADE
);

CREATE TABLE Staff_User (
    username VARCHAR(100) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK(role IN ('Admin', 'Librarian'))
);

-- Indexes
CREATE INDEX idx_book_title ON Book(title);
CREATE INDEX idx_author_name ON Author(name);
CREATE INDEX idx_edition_isbn ON Edition(isbn);
CREATE INDEX idx_copy_accession ON Copy(accession_no);
CREATE INDEX idx_member_name ON Member(name);
CREATE INDEX idx_member_email ON Member(email);
CREATE INDEX idx_issue_member ON Issue(member_id);
CREATE INDEX idx_issue_return_date ON Issue(return_date);
CREATE INDEX idx_reservation_edition ON Reservation(edition_id);

-- TRIGGER FUNCTIONS AND TRIGGERS

CREATE OR REPLACE FUNCTION check_issue_conditions() RETURNS TRIGGER AS $$
DECLARE
    copy_status VARCHAR(50);
    mem_status VARCHAR(50);
    unpaid_fines NUMERIC;
    active_issues INT;
    m_max_books INT;
BEGIN
    SELECT status INTO copy_status FROM Copy WHERE copy_id = NEW.copy_id;
    IF copy_status != 'Available' THEN
        RAISE EXCEPTION 'Copy is not available for issue';
    END IF;

    SELECT status INTO mem_status FROM Member WHERE member_id = NEW.member_id;
    IF mem_status = 'Suspended' THEN
        RAISE EXCEPTION 'Member is suspended';
    END IF;

    SELECT COALESCE(SUM(amount), 0) INTO unpaid_fines FROM Fine f 
    JOIN Issue i ON f.issue_id = i.issue_id 
    WHERE i.member_id = NEW.member_id AND f.paid_flag = 0;
    IF unpaid_fines > 100 THEN
        RAISE EXCEPTION 'Member has unpaid fines exceeding threshold';
    END IF;

    SELECT COUNT(*) INTO active_issues FROM Issue WHERE member_id = NEW.member_id AND return_date IS NULL;
    SELECT lp.max_books INTO m_max_books FROM Loan_Policy lp JOIN Member m ON m.member_type = lp.member_type WHERE m.member_id = NEW.member_id;
    IF active_issues >= m_max_books THEN
        RAISE EXCEPTION 'Member reached maximum borrowing limit';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_issue_check_conditions
BEFORE INSERT ON Issue
FOR EACH ROW EXECUTE FUNCTION check_issue_conditions();

CREATE OR REPLACE FUNCTION update_copy_on_issue() RETURNS TRIGGER AS $$
BEGIN
    UPDATE Copy SET status = 'Issued' WHERE copy_id = NEW.copy_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_issue_update_copy
AFTER INSERT ON Issue
FOR EACH ROW EXECUTE FUNCTION update_copy_on_issue();

CREATE OR REPLACE FUNCTION update_on_return() RETURNS TRIGGER AS $$
DECLARE
    fine_amt NUMERIC;
    f_per_day NUMERIC;
    has_reservation BOOLEAN;
BEGIN
    IF NEW.return_date IS NOT NULL AND OLD.return_date IS NULL THEN
        SELECT EXISTS (
            SELECT 1 FROM Reservation r 
            WHERE r.edition_id = (SELECT edition_id FROM Copy WHERE copy_id = NEW.copy_id) 
            AND r.status = 'Waiting'
        ) INTO has_reservation;
        
        IF has_reservation THEN
            UPDATE Copy SET status = 'Reserved' WHERE copy_id = NEW.copy_id;
        ELSE
            UPDATE Copy SET status = 'Available' WHERE copy_id = NEW.copy_id;
        END IF;

        IF NEW.return_date > NEW.due_date THEN
            SELECT lp.fine_per_day INTO f_per_day FROM Loan_Policy lp JOIN Member m ON m.member_type = lp.member_type WHERE m.member_id = NEW.member_id;
            fine_amt := (NEW.return_date - NEW.due_date) * f_per_day;
            INSERT INTO Fine (issue_id, amount, paid_flag) VALUES (NEW.issue_id, fine_amt, 0);
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_return_update_copy_and_fine
AFTER UPDATE OF return_date ON Issue
FOR EACH ROW EXECUTE FUNCTION update_on_return();

CREATE OR REPLACE FUNCTION compact_reservation_queue() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'Waiting' AND NEW.status != 'Waiting' THEN
        UPDATE Reservation
        SET queue_position = queue_position - 1
        WHERE edition_id = NEW.edition_id AND status = 'Waiting' AND queue_position > OLD.queue_position;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reservation_compact
AFTER UPDATE OF status ON Reservation
FOR EACH ROW EXECUTE FUNCTION compact_reservation_queue();

CREATE OR REPLACE FUNCTION check_reservation_queue_pos() RETURNS TRIGGER AS $$
DECLARE
    expected_pos INT;
BEGIN
    IF NEW.status = 'Waiting' THEN
        SELECT COALESCE(MAX(queue_position), 0) + 1 INTO expected_pos FROM Reservation WHERE edition_id = NEW.edition_id AND status = 'Waiting';
        IF NEW.queue_position != expected_pos THEN
            RAISE EXCEPTION 'Invalid queue position for reservation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reservation_queue_check
BEFORE INSERT ON Reservation
FOR EACH ROW EXECUTE FUNCTION check_reservation_queue_pos();
