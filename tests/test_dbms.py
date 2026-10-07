import unittest
import sqlite3
import os
from datetime import datetime, timedelta

class TestLibraryDBMS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We will use an in-memory DB for tests, but SQLite constraints behave the same.
        # However, to test exact seed data triggers, let's build a clean file DB for tests.
        cls.db_path = 'test_library.db'
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
            
        cls.conn = sqlite3.connect(cls.db_path)
        cls.conn.execute('PRAGMA foreign_keys = ON')
        cls.conn.row_factory = sqlite3.Row
        
        # Apply schema
        with open('db/schema_sqlite.sql', 'r') as f:
            cls.conn.executescript(f.read())

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        # Clean up tables we modify
        tables = ['Fine', 'Reservation', 'Issue', 'Copy', 'Book_Category', 'Book_Author', 'Edition', 'Book', 'Member', 'Author', 'Publisher', 'Category', 'Loan_Policy']
        for t in tables:
            self.conn.execute(f"DELETE FROM {t}")
        self.conn.commit()
        
        self.conn.execute("INSERT INTO Loan_Policy (member_type, max_books, loan_days, fine_per_day) VALUES ('Student', 2, 14, 2.0)")
        self.conn.execute("INSERT INTO Publisher (publisher_id, name) VALUES (1, 'Test Pub')")
        self.conn.execute("INSERT INTO Book (book_id, title) VALUES (1, 'Test Book')")
        self.conn.execute("INSERT INTO Edition (edition_id, book_id, publisher_id, edition_no, publication_year, isbn) VALUES (1, 1, 1, 1, 2023, '123-456')")
        self.conn.execute("INSERT INTO Copy (copy_id, edition_id, accession_no, status) VALUES (1, 1, 'ACC-001', 'Available')")
        self.conn.execute("INSERT INTO Copy (copy_id, edition_id, accession_no, status) VALUES (2, 1, 'ACC-002', 'Available')")
        self.conn.execute("INSERT INTO Member (member_id, name, email, member_type, join_date, status) VALUES (1, 'Alice', 'a@a.com', 'Student', date('now'), 'Active')")
        self.conn.commit()

    def test_duplicate_isbn(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Edition (book_id, publisher_id, edition_no, publication_year, isbn) VALUES (1, 1, 2, 2024, '123-456')")

    def test_duplicate_accession(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Copy (edition_id, accession_no) VALUES (1, 'ACC-001')")

    def test_second_active_issue_same_copy(self):
        self.conn.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (1, 1, date('now'), date('now', '+14 days'))")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (1, 1, date('now'), date('now', '+14 days'))")

    def test_return_before_issue_date(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date, return_date) VALUES (1, 1, date('now'), date('now', '+14 days'), date('now', '-1 day'))")

    def test_negative_fine(self):
        self.conn.execute("INSERT INTO Issue (issue_id, copy_id, member_id, issue_date, due_date) VALUES (99, 1, 1, date('now'), date('now', '+14 days'))")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO Fine (issue_id, amount) VALUES (99, -5.0)")

    def test_borrowing_limit(self):
        # max 2 books
        self.conn.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (1, 1, date('now'), date('now', '+14 days'))")
        self.conn.execute("UPDATE Copy SET status = 'Available' WHERE copy_id=2")
        self.conn.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (2, 1, date('now'), date('now', '+14 days'))")
        
        # 3rd issue should fail via trigger
        self.conn.execute("INSERT INTO Copy (copy_id, edition_id, accession_no, status) VALUES (3, 1, 'ACC-003', 'Available')")
        with self.assertRaises(sqlite3.DatabaseError) as ctx:
            self.conn.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (3, 1, date('now'), date('now', '+14 days'))")
        self.assertIn("borrowing limit", str(ctx.exception))

    def test_fine_calculation(self):
        # issue 5 days ago, due 3 days ago -> 3 days late. fine = 3 * 2.0 = 6.0
        self.conn.execute("INSERT INTO Issue (issue_id, copy_id, member_id, issue_date, due_date) VALUES (10, 1, 1, date('now', '-5 days'), date('now', '-3 days'))")
        self.conn.commit()
        
        self.conn.execute("UPDATE Issue SET return_date = date('now') WHERE issue_id = 10")
        self.conn.commit()
        
        fine = self.conn.execute("SELECT amount FROM Fine WHERE issue_id = 10").fetchone()
        self.assertIsNotNone(fine)
        self.assertEqual(fine['amount'], 6.0)

    def test_reservation_queue_ordering_compaction(self):
        self.conn.execute("INSERT INTO Member (member_id, name, email, member_type, join_date) VALUES (2, 'Bob', 'b@b.com', 'Student', date('now'))")
        self.conn.execute("INSERT INTO Member (member_id, name, email, member_type, join_date) VALUES (3, 'Charlie', 'c@c.com', 'Student', date('now'))")
        
        self.conn.execute("INSERT INTO Reservation (reservation_id, edition_id, member_id, reserved_on, queue_position) VALUES (1, 1, 1, date('now'), 1)")
        self.conn.execute("INSERT INTO Reservation (reservation_id, edition_id, member_id, reserved_on, queue_position) VALUES (2, 1, 2, date('now'), 2)")
        self.conn.execute("INSERT INTO Reservation (reservation_id, edition_id, member_id, reserved_on, queue_position) VALUES (3, 1, 3, date('now'), 3)")
        
        # Cancel middle one
        self.conn.execute("UPDATE Reservation SET status = 'Cancelled' WHERE reservation_id = 2")
        self.conn.commit()
        
        # Bob should be cancelled, Charlie should be pos 2
        r3 = self.conn.execute("SELECT queue_position FROM Reservation WHERE reservation_id = 3").fetchone()
        self.assertEqual(r3['queue_position'], 2)

    def test_transaction_rollback(self):
        # Using a context manager for transaction
        try:
            with self.conn:
                self.conn.execute("INSERT INTO Member (member_id, name, email, member_type, join_date) VALUES (5, 'E', 'e@e.com', 'Student', date('now'))")
                # This will fail
                self.conn.execute("INSERT INTO Member (member_id, name, email, member_type, join_date) VALUES (6, 'F', 'a@a.com', 'Student', date('now'))") # dup email
        except sqlite3.IntegrityError:
            pass
            
        # Member 5 should not exist because transaction rolled back
        mem = self.conn.execute("SELECT * FROM Member WHERE member_id = 5").fetchone()
        self.assertIsNone(mem)

if __name__ == '__main__':
    unittest.main()
