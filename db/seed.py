import sqlite3
import random
from datetime import datetime, timedelta
import hashlib
import os

def seed_db(db_path='library.db', schema_path='db/schema_sqlite.sql'):
    random.seed(42)  # For deterministic data generation
    
    conn = sqlite3.connect(db_path)
    # Enable foreign keys
    conn.execute('PRAGMA foreign_keys = ON')
    
    # Execute schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    
    # Execute views
    with open('db/views.sql', 'r', encoding='utf-8') as f:
        views_sql = f.read()
    conn.executescript(views_sql)
    
    cursor = conn.cursor()
    
    # Staff Users
    pwd_admin = hashlib.sha256(b'admin123').hexdigest()
    pwd_lib = hashlib.sha256(b'lib123').hexdigest()
    cursor.execute("INSERT INTO Staff_User (username, password_hash, role) VALUES ('admin', ?, 'Admin')", (pwd_admin,))
    cursor.execute("INSERT INTO Staff_User (username, password_hash, role) VALUES ('librarian', ?, 'Librarian')", (pwd_lib,))
    
    # Loan Policies
    cursor.executemany("INSERT INTO Loan_Policy (member_type, max_books, loan_days, fine_per_day) VALUES (?, ?, ?, ?)", [
        ('Student', 3, 14, 2.0),
        ('Faculty', 10, 30, 0.0),
        ('Staff', 5, 21, 1.0)
    ])
    
    # Categories (~10)
    categories = ['Computer Science', 'Mathematics', 'Physics', 'History', 'Literature', 'Philosophy', 'Economics', 'Art', 'Biology', 'Chemistry']
    for cat in categories:
        cursor.execute("INSERT INTO Category (name) VALUES (?)", (cat,))
        
    # Publishers (~15)
    publishers = [f'Publisher {i}' for i in range(1, 16)]
    for pub in publishers:
        cursor.execute("INSERT INTO Publisher (name, contact) VALUES (?, ?)", (pub, f'contact@{pub.replace(" ", "").lower()}.com'))
        
    # Authors (~40)
    authors = [f'Author {i}' for i in range(1, 41)]
    for auth in authors:
        cursor.execute("INSERT INTO Author (name, bio) VALUES (?, ?)", (auth, f'Bio for {auth}'))
        
    # Books, Editions, Book_Author, Book_Category (~60)
    real_books = [
        "The Pragmatic Programmer", "Clean Code", "Design Patterns", "Introduction to Algorithms", "Structure and Interpretation of Computer Programs",
        "Artificial Intelligence: A Modern Approach", "Database System Concepts", "Computer Networking", "Operating System Concepts", "Compilers",
        "Calculus", "Linear Algebra and Its Applications", "Abstract Algebra", "Introduction to Topology", "Real Analysis",
        "A Brief History of Time", "The Elegant Universe", "Feynman Lectures on Physics", "Quantum Mechanics", "Cosmos",
        "Sapiens", "Guns, Germs, and Steel", "A People's History of the United States", "The Silk Roads", "SPQR",
        "1984", "To Kill a Mockingbird", "The Great Gatsby", "Pride and Prejudice", "Moby-Dick",
        "Meditations", "Beyond Good and Evil", "Critique of Pure Reason", "The Republic", "Nicomachean Ethics",
        "The Wealth of Nations", "Capital", "Thinking, Fast and Slow", "Freakonomics", "The Intelligent Investor",
        "The Story of Art", "Ways of Seeing", "Understanding Media", "Interaction of Color", "History of Modern Art",
        "Origin of Species", "The Selfish Gene", "Campbell Biology", "Molecular Biology of the Cell", "The Immortal Life of Henrietta Lacks",
        "Organic Chemistry", "Physical Chemistry", "Lehninger Principles of Biochemistry", "Inorganic Chemistry", "Chemistry: The Central Science",
        "Dune", "Neuromancer", "Foundation", "The Hobbit", "The Lord of the Rings"
    ]
    
    for i, title in enumerate(real_books, start=1):
        cursor.execute("INSERT INTO Book (title, description) VALUES (?, ?)", (title, f'A comprehensive guide on {title}.'))
        book_id = cursor.lastrowid
        
        # Editions
        publisher_id = random.randint(1, 15)
        year = random.randint(1990, 2023)
        isbn = f'978-0-{random.randint(100,999)}-{random.randint(1000,9999)}-{random.randint(0,9)}'
        cursor.execute("INSERT INTO Edition (book_id, publisher_id, edition_no, publication_year, isbn) VALUES (?, ?, 1, ?, ?)", (book_id, publisher_id, year, isbn))
        
        # Book Author
        num_authors = random.randint(1, 3)
        auth_ids = random.sample(range(1, 41), num_authors)
        for aid in auth_ids:
            cursor.execute("INSERT INTO Book_Author (book_id, author_id) VALUES (?, ?)", (book_id, aid))
            
        # Book Category
        cat_id = random.randint(1, 10)
        cursor.execute("INSERT INTO Book_Category (book_id, category_id) VALUES (?, ?)", (book_id, cat_id))

    # Copies (~150)
    copy_status_pool = ['Available', 'Available', 'Available', 'Available', 'Lost', 'Withdrawn']
    for i in range(1, 151):
        edition_id = random.randint(1, 60)
        accession_no = f'ACC-{i:04d}'
        status = random.choice(copy_status_pool)
        shelf = f'Shelf-{random.randint(1, 20)}'
        cursor.execute("INSERT INTO Copy (edition_id, accession_no, status, shelf_location) VALUES (?, ?, ?, ?)", (edition_id, accession_no, status, shelf))

    # Members (~40)
    member_types = ['Student'] * 25 + ['Faculty'] * 10 + ['Staff'] * 5
    for i in range(1, 41):
        name = f'Member {i}'
        email = f'member{i}@univ.edu'
        phone = f'555-{random.randint(1000,9999)}'
        m_type = member_types[i-1]
        join_date = (datetime.now() - timedelta(days=random.randint(100, 1000))).strftime('%Y-%m-%d')
        status = 'Active' if random.random() > 0.1 else 'Suspended'
        cursor.execute("INSERT INTO Member (name, email, phone, member_type, join_date, status) VALUES (?, ?, ?, ?, ?, ?)", 
                       (name, email, phone, m_type, join_date, status))

    # Issues (~80)
    available_copies = cursor.execute("SELECT copy_id FROM Copy WHERE status = 'Available'").fetchall()
    available_copies = [c[0] for c in available_copies]
    
    active_members = cursor.execute("SELECT member_id FROM Member WHERE status = 'Active'").fetchall()
    active_members = [m[0] for m in active_members]
    
    # We want some active issues, some returned.
    # To test overdue, some active issues should have due_date in the past.
    for i in range(80):
        member_id = random.choice(active_members)
        
        # Get loan days for member
        loan_days = cursor.execute("SELECT lp.loan_days FROM Loan_Policy lp JOIN Member m ON m.member_type = lp.member_type WHERE m.member_id = ?", (member_id,)).fetchone()[0]
        
        is_returned = random.random() > 0.3
        
        if is_returned:
            # issue in past, returned in past
            issue_date = datetime.now() - timedelta(days=random.randint(20, 100))
            due_date = issue_date + timedelta(days=loan_days)
            # 20% chance it was returned late
            is_late = random.random() > 0.8
            if is_late:
                return_date = due_date + timedelta(days=random.randint(1, 10))
            else:
                return_date = issue_date + timedelta(days=random.randint(1, loan_days))
                
            copy_id = random.choice(available_copies)
            
            try:
                # Insert as issued
                cursor.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
                               (copy_id, member_id, issue_date.strftime('%Y-%m-%d'), due_date.strftime('%Y-%m-%d')))
                issue_id = cursor.lastrowid
                # Update as returned to fire the return trigger
                cursor.execute("UPDATE Issue SET return_date = ? WHERE issue_id = ?", (return_date.strftime('%Y-%m-%d'), issue_id))
            except sqlite3.IntegrityError:
                pass
            
        else:
            # currently issued. some overdue, some not.
            is_overdue = random.random() > 0.5
            if is_overdue:
                issue_date = datetime.now() - timedelta(days=loan_days + random.randint(1, 10))
            else:
                issue_date = datetime.now() - timedelta(days=random.randint(1, loan_days - 1))
            due_date = issue_date + timedelta(days=loan_days)
            
            if available_copies:
                copy_id = available_copies.pop(0)
                try:
                    cursor.execute("INSERT INTO Issue (copy_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
                                   (copy_id, member_id, issue_date.strftime('%Y-%m-%d'), due_date.strftime('%Y-%m-%d')))
                except sqlite3.IntegrityError:
                    pass

    # Fines (~30) 
    # Automatically created by trigger if returned late. Let's mark some as paid.
    fines = cursor.execute("SELECT fine_id, issue_id FROM Fine").fetchall()
    for row in fines:
        fine_id = row[0]
        paid = 1 if random.random() > 0.5 else 0
        if paid:
            cursor.execute("UPDATE Fine SET paid_flag = 1, paid_date = date('now') WHERE fine_id = ?", (fine_id,))

    # Reservations (~15)
    for i in range(15):
        edition_id = random.randint(1, 60)
        member_id = random.randint(1, 40)
        reserved_on = (datetime.now() - timedelta(days=random.randint(1, 10))).strftime('%Y-%m-%d')
        
        # Get next queue position
        pos = cursor.execute("SELECT COALESCE(MAX(queue_position), 0) + 1 FROM Reservation WHERE edition_id = ? AND status = 'Waiting'", (edition_id,)).fetchone()[0]
        
        cursor.execute("INSERT INTO Reservation (edition_id, member_id, reserved_on, queue_position) VALUES (?, ?, ?, ?)",
                       (edition_id, member_id, reserved_on, pos))

    # Digital Resources (~25)
    for i in range(1, 26):
        title = f'Digital Resource {i}'
        url = f'/static/resources/res_{i}.pdf'
        l_type = random.choice(['Open Access', 'Proprietary', 'Subscription'])
        cursor.execute("INSERT INTO Digital_Resource (title, url_or_path, license_type) VALUES (?, ?, ?)", (title, url, l_type))

    # Digital Access Logs (~100)
    for i in range(100):
        member_id = random.randint(1, 40)
        resource_id = random.randint(1, 25)
        acc_time = (datetime.now() - timedelta(hours=random.randint(1, 1000))).strftime('%Y-%m-%d %H:%M:%S')
        action = random.choice(['View', 'Download'])
        cursor.execute("INSERT INTO Digital_Access_Log (member_id, resource_id, access_time, action) VALUES (?, ?, ?, ?)",
                       (member_id, resource_id, acc_time, action))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    if os.path.exists('library.db'):
        os.remove('library.db')
    seed_db('library.db', 'schema_sqlite.sql')
    print("Database seeded successfully.")
