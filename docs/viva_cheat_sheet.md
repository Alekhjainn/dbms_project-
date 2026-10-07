# Viva Cheat Sheet

1. **What is a Primary Key?** A column/set of columns uniquely identifying a record.
2. **What is a Foreign Key?** A column linking to a Primary Key in another table, ensuring referential integrity.
3. **What is Normalization?** Process of organizing data to reduce redundancy and improve integrity (1NF, 2NF, 3NF).
4. **How did you enforce one active issue per copy?** Using a partial unique index: `UNIQUE INDEX ON Issue(copy_id) WHERE return_date IS NULL`.
5. **What is a Trigger?** A stored procedure that automatically executes when an event (INSERT, UPDATE, DELETE) occurs.
6. **Where are triggers used here?** To auto-update copy status (Issued/Available), calculate fines on return, block issues for suspended members, and compact reservation queues.
7. **What is the difference between INNER and LEFT JOIN?** INNER returns only matches; LEFT returns all records from the left table and matched records from the right.
8. **Explain the fine calculation query.** It's handled in a trigger: dates are subtracted (`julianday` in SQLite) and multiplied by `fine_per_day` from the `Loan_Policy` table.
9. **Why use parameterized queries in Python?** To prevent SQL Injection attacks.
10. **What is a View?** A virtual table based on the result-set of an SQL statement. We used views for reports like `v_available_titles`.
11. **How do you handle transactions?** Using `with conn:` in Python or explicit `conn.commit()` so if an error occurs mid-operation, partial writes are rolled back.
12. **Why separate Author and Book_Author?** Because of the Many-to-Many relationship between books and authors.
13. **What is an Index and why use it?** An index speeds up data retrieval. I added indexes on frequently searched columns like `title`, `isbn`, and `member_email`.
14. **How do you verify your DB is in 3NF?** By ensuring every non-key column is directly dependent only on the primary key, eliminating transitive dependencies (like extracting `Loan_Policy`).
15. **What happens if a member reserves a book that is returned?** The return trigger checks `Reservation` and sets the `Copy` status to `Reserved` instead of `Available`.
