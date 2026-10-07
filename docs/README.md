# Library Circulation and Digital Resource Management System

A complete, fully offline, database-centric project built purely on the Python standard library. No external dependencies, pip installs, or internet connections required.

## Features
- **Pure Local Implementation**: Runs `http.server` serving vanilla HTML/CSS/JS.
- **Relational Database**: Uses SQLite3 with 3NF normalized tables, fully automated via `schema_sqlite.sql`.
- **Advanced Constraints**: Strict business rules enforced natively in DB via Check, Unique Partial Indices, Foreign Keys, and Triggers.
- **Full Reporting**: Complex queries including inner/left/self joins, group by/having, nested subqueries, and EXISTS.
- **Robust UI**: Clean UI allowing Issue, Return, Fines, Reservations, Search, and Reports.

## Setup and Run
1. Ensure Python 3.9+ is installed.
2. Open terminal in the project directory.
3. Run the application:
   ```bash
   python run.py
   ```
   This automatically detects the DB, seeds it if new, runs the server, and opens the browser.
   
4. **Options**:
   - `python run.py --reset`: Resets the DB and re-seeds it.
   - `python run.py --test`: Runs the built-in unit test suite.

## Credentials
- **Admin**: `admin` / `admin123`
- **Librarian**: `librarian` / `lib123`
