-- db/queries.sql

-- 1. Available titles (INNER JOIN, GROUP BY, COUNT)
-- Demonstrates aggregation and multi-table joins.
SELECT b.title, e.isbn, e.edition_no, COUNT(c.copy_id) AS available_copies
FROM Book b
INNER JOIN Edition e ON b.book_id = e.book_id
INNER JOIN Copy c ON e.edition_id = c.edition_id
WHERE c.status = 'Available'
GROUP BY b.title, e.isbn, e.edition_no;

-- 2. Overdue copies with member and days overdue (INNER JOIN, Date math)
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

-- 3. Member borrowing history (LEFT JOIN)
-- Demonstrates LEFT JOIN in case we want members with no history (though here it's an inner join, let's make it LEFT)
SELECT 
    m.name, m.email, b.title, c.accession_no, 
    i.issue_date, i.due_date, i.return_date
FROM Member m
LEFT JOIN Issue i ON m.member_id = i.member_id
LEFT JOIN Copy c ON i.copy_id = c.copy_id
LEFT JOIN Edition e ON c.edition_id = e.edition_id
LEFT JOIN Book b ON e.book_id = b.book_id
ORDER BY m.name, i.issue_date DESC;

-- 4. Most popular books (top 10) (GROUP BY, Aggregate, LIMIT)
SELECT 
    b.title, COUNT(i.issue_id) AS total_issues
FROM Book b
JOIN Edition e ON b.book_id = e.book_id
JOIN Copy c ON e.edition_id = c.edition_id
JOIN Issue i ON c.copy_id = i.copy_id
GROUP BY b.book_id, b.title
ORDER BY total_issues DESC
LIMIT 10;

-- 5. Active reservations by queue order (INNER JOIN)
SELECT 
    b.title, e.isbn, m.name, r.reserved_on, r.queue_position
FROM Reservation r
JOIN Edition e ON r.edition_id = e.edition_id
JOIN Book b ON e.book_id = b.book_id
JOIN Member m ON r.member_id = m.member_id
WHERE r.status = 'Waiting'
ORDER BY e.edition_id, r.queue_position;

-- 6. Fine collection - Total collected and outstanding per month (GROUP BY, SUM)
SELECT 
    strftime('%Y-%m', f.paid_date) AS month,
    SUM(CASE WHEN f.paid_flag = 1 THEN f.amount ELSE 0 END) AS collected,
    SUM(CASE WHEN f.paid_flag = 0 THEN f.amount ELSE 0 END) AS outstanding
FROM Fine f
GROUP BY strftime('%Y-%m', f.paid_date);

-- 7. Category-wise circulation (GROUP BY, HAVING)
-- Demonstrates HAVING clause
SELECT 
    cat.name AS category_name, COUNT(i.issue_id) AS total_issues
FROM Category cat
JOIN Book_Category bc ON cat.category_id = bc.category_id
JOIN Edition e ON bc.book_id = e.book_id
JOIN Copy c ON e.edition_id = c.edition_id
JOIN Issue i ON c.copy_id = i.copy_id
GROUP BY cat.name
HAVING COUNT(i.issue_id) > 0
ORDER BY total_issues DESC;

-- 8. Digital resource usage ranking (Aggregate MAX/COUNT)
SELECT 
    dr.title, COUNT(log.log_id) AS total_accesses, MAX(log.access_time) AS last_accessed
FROM Digital_Resource dr
LEFT JOIN Digital_Access_Log log ON dr.resource_id = log.resource_id
GROUP BY dr.resource_id, dr.title
ORDER BY total_accesses DESC;

-- 9. Members with no activity (Correlated subquery / NOT EXISTS)
-- Demonstrates NOT EXISTS
SELECT m.name, m.email 
FROM Member m
WHERE NOT EXISTS (
    SELECT 1 FROM Issue i WHERE i.member_id = m.member_id
);

-- 10. Members with more than average fines (Nested Subquery)
-- Demonstrates nested subqueries
SELECT m.name, SUM(f.amount) as total_fine
FROM Member m
JOIN Issue i ON m.member_id = i.member_id
JOIN Fine f ON i.issue_id = f.issue_id
GROUP BY m.member_id, m.name
HAVING SUM(f.amount) > (
    SELECT AVG(total_fine) FROM (
        SELECT SUM(amount) as total_fine
        FROM Fine
        GROUP BY issue_id
    )
);

-- 11. Copies located on same shelf (Self Join)
-- Demonstrates self join
SELECT c1.accession_no AS copy1, c2.accession_no AS copy2, c1.shelf_location
FROM Copy c1
JOIN Copy c2 ON c1.shelf_location = c2.shelf_location 
AND c1.copy_id < c2.copy_id
WHERE c1.shelf_location IS NOT NULL;
