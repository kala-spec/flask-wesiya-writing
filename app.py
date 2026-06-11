from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "my_secret_key_for_learning"

DATABASE = "wesiya.db"
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
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
        (
            email,
            password,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    connection.commit()
    connection.close()


def save_text_note(user_id, daily_note):
    connection = get_db_connection()

    connection.execute(
        "INSERT INTO notes (user_id, daily_note, created_at) VALUES (?, ?, ?)",
        (
            user_id,
            daily_note,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    connection.commit()
    connection.close()


def get_text_notes_by_user(user_id):
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


def save_voice_note(user_id, filename, file_path):
    connection = get_db_connection()

    connection.execute(
        "INSERT INTO voice_notes (user_id, filename, file_path, created_at) VALUES (?, ?, ?, ?)",
        (
            user_id,
            filename,
            file_path,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    connection.commit()
    connection.close()


def get_voice_notes_by_user(user_id):
    connection = get_db_connection()

    voice_notes = connection.execute("""
        SELECT voice_notes.id, voice_notes.filename, voice_notes.file_path,
               voice_notes.created_at, users.email
        FROM voice_notes
        JOIN users ON voice_notes.user_id = users.id
        WHERE voice_notes.user_id = ?
        ORDER BY voice_notes.id DESC
    """, (user_id,)).fetchall()

    connection.close()
    return voice_notes


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

    notes = get_text_notes_by_user(session["user_id"])
    voice_notes = get_voice_notes_by_user(session["user_id"])

    return render_template(
        "profile.html",
        notes=notes,
        voice_notes=voice_notes
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if "user_id" not in session:
        return redirect(url_for("login"))

    return send_from_directory(UPLOAD_FOLDER, filename)


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


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/submit_note", methods=["POST"])
def submit_note():
    if "user_id" not in session:
        return redirect(url_for("login"))

    daily_note = request.form.get("daily_note")

    if daily_note:
        save_text_note(session["user_id"], daily_note)

    return redirect(url_for("profile"))


@app.route("/save_voice_recording", methods=["POST"])
def save_voice_recording():
    if "user_id" not in session:
        return redirect(url_for("login"))

    voice_file = request.files.get("voice_recording")

    if voice_file is None:
        return "No voice recording received."

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = secure_filename(
        f"user_{session['user_id']}_voice_{timestamp}.webm"
    )

    file_path = os.path.join(UPLOAD_FOLDER, filename)

    voice_file.save(file_path)

    save_voice_note(
        session["user_id"],
        filename,
        file_path
    )

    return redirect(url_for("profile"))


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)