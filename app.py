from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for session handling

# Database setup
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS alumni (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        email TEXT UNIQUE,
                        password TEXT,
                        batch TEXT,
                        branch TEXT
                    )''')
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
