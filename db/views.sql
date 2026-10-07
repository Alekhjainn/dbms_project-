-- db/views.sql

-- 1. Available titles
CREATE VIEW v_available_titles AS
SELECT b.title, e.isbn, e.edition_no, COUNT(c.copy_id) AS available_copies
FROM Book b
JOIN Edition e ON b.book_id = e.book_id
JOIN Copy c ON e.edition_id = c.edition_id
WHERE c.status = 'Available'
GROUP BY b.title, e.isbn, e.edition_no;

-- 2. Overdue copies
CREATE VIEW v_overdue_copies AS
SELECT 
    i.issue_id, c.accession_no, b.title, m.name AS member_name, m.email,
    i.issue_date, i.due_date,
    CAST(julianday(date('now')) - julianday(i.due_date) AS INTEGER) AS days_overdue
FROM Issue i
JOIN Copy c ON i.copy_id = c.copy_id
JOIN Edition e ON c.edition_id = e.edition_id
JOIN Book b ON e.book_id = b.book_id
JOIN Member m ON i.member_id = m.member_id
WHERE i.return_date IS NULL AND date('now') > i.due_date;

-- 3. Member borrowing history
CREATE VIEW v_member_history AS
SELECT 
    m.member_id, m.name, b.title, c.accession_no, 
    i.issue_date, i.due_date, i.return_date
FROM Member m
JOIN Issue i ON m.member_id = i.member_id
JOIN Copy c ON i.copy_id = c.copy_id
JOIN Edition e ON c.edition_id = e.edition_id
JOIN Book b ON e.book_id = b.book_id
ORDER BY m.member_id, i.issue_date DESC;

-- 4. Popular books (to be used with LIMIT 10 in query)
CREATE VIEW v_popular_books AS
SELECT 
    b.book_id, b.title, COUNT(i.issue_id) AS issue_count
FROM Book b
JOIN Edition e ON b.book_id = e.book_id
JOIN Copy c ON e.edition_id = c.edition_id
JOIN Issue i ON c.copy_id = i.copy_id
GROUP BY b.book_id, b.title
ORDER BY issue_count DESC;

-- 5. Reservation queue
CREATE VIEW v_reservation_queue AS
SELECT 
    r.reservation_id, b.title, e.isbn, m.name AS member_name, 
    r.reserved_on, r.queue_position
FROM Reservation r
JOIN Edition e ON r.edition_id = e.edition_id
JOIN Book b ON e.book_id = b.book_id
JOIN Member m ON r.member_id = m.member_id
WHERE r.status = 'Waiting'
ORDER BY e.edition_id, r.queue_position;

-- 6. Fine summary (total collected, outstanding per member)
CREATE VIEW v_fine_summary AS
SELECT 
    m.member_id, m.name,
    SUM(CASE WHEN f.paid_flag = 1 THEN f.amount ELSE 0 END) AS total_collected,
    SUM(CASE WHEN f.paid_flag = 0 THEN f.amount ELSE 0 END) AS outstanding_balance
FROM Member m
JOIN Issue i ON m.member_id = i.member_id
JOIN Fine f ON i.issue_id = f.issue_id
GROUP BY m.member_id, m.name;
