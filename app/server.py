import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import cookies
import os
import hashlib
from app.dao import LibraryDAO

dao = LibraryDAO('library.db')

SESSIONS = {}

def get_template(name):
    path = os.path.join('app', 'templates', f'{name}.html')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def render(template_name, context=None, use_layout=True):
    if context is None:
        context = {}
    html = get_template(template_name)
    
    if use_layout:
        layout = get_template('layout')
        content_html = html
        for k, v in context.items():
            content_html = content_html.replace(f'{{{{ {k} }}}}', str(v))
            
        html = layout.replace('{{ content }}', content_html)
        
        # Process layout-level contexts like flash messages and user
        for k in ['flash', 'username', 'role', 'admin_panel_link']:
            val = context.get(k, '')
            html = html.replace(f'{{{{ {k} }}}}', str(val))
    else:
        # Just replace context in the single template
        for k, v in context.items():
            html = html.replace(f'{{{{ {k} }}}}', str(v))
            
    return html

class LibraryHandler(BaseHTTPRequestHandler):
    def get_session(self):
        cookie_str = self.headers.get('Cookie', '')
        c = cookies.SimpleCookie(cookie_str)
        if 'session_id' in c:
            sid = c['session_id'].value
            return SESSIONS.get(sid)
        return None

    def create_session(self, user):
        sid = hashlib.sha256(os.urandom(32)).hexdigest()
        SESSIONS[sid] = user
        return sid

    def parse_post_data(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        return dict(urllib.parse.parse_qsl(post_data))

    def redirect(self, path, session_id=None):
        self.send_response(302)
        self.send_header('Location', path)
        if session_id:
            c = cookies.SimpleCookie()
            c['session_id'] = session_id
            c['session_id']['path'] = '/'
            self.send_header('Set-Cookie', c['session_id'].OutputString())
        self.end_headers()

    def do_GET(self):
        # Serve static files
        if self.path.startswith('/static/'):
            path = os.path.join('app', self.path.lstrip('/'))
            if os.path.exists(path):
                self.send_response(200)
                ext = path.split('.')[-1]
                ct = 'text/css' if ext == 'css' else 'application/javascript' if ext == 'js' else 'text/html'
                self.send_header('Content-Type', ct)
                self.end_headers()
                with open(path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
            return

        user = self.get_session()
        
        path = self.path.split('?')[0]
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if path == '/login':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(render('login', {'flash': qs.get('flash', [''])[0]}, use_layout=False).encode())
            return
            
        if not user:
            self.redirect('/login')
            return

        admin_link = '<li><a href="/admin" style="color: #ef4444; font-weight: bold;">Admin Panel</a></li>' if user['role'] == 'Admin' else ''
        context = {'username': user['username'], 'role': user['role'], 'flash': qs.get('flash', [''])[0], 'admin_panel_link': admin_link}

        try:
            if path == '/' or path == '/dashboard':
                stats = dao.get_dashboard_stats()
                context.update(stats)
                html = render('dashboard', context)
                
            elif path == '/search':
                term = qs.get('q', [''])[0]
                results = dao.search_books(term) if term else []
                rows = ''.join([f"<tr><td>{r['title']}</td><td>{r['author']}</td><td>{r['category']}</td><td>{r['isbn']}</td><td>{r['accession_no']}</td><td>{r['status']}</td></tr>" for r in results])
                context.update({'term': term, 'results': rows})
                html = render('search', context)
                
            elif path == '/issue':
                html = render('issue', context)
                
            elif path == '/return':
                html = render('return', context)
                
            elif path == '/fines':
                fines = dao.fetch_all("SELECT f.fine_id, i.issue_id, m.name, f.amount, f.paid_flag, f.paid_date FROM Fine f JOIN Issue i ON f.issue_id = i.issue_id JOIN Member m ON i.member_id = m.member_id ORDER BY f.paid_flag, f.fine_id DESC")
                rows = ''
                for f in fines:
                    status = 'Paid' if f['paid_flag'] else f'<form method="POST" action="/pay_fine" style="display:inline"><input type="hidden" name="fine_id" value="{f["fine_id"]}"><button type="submit">Mark Paid</button></form>'
                    rows += f"<tr><td>{f['fine_id']}</td><td>{f['name']}</td><td>₹{f['amount']}</td><td>{status}</td><td>{f['paid_date'] or '-'}</td></tr>"
                context['fines_table'] = rows
                html = render('fines', context)

            elif path == '/reports':
                with open('db/queries.sql', 'r') as f:
                    queries = f.read()
                
                # We will just fetch a few interesting ones
                # v_available_titles
                titles = dao.fetch_all("SELECT * FROM v_available_titles")
                t_rows = ''.join([f"<tr><td>{r['title']}</td><td>{r['isbn']}</td><td>{r['edition_no']}</td><td>{r['available_copies']}</td></tr>" for r in titles])
                
                overdue = dao.fetch_all("SELECT * FROM v_overdue_copies")
                o_rows = ''.join([f"<tr><td>{r['accession_no']}</td><td>{r['title']}</td><td>{r['member_name']}</td><td>{r['days_overdue']}</td></tr>" for r in overdue])
                
                context.update({'available_titles': t_rows, 'overdue_copies': o_rows, 'sql_text': queries})
                html = render('reports', context)
                
            elif path == '/admin':
                if user['role'] != 'Admin':
                    self.redirect('/dashboard?flash=Unauthorized+access')
                    return
                html = render('admin', context)

                
            elif path == '/list':
                l_type = qs.get('type', [''])[0]
                if l_type == 'copies':
                    data = dao.fetch_all("SELECT c.accession_no, b.title, c.status, c.shelf_location FROM Copy c JOIN Edition e ON c.edition_id = e.edition_id JOIN Book b ON e.book_id = b.book_id ORDER BY c.accession_no")
                    headers = "<th>Accession No</th><th>Title</th><th>Status</th><th>Shelf</th>"
                    rows = ''.join([f"<tr><td>{r['accession_no']}</td><td>{r['title']}</td><td>{r['status']}</td><td>{r['shelf_location']}</td></tr>" for r in data])
                    context.update({'list_title': 'Total Copies', 'headers': headers, 'rows': rows})
                elif l_type == 'issued':
                    data = dao.fetch_all("SELECT c.accession_no, b.title, m.name, i.issue_date, i.due_date FROM Issue i JOIN Copy c ON i.copy_id = c.copy_id JOIN Edition e ON c.edition_id = e.edition_id JOIN Book b ON e.book_id = b.book_id JOIN Member m ON i.member_id = m.member_id WHERE i.return_date IS NULL ORDER BY i.issue_date DESC")
                    headers = "<th>Accession No</th><th>Title</th><th>Member</th><th>Issue Date</th><th>Due Date</th>"
                    rows = ''.join([f"<tr><td>{r['accession_no']}</td><td>{r['title']}</td><td>{r['name']}</td><td>{r['issue_date']}</td><td>{r['due_date']}</td></tr>" for r in data])
                    context.update({'list_title': 'Currently Issued Books', 'headers': headers, 'rows': rows})
                elif l_type == 'overdue':
                    data = dao.fetch_all("SELECT * FROM v_overdue_copies")
                    headers = "<th>Accession No</th><th>Title</th><th>Member</th><th>Due Date</th><th>Days Overdue</th>"
                    rows = ''.join([f"<tr><td>{r['accession_no']}</td><td>{r['title']}</td><td>{r['member_name']}</td><td>{r['due_date']}</td><td>{r['days_overdue']}</td></tr>" for r in data])
                    context.update({'list_title': 'Overdue Books', 'headers': headers, 'rows': rows})
                elif l_type == 'reservations':
                    data = dao.fetch_all("SELECT * FROM v_reservation_queue")
                    headers = "<th>Queue Pos</th><th>Title</th><th>ISBN</th><th>Member</th><th>Reserved On</th>"
                    rows = ''.join([f"<tr><td>{r['queue_position']}</td><td>{r['title']}</td><td>{r['isbn']}</td><td>{r['member_name']}</td><td>{r['reserved_on']}</td></tr>" for r in data])
                    context.update({'list_title': 'Waiting Reservations', 'headers': headers, 'rows': rows})
                else:
                    context.update({'list_title': 'Unknown List', 'headers': '', 'rows': ''})
                html = render('list', context)
                
            elif path == '/logout':
                if 'session_id' in self.headers.get('Cookie', ''):
                    c = cookies.SimpleCookie(self.headers['Cookie'])
                    sid = c['session_id'].value
                    if sid in SESSIONS:
                        del SESSIONS[sid]
                self.redirect('/login')
                return
            else:
                self.send_error(404)
                return
                
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
            self.send_error(500, str(e))

    def do_POST(self):
        path = self.path
        data = self.parse_post_data()
        
        if path == '/login':
            user = dao.authenticate(data.get('username'), hashlib.sha256(data.get('password', '').encode()).hexdigest())
            if user:
                sid = self.create_session(dict(user))
                self.redirect('/dashboard', sid)
            else:
                self.redirect('/login?flash=Invalid+credentials')
            return
            
        user = self.get_session()
        if not user:
            self.redirect('/login')
            return

        if path == '/issue':
            accession_no = data.get('accession_no')
            member_id = data.get('member_id')
            success, msg = dao.issue_book(accession_no, member_id)
            self.redirect(f'/issue?flash={urllib.parse.quote(msg)}')
            
        elif path == '/return':
            accession_no = data.get('accession_no')
            success, msg = dao.return_book(accession_no)
            self.redirect(f'/return?flash={urllib.parse.quote(msg)}')
            
        elif path == '/pay_fine':
            fine_id = data.get('fine_id')
            success, msg = dao.pay_fine(fine_id)
            self.redirect(f'/fines?flash={urllib.parse.quote(msg)}')
            
        elif path.startswith('/admin'):
            if user['role'] != 'Admin':
                self.redirect('/dashboard?flash=Unauthorized')
                return
                
            if path == '/admin/delete_member':
                member_id = data.get('member_id')
                success, msg = dao.delete_member(member_id)
                self.redirect(f'/admin?flash={urllib.parse.quote(msg)}')
                
            elif path == '/admin/update_policy':
                m_type = data.get('member_type')
                max_books = data.get('max_books')
                loan_days = data.get('loan_days')
                fine = data.get('fine_per_day')
                success, msg = dao.update_policy(m_type, max_books, loan_days, fine)
                self.redirect(f'/admin?flash={urllib.parse.quote(msg)}')
                
            elif path == '/admin/reset_db':
                # Call seed_db directly
                import db.seed
                db.seed.seed_db()
                # Clear all sessions
                SESSIONS.clear()
                self.redirect('/login?flash=Database+Reset+Successfully.+Please+log+in+again.')
                
        else:
            self.send_error(404)

def run_server(port=8000):
    while port < 8100:
        try:
            server = HTTPServer(('127.0.0.1', port), LibraryHandler)
            print(f"Server running on http://127.0.0.1:{port}")
            return server, port
        except OSError:
            port += 1
    raise RuntimeError("Could not find open port")
