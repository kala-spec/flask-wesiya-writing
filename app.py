from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "my_secret_key_for_learning"

DATABASE = "wesiya.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            daily_note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    connection.commit()
    connection.close()


def find_user_by_email(email):
    connection = get_db_connection()
    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    connection.close()

    return user


def create_user(email, password):
    connection = get_db_connection()

    connection.execute(
        "INSERT INTO users (email, password, created_at) VALUES (?, ?, ?)",
        (email, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    connection.commit()
    connection.close()


def save_note(user_id, daily_note):
    connection = get_db_connection()

    connection.execute(
        "INSERT INTO notes (user_id, daily_note, created_at) VALUES (?, ?, ?)",
        (user_id, daily_note, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    connection.commit()
    connection.close()


def get_notes_by_user(user_id):
    connection = get_db_connection()

    notes = connection.execute("""
        SELECT notes.id, notes.daily_note, notes.created_at, users.email
        FROM notes
        JOIN users ON notes.user_id = users.id
        WHERE notes.user_id = ?
        ORDER BY notes.id DESC
    """, (user_id,)).fetchall()

    connection.close()

    return notes


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html")


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    notes = get_notes_by_user(session["user_id"])

    return render_template("profile.html", notes=notes)


@app.route("/login", methods=["POST"])
def login_user():
    email = request.form.get("email")
    password = request.form.get("password")

    user = find_user_by_email(email)

    if user is None:
        return render_template(
            "login.html",
            signup_message="No account found with this email. Please sign up first.",
            signup_email=email
        )

    if user["password"] != password:
        return render_template(
            "login.html",
            error="Wrong password. Please try again."
        )

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return redirect(url_for("home"))


@app.route("/signup", methods=["POST"])
def signup_user():
    email = request.form.get("email")
    password = request.form.get("password")

    existing_user = find_user_by_email(email)

    if existing_user is not None:
        return render_template(
            "login.html",
            error="This email already exists. Please login instead."
        )

    create_user(email, password)

    new_user = find_user_by_email(email)

    session["user_id"] = new_user["id"]
    session["email"] = new_user["email"]

    return redirect(url_for("home"))


@app.route("/submit_note", methods=["POST"])
def submit_note():
    if "user_id" not in session:
        return redirect(url_for("login"))

    daily_note = request.form.get("daily_note")

    if daily_note:
        save_note(session["user_id"], daily_note)

    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)