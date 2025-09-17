import sqlite3
from werkzeug.security import generate_password_hash

def hash_existing_passwords():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM alumni")
    users = cursor.fetchall()
    for user in users:
        user_id, password = user
        # Only hash if not already hashed (simple check: hashes start with 'pbkdf2:')
        if not password.startswith('pbkdf2:'):
            hashed = generate_password_hash(password)
            cursor.execute("UPDATE alumni SET password=? WHERE id=?", (hashed, user_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    hash_existing_passwords()
    print("All plain text passwords have been hashed.")
