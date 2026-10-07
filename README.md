# dbms_project-
# Offline Library Database Management System

A comprehensive, zero-dependency, fully offline Database Management System (DBMS) designed for library circulation and digital resource management. Built entirely using Python's Standard Library and vanilla frontend technologies to ensure maximum portability.

## 🚀 Features
- **Zero External Dependencies:** No `pip install` required. No frameworks like Django or Flask. No CDNs for frontend. Runs purely on Python standard library (`http.server`, `sqlite3`).
- **Robust 3NF Database Schema:** 13 deeply relational tables utilizing SQLite `FOREIGN KEY` constraints (`ON DELETE CASCADE` / `RESTRICT`).
- **Automated Business Logic (Triggers):** Fines are automatically calculated, reservations are processed, and statuses are updated entirely by SQLite triggers.
- **Dynamic SQL Views:** Real-time reporting on overdue books and available titles.
- **Premium User Interface:** Custom Dark Mode UI featuring Glassmorphism, built with Vanilla CSS/HTML/JS.
- **Admin Dashboard:** Manage members, dynamically update loan policies (max books, fine rates), and perform a full database factory reset.

## 🛠️ Tech Stack
- **Backend:** Python 3.9+ 
- **Database:** SQLite3 (Schema strictly normalized to 3NF)
- **Frontend:** Vanilla HTML5, CSS3, JavaScript
- **Server:** Custom built using `http.server.BaseHTTPRequestHandler`

## ⚙️ How to Run Locally

Because this project uses zero external packages, running it is incredibly easy on any machine:

1. **Prerequisites:** Ensure you have [Python 3.9+](https://www.python.org/downloads/) installed on your system.
2. **Clone the Repository** (or extract the `.zip` file).
3. **Open Terminal** and navigate into the project directory:
   ```bash
   cd library_dbms
   ```
4. **Initialize and Run:**
   To build the database with sample data for the very first time, run:
   ```bash
   python run.py --reset
   ```
   *(For all future runs, you can simply run `python run.py` so you don't overwrite your data).*
5. **Access the Application:**
   The server will automatically open your default web browser to `http://127.0.0.1:8000`.

## 🔐 Demo Credentials

The database is pre-seeded with two staff accounts for testing:

**Administrator Account:** (Has access to the Admin Panel)
- **Username:** `admin`
- **Password:** `admin123`

**Librarian Account:** (Standard circulation operations)
- **Username:** `librarian`
- **Password:** `lib123`

## 📁 Project Structure

```
library_dbms/
├── app/
│   ├── static/         # CSS and JS files
│   ├── templates/      # HTML layout and page templates
│   ├── dao.py          # Data Access Object handling all SQL queries
│   ├── server.py       # Custom HTTP Server and routing logic
│   └── validators.py   # Input validation logic
├── db/
│   ├── schema_sqlite.sql    # Core DDL (Tables, Indexes, Triggers)
│   ├── schema_postgres.sql  # Equivalent Postgres DDL
│   ├── views.sql            # Core SQL Views (Reports)
│   ├── queries.sql          # Collection of complex analytical queries
│   └── seed.py              # Generates dummy data and builds the DB
├── docs/
│   └── project_report.md    # Full academic project report with ER Diagram
└── run.py                   # Main entry point to launch the app
```
