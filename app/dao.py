import sqlite3

class LibraryDAO:
    def __init__(self, db_path='library.db'):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.row_factory = sqlite3.Row
        return conn

    def authenticate(self, username, password_hash):
        with self._get_conn() as conn:
            user = conn.execute("SELECT * FROM Staff_User WHERE username = ? AND password_hash = ?", (username, password_hash)).fetchone()
            return user

    def get_dashboard_stats(self):
        stats = {}
        with self._get_conn() as conn:
            stats['total_books'] = conn.execute("SELECT COUNT(*) FROM Copy").fetchone()[0]
            stats['issued'] = conn.execute("SELECT COUNT(*) FROM Issue WHERE return_date IS NULL").fetchone()[0]
            stats['overdue'] = conn.execute("SELECT COUNT(*) FROM Issue WHERE return_date IS NULL AND date('now') > due_date").fetchone()[0]
            stats['reservations'] = conn.execute("SELECT COUNT(*) FROM Reservation WHERE status = 'Waiting'").fetchone()[0]
            stats['fines_due'] = conn.execute("SELECT SUM(amount) FROM Fine WHERE paid_flag = 0").fetchone()[0] or 0
        return stats

    def fetch_all(self, query, params=()):
        with self._get_conn() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_one(self, query, params=()):
        with self._get_conn() as conn:
            return conn.execute(query, params).fetchone()

    def execute_write(self, query, params=()):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def issue_book(self, accession_no, member_id):
        # Transaction required for issue book
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                # Find copy_id
                copy = cursor.execute("SELECT copy_id FROM Copy WHERE accession_no = ?", (accession_no,)).fetchone()
                if not copy:
                    return False, "Copy not found"
                copy_id = copy['copy_id']
                
                # Check member
                member = cursor.execute("SELECT member_type FROM Member WHERE member_id = ?", (member_id,)).fetchone()
                if not member:
                    return False, "Member not found"
                
                # Get loan policy
                lp = cursor.execute("SELECT loan_days FROM Loan_Policy WHERE member_type = ?", (member['member_type'],)).fetchone()
                loan_days = lp['loan_days']
                
                # Insert issue record (triggers will check business rules)
                cursor.execute("""
                    INSERT INTO Issue (copy_id, member_id, issue_date, due_date) 
                    VALUES (?, ?, date('now'), date('now', '+' || ? || ' days'))
                """, (copy_id, member_id, str(loan_days)))
                conn.commit()
                return True, "Book issued successfully"
        except sqlite3.IntegrityError as e:
            return False, str(e)
        except sqlite3.DatabaseError as e:
            return False, str(e)

    def return_book(self, accession_no):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                copy = cursor.execute("SELECT copy_id FROM Copy WHERE accession_no = ?", (accession_no,)).fetchone()
                if not copy:
                    return False, "Copy not found"
                copy_id = copy['copy_id']
                
                issue = cursor.execute("SELECT issue_id FROM Issue WHERE copy_id = ? AND return_date IS NULL", (copy_id,)).fetchone()
                if not issue:
                    return False, "Book is not currently issued"
                    
                cursor.execute("UPDATE Issue SET return_date = date('now') WHERE issue_id = ?", (issue['issue_id'],))
                conn.commit()
                
                # Check if fine was generated
                fine = cursor.execute("SELECT amount FROM Fine WHERE issue_id = ?", (issue['issue_id'],)).fetchone()
                msg = "Book returned successfully."
                if fine:
                    msg += f" Late return: Fine of {fine['amount']} generated."
                return True, msg
        except sqlite3.Error as e:
            return False, str(e)
            
    def pay_fine(self, fine_id):
        try:
            with self._get_conn() as conn:
                conn.execute("UPDATE Fine SET paid_flag = 1, paid_date = date('now') WHERE fine_id = ?", (fine_id,))
                conn.commit()
                return True, "Fine marked as paid."
        except sqlite3.Error as e:
            return False, str(e)

    def add_member(self, name, email, phone, member_type):
        try:
            with self._get_conn() as conn:
                conn.execute("INSERT INTO Member (name, email, phone, member_type, join_date) VALUES (?, ?, ?, ?, date('now'))",
                             (name, email, phone, member_type))
                conn.commit()
                return True, "Member registered successfully"
        except sqlite3.Error as e:
            return False, str(e)

    def search_books(self, term):
        query = """
            SELECT b.title, a.name AS author, c.name AS category, e.isbn, cp.accession_no, cp.status
            FROM Book b
            JOIN Book_Author ba ON b.book_id = ba.book_id
            JOIN Author a ON ba.author_id = a.author_id
            JOIN Book_Category bc ON b.book_id = bc.book_id
            JOIN Category c ON bc.category_id = c.category_id
            JOIN Edition e ON b.book_id = e.book_id
            JOIN Copy cp ON e.edition_id = cp.edition_id
            WHERE b.title LIKE ? OR a.name LIKE ? OR e.isbn LIKE ? OR c.name LIKE ?
            ORDER BY b.title
        """
        term = f'%{term}%'
        return self.fetch_all(query, (term, term, term, term))

    def place_reservation(self, edition_id, member_id):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                pos = cursor.execute("SELECT COALESCE(MAX(queue_position), 0) + 1 FROM Reservation WHERE edition_id = ? AND status = 'Waiting'", (edition_id,)).fetchone()[0]
                cursor.execute("INSERT INTO Reservation (edition_id, member_id, reserved_on, queue_position) VALUES (?, ?, date('now'), ?)",
                               (edition_id, member_id, pos))
                conn.commit()
                return True, f"Reservation placed successfully at position {pos}"
        except sqlite3.Error as e:
            return False, str(e)

    def cancel_reservation(self, reservation_id):
        try:
            with self._get_conn() as conn:
                conn.execute("UPDATE Reservation SET status = 'Cancelled' WHERE reservation_id = ?", (reservation_id,))
                conn.commit()
                return True, "Reservation cancelled successfully"
        except sqlite3.Error as e:
            return False, str(e)

    def log_digital_access(self, member_id, resource_id, action):
        try:
            with self._get_conn() as conn:
                conn.execute("INSERT INTO Digital_Access_Log (member_id, resource_id, access_time, action) VALUES (?, ?, datetime('now'), ?)",
                             (member_id, resource_id, action))
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def delete_member(self, member_id):
        try:
            with self._get_conn() as conn:
                # Check if member exists
                exists = conn.execute("SELECT 1 FROM Member WHERE member_id = ?", (member_id,)).fetchone()
                if not exists:
                    return False, "Member not found"
                # If they have active issues, delete will fail because of ON DELETE RESTRICT in schema
                conn.execute("DELETE FROM Member WHERE member_id = ?", (member_id,))
                conn.commit()
                return True, "Member deleted successfully."
        except sqlite3.IntegrityError:
            return False, "Cannot delete member: They currently have active book issues."
        except sqlite3.Error as e:
            return False, str(e)

    def update_policy(self, member_type, max_books, loan_days, fine_per_day):
        try:
            with self._get_conn() as conn:
                conn.execute("UPDATE Loan_Policy SET max_books = ?, loan_days = ?, fine_per_day = ? WHERE member_type = ?",
                             (max_books, loan_days, fine_per_day, member_type))
                conn.commit()
                return True, f"{member_type} policy updated successfully."
        except sqlite3.Error as e:
            return False, str(e)
