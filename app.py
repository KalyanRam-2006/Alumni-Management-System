from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for session handling

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

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM admin WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ("admin", "admin123"))

    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        batch = request.form["batch"]
        branch = request.form["branch"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO alumni (name, email, password, batch, branch) VALUES (?, ?, ?, ?, ?)",
                       (name, email, password, batch, branch))
        conn.commit()
        conn.close()

        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alumni WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]  # store name in session
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Credentials!"
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return f"Welcome {session['user']} to Alumni Dashboard!"
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
