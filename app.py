from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for session handling

# Admin-only user management route
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    # Only allow access if logged in as admin
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Approve or delete user actions
    if request.method == "POST":
        user_id = request.form.get("user_id")
        action = request.form.get("action")
        if user_id and action:
            if action == "approve":
                # Add 'approved' column if not exists
                cursor.execute("PRAGMA table_info(alumni)")
                columns = [col[1] for col in cursor.fetchall()]
                if "approved" not in columns:
                    cursor.execute("ALTER TABLE alumni ADD COLUMN approved INTEGER DEFAULT 0")
                    conn.commit()
                cursor.execute("UPDATE alumni SET approved=1 WHERE id=?", (user_id,))
                conn.commit()
            elif action == "delete":
                cursor.execute("DELETE FROM alumni WHERE id=?", (user_id,))
                conn.commit()

    # Ensure 'approved' column exists for display
    cursor.execute("PRAGMA table_info(alumni)")
    columns = [col[1] for col in cursor.fetchall()]
    if "approved" not in columns:
        cursor.execute("ALTER TABLE alumni ADD COLUMN approved INTEGER DEFAULT 0")
        conn.commit()

    cursor.execute("SELECT id, name, email, batch, branch, approved FROM alumni")
    users = cursor.fetchall()
    conn.close()

    return render_template("admin.html", users=users)

# Database setup
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Alumni Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS alumni (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        email TEXT UNIQUE,
                        password TEXT,
                        batch TEXT,
                        branch TEXT
                    )''')

    # Admin Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT
                    )''')
    
    # Announcements Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    message TEXT
                )''')   

    # Events Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    date TEXT,
                    created_by TEXT
                )''')

    # RSVP Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS rsvp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    alumni_id INTEGER,
                    FOREIGN KEY(event_id) REFERENCES events(id),
                    FOREIGN KEY(alumni_id) REFERENCES alumni(id)
                )''')

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM admin WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ("admin", "admin123"))

    conn.commit()
    conn.close()
# List all events
@app.route("/events", methods=["GET", "POST"])
def events():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events_list = cursor.fetchall()

    rsvp_status = {}
    if "user" in session:
        # Get alumni id
        cursor.execute("SELECT id FROM alumni WHERE name=?", (session["user"],))
        alumni = cursor.fetchone()
        if alumni:
            alumni_id = alumni[0]
            cursor.execute("SELECT event_id FROM rsvp WHERE alumni_id=?", (alumni_id,))
            rsvp_events = [row[0] for row in cursor.fetchall()]
            rsvp_status = {eid: True for eid in rsvp_events}

    conn.close()
    return render_template("events.html", events=events_list, rsvp_status=rsvp_status)

# Create a new event (admin only)
@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        date = request.form["date"].strip()
        created_by = session["admin"]
        if not title or not description or not date:
            flash("All fields are required.")
            return render_template("create_event.html")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO events (title, description, date, created_by) VALUES (?, ?, ?, ?)",
                       (title, description, date, created_by))
        conn.commit()
        conn.close()
        return redirect(url_for("events"))
    return render_template("create_event.html")

# RSVP to an event (alumni only)
@app.route("/rsvp/<int:event_id>", methods=["POST"])
def rsvp_event(event_id):
    if "user" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alumni WHERE name=?", (session["user"],))
    alumni = cursor.fetchone()
    if alumni:
        alumni_id = alumni[0]
        # Prevent duplicate RSVP
        cursor.execute("SELECT * FROM rsvp WHERE event_id=? AND alumni_id=?", (event_id, alumni_id))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO rsvp (event_id, alumni_id) VALUES (?, ?)", (event_id, alumni_id))
            conn.commit()
    conn.close()
    return redirect(url_for("events"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        batch = request.form["batch"].strip()
        branch = request.form["branch"].strip()

        # Input validation
        if not name or not email or not password:
            flash("Name, Email, and Password are required.")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO alumni (name, email, password, batch, branch) VALUES (?, ?, ?, ?, ?)",
                           (name, email, hashed_password, batch, branch))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template("register.html")
        finally:
            conn.close()

        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        # Input validation
        if not email or not password:
            flash("Email and Password are required.")
            return render_template("login.html")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alumni WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user"] = user[1]  # store name in session
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Credentials!")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" in session:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
        announcements = cursor.fetchall()
        conn.close()
        return render_template("dashboard.html", user=session["user"], announcements=announcements)
    else:
        return redirect(url_for("login"))
  
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["admin"] = username
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials!"
    return render_template("admin_login.html")


@app.route("/admin-dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Search & Filter
    query = "SELECT * FROM alumni"
    filters = []
    params = []

    if request.method == "POST":
        batch = request.form.get("batch")
        branch = request.form.get("branch")
        if batch:
            filters.append("batch=?")
            params.append(batch)
        if branch:
            filters.append("branch=?")
            params.append(branch)

        if filters:
            query += " WHERE " + " AND ".join(filters)

    cursor.execute(query, params)
    alumni_list = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", alumni_list=alumni_list)

@app.route("/admin-announcements", methods=["GET", "POST"])
def admin_announcements():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        message = request.form["message"]
        cursor.execute("INSERT INTO announcements (title, message) VALUES (?, ?)", (title, message))
        conn.commit()

    cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
    announcements = cursor.fetchall()
    conn.close()

    return render_template("admin_announcements.html", announcements=announcements)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
