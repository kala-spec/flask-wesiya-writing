from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
import os


app = Flask(__name__)
app.secret_key = "my_secret_key_for_learning"

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
    ]
)

DATABASE = "wesiya.db"
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# =========================
# DATABASE CONNECTION
# =========================

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            height TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trusted_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            member_phone TEXT NOT NULL,
            relationship TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    connection.commit()
    connection.close()


# =========================
# USER FUNCTIONS
# =========================

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


# =========================
# NOTE FUNCTIONS
# =========================

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


# =========================
# VOICE FUNCTIONS
# =========================

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


# =========================
# PERSONAL PROFILE FUNCTIONS
# =========================

def save_user_profile(user_id, full_name, phone_number, date_of_birth, height):
    connection = get_db_connection()

    existing_profile = connection.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if existing_profile:
        connection.execute("""
            UPDATE user_profiles
            SET full_name = ?, phone_number = ?, date_of_birth = ?, height = ?
            WHERE user_id = ?
        """, (
            full_name,
            phone_number,
            date_of_birth,
            height,
            user_id
        ))
    else:
        connection.execute("""
            INSERT INTO user_profiles
            (user_id, full_name, phone_number, date_of_birth, height, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            full_name,
            phone_number,
            date_of_birth,
            height,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    connection.commit()
    connection.close()


def save_trusted_members(user_id, trusted_members):
    connection = get_db_connection()

    connection.execute(
        "DELETE FROM trusted_members WHERE user_id = ?",
        (user_id,)
    )

    for member in trusted_members:
        connection.execute("""
            INSERT INTO trusted_members
            (user_id, member_name, member_phone, relationship, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            member["member_name"],
            member["member_phone"],
            member["relationship"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    connection.commit()
    connection.close()


def get_user_profile(user_id):
    connection = get_db_connection()

    profile = connection.execute("""
        SELECT * FROM user_profiles
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    connection.close()
    return profile


def get_trusted_members(user_id):
    connection = get_db_connection()

    members = connection.execute("""
        SELECT * FROM trusted_members
        WHERE user_id = ?
        ORDER BY id ASC
    """, (user_id,)).fetchall()

    connection.close()
    return members


# =========================
# OLD FLASK HTML ROUTES
# =========================

@app.route("/")
def login():
    return render_template("login.html", default_form="login")


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


@app.route("/about")
def about():
    if "user_id" not in session:
        return redirect(url_for("login"))

    profile = get_user_profile(session["user_id"])
    trusted_members = get_trusted_members(session["user_id"])

    return render_template(
        "about.html",
        email=session.get("email"),
        profile=profile,
        trusted_members=trusted_members
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
            signup_message="No account found with this email. Please create an account first.",
            signup_email=email,
            default_form="signup"
        )

    if user["password"] != password:
        return render_template(
            "login.html",
            error="Wrong password. Please try again.",
            login_email=email,
            default_form="login"
        )

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return redirect(url_for("home"))


@app.route("/signup", methods=["POST"])
def signup_user():
    email = request.form.get("email")
    password = request.form.get("password")

    full_name = request.form.get("full_name")
    phone_number = request.form.get("phone_number")
    date_of_birth = request.form.get("date_of_birth")
    height = request.form.get("height")

    trusted_members = [
        {
            "member_name": request.form.get("member_name_1"),
            "member_phone": request.form.get("member_phone_1"),
            "relationship": request.form.get("relationship_1")
        },
        {
            "member_name": request.form.get("member_name_2"),
            "member_phone": request.form.get("member_phone_2"),
            "relationship": request.form.get("relationship_2")
        },
        {
            "member_name": request.form.get("member_name_3"),
            "member_phone": request.form.get("member_phone_3"),
            "relationship": request.form.get("relationship_3")
        }
    ]

    if not email or not password:
        return render_template(
            "login.html",
            error="Email and password are required.",
            default_form="signup"
        )

    if not full_name or not phone_number or not date_of_birth or not height:
        return render_template(
            "login.html",
            error="Please complete your personal information.",
            default_form="signup"
        )

    valid_members = []

    for member in trusted_members:
        if member["member_name"] and member["member_phone"] and member["relationship"]:
            valid_members.append(member)

    if len(valid_members) < 3:
        return render_template(
            "login.html",
            error="Please add at least 3 trusted or family members.",
            default_form="signup"
        )

    existing_user = find_user_by_email(email)

    if existing_user is not None:
        return render_template(
            "login.html",
            signup_message="This account already exists. Please login instead.",
            login_email=email,
            default_form="login"
        )

    create_user(email, password)
    new_user = find_user_by_email(email)

    save_user_profile(
        new_user["id"],
        full_name,
        phone_number,
        date_of_birth,
        height
    )

    save_trusted_members(new_user["id"], valid_members)

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

    save_voice_note(session["user_id"], filename, file_path)

    return redirect(url_for("profile"))

@app.route("/trusted-access")
def trusted_access():
    return render_template("trusted_access.html")


@app.route("/trusted-login", methods=["POST"])
def trusted_login():
    owner_full_name = request.form.get("owner_full_name")
    owner_email = request.form.get("owner_email")

    member_name = request.form.get("member_name")
    member_phone = request.form.get("member_phone")
    relationship = request.form.get("relationship")

    connection = get_db_connection()

    owner = connection.execute("""
        SELECT users.id, users.email, user_profiles.full_name
        FROM users
        JOIN user_profiles ON users.id = user_profiles.user_id
        WHERE users.email = ?
        AND LOWER(user_profiles.full_name) = LOWER(?)
    """, (owner_email, owner_full_name)).fetchone()

    if owner is None:
        connection.close()
        return render_template(
            "trusted_access.html",
            error="Account owner information was not found."
        )

    trusted_member = connection.execute("""
        SELECT * FROM trusted_members
        WHERE user_id = ?
        AND LOWER(member_name) = LOWER(?)
        AND member_phone = ?
        AND LOWER(relationship) = LOWER(?)
    """, (
        owner["id"],
        member_name,
        member_phone,
        relationship
    )).fetchone()

    connection.close()

    if trusted_member is None:
        return render_template(
            "trusted_access.html",
            error="Trusted member information does not match our records."
        )

    session["trusted_access_user_id"] = owner["id"]
    session["trusted_access_email"] = owner["email"]
    session["trusted_access_name"] = owner["full_name"]

    return redirect(url_for("trusted_view"))


@app.route("/trusted-view")
def trusted_view():
    if "trusted_access_user_id" not in session:
        return redirect(url_for("trusted_access"))

    owner_user_id = session["trusted_access_user_id"]

    profile = get_user_profile(owner_user_id)
    trusted_members = get_trusted_members(owner_user_id)
    notes = get_text_notes_by_user(owner_user_id)
    voice_notes = get_voice_notes_by_user(owner_user_id)

    return render_template(
        "trusted_view.html",
        email=session.get("trusted_access_email"),
        owner_name=session.get("trusted_access_name"),
        profile=profile,
        trusted_members=trusted_members,
        notes=notes,
        voice_notes=voice_notes
    )


@app.route("/trusted-logout")
def trusted_logout():
    session.pop("trusted_access_user_id", None)
    session.pop("trusted_access_email", None)
    session.pop("trusted_access_name", None)

    return redirect(url_for("login"))

# =========================
# REACT API ROUTES
# =========================

@app.route("/api/check-session", methods=["GET"])
def api_check_session():
    if "user_id" in session:
        return jsonify({
            "success": True,
            "email": session.get("email")
        })

    return jsonify({
        "success": False,
        "message": "Not logged in"
    }), 401


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    user = find_user_by_email(email)

    if user is None:
        return jsonify({
            "success": False,
            "message": "No account found with this email. Please sign up first."
        }), 404

    if user["password"] != password:
        return jsonify({
            "success": False,
            "message": "Wrong password. Please try again."
        }), 401

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify({
        "success": True,
        "message": "Login successful",
        "email": user["email"]
    })


@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    full_name = data.get("full_name")
    phone_number = data.get("phone_number")
    date_of_birth = data.get("date_of_birth")
    height = data.get("height")

    trusted_members = data.get("trusted_members", [])

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    if not full_name or not phone_number or not date_of_birth or not height:
        return jsonify({
            "success": False,
            "message": "Please complete your personal information."
        }), 400

    valid_members = []

    for member in trusted_members:
        member_name = member.get("member_name")
        member_phone = member.get("member_phone")
        relationship = member.get("relationship")

        if member_name and member_phone and relationship:
            valid_members.append({
                "member_name": member_name,
                "member_phone": member_phone,
                "relationship": relationship
            })

    if len(valid_members) < 3:
        return jsonify({
            "success": False,
            "message": "Please add at least 3 trusted or family members."
        }), 400

    existing_user = find_user_by_email(email)

    if existing_user is not None:
        return jsonify({
            "success": False,
            "message": "This account already exists. Please login instead."
        }), 409

    create_user(email, password)
    new_user = find_user_by_email(email)

    save_user_profile(
        new_user["id"],
        full_name,
        phone_number,
        date_of_birth,
        height
    )

    save_trusted_members(new_user["id"], valid_members)

    session["user_id"] = new_user["id"]
    session["email"] = new_user["email"]

    return jsonify({
        "success": True,
        "message": "Signup successful",
        "email": new_user["email"]
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    })


@app.route("/api/submit-note", methods=["POST"])
def api_submit_note():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Not logged in"
        }), 401

    data = request.get_json()
    daily_note = data.get("daily_note")

    if not daily_note:
        return jsonify({
            "success": False,
            "message": "Writing update is required"
        }), 400

    save_text_note(session["user_id"], daily_note)

    return jsonify({
        "success": True,
        "message": "Writing update saved successfully"
    })


@app.route("/api/profile", methods=["GET"])
def api_profile():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Not logged in"
        }), 401

    notes = get_text_notes_by_user(session["user_id"])
    voice_notes = get_voice_notes_by_user(session["user_id"])

    return jsonify({
        "success": True,
        "email": session.get("email"),
        "notes": [dict(note) for note in notes],
        "voice_notes": [dict(voice) for voice in voice_notes]
    })


@app.route("/api/about", methods=["GET"])
def api_about():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Not logged in"
        }), 401

    profile = get_user_profile(session["user_id"])
    trusted_members = get_trusted_members(session["user_id"])

    return jsonify({
        "success": True,
        "email": session.get("email"),
        "profile": dict(profile) if profile else None,
        "trusted_members": [dict(member) for member in trusted_members]
    })


@app.route("/api/save-voice", methods=["POST"])
def api_save_voice():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Not logged in"
        }), 401

    voice_file = request.files.get("voice_recording")

    if voice_file is None:
        return jsonify({
            "success": False,
            "message": "No voice recording received"
        }), 400

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = secure_filename(
        f"user_{session['user_id']}_voice_{timestamp}.webm"
    )

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    voice_file.save(file_path)

    save_voice_note(session["user_id"], filename, file_path)

    return jsonify({
        "success": True,
        "message": "Voice update saved successfully",
        "filename": filename
    })


# =========================
# START APP
# =========================

create_tables()


if __name__ == "__main__":
    app.run(debug=True)