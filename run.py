import argparse
import os
import sys
import webbrowser
import threading
import time

def setup_db(reset=False):
    db_path = 'library.db'
    if reset and os.path.exists(db_path):
        os.remove(db_path)
        print("Existing database removed.")
        
    if not os.path.exists(db_path):
        print("Database not found. Creating and seeding...")
        from db.seed import seed_db
        seed_db(db_path, 'db/schema_sqlite.sql')
    else:
        print("Database already exists. Reusing library.db")

def run_tests():
    import unittest
    print("Running test suite...")
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

def open_browser(url):
    time.sleep(1)
    webbrowser.open(url)

if __name__ == '__main__':
    # Ensure working directory is the project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    parser = argparse.ArgumentParser(description="Library DBMS runner")
    parser.add_argument('--reset', action='store_true', help="Reset and reseed database")
    parser.add_argument('--test', action='store_true', help="Run unit tests")
    args = parser.parse_args()

    if args.test:
        run_tests()
        sys.exit(0)

    setup_db(args.reset)
    
    from app.server import run_server
    
    # Run server in a way that detects port
    print("Starting server...")
    try:
        from http.server import HTTPServer
        from app.server import LibraryHandler
        port = 8000
        server = None
        while port < 8100:
            try:
                server = HTTPServer(('127.0.0.1', port), LibraryHandler)
                break
            except OSError:
                port += 1
        if not server:
            print("No free ports found.")
            sys.exit(1)
            
        url = f"http://127.0.0.1:{port}"
        print(f"Database ready. Server running at {url}")
        print("Login credentials:")
        print("Admin: admin / admin123")
        print("Librarian: librarian / lib123")
        
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        sys.exit(0)
