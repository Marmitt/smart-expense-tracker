import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "data/app.db"

def connect():
    return sqlite3.connect(DB_NAME)

def create_user(username, password):
    db = connect()
    hashed = generate_password_hash(password)
    try:
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        db.close()

def validate_user(username, password):
    db = connect()
    row = db.execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchone()
    db.close()
    if row and check_password_hash(row[1], password):
        return row[0]
    return None
