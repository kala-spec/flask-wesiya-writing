from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
import requests
import os
import json

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

@app.route("/api/translate-page", methods=["POST"])
def translate_page():
    data = request.get_json()

    target_language = data.get("target_language")
    texts = data.get("texts", [])

    if not target_language or not texts:
        return jsonify({
            "success": False,
            "message": "Target language and texts are required."
        }), 400

    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not gemini_api_key:
        return jsonify({
            "success": False,
            "message": "Gemini API key is not configured."
        }), 500

    texts = [str(text).strip() for text in texts if str(text).strip()]
    texts = texts[:60]

    prompt = f"""
You are a translation engine.

Translate this JSON array into {target_language}.
Return ONLY valid JSON.
Return the result in this exact format:

{{
  "translations": ["translated text 1", "translated text 2"]
}}

Rules:
- Keep the same order.
- Keep the same number of items.
- Do not add explanations.
- Do not use markdown.
- Do not wrap response in code blocks.

JSON array:
{json.dumps(texts, ensure_ascii=False)}
"""

    models = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
    ]

    last_error_message = "Translation service is temporarily unavailable."

    for model in models:
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": gemini_api_key,
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                timeout=45,
            )

            if response.status_code != 200:
                print(f"Gemini model failed: {model}")
                print("Gemini API status:", response.status_code)
                print("Gemini API response:", response.text)

                if response.status_code == 503:
                    last_error_message = "Gemini is busy right now. Please try again in a minute."
                    continue

                last_error_message = "Translation service returned an error."
                continue

            result = response.json()

            translated_text = (
                result
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            if not translated_text:
                print(f"Empty Gemini response from model: {model}")
                last_error_message = "Translation response was empty."
                continue

            translated_text = translated_text.replace("```json", "")
            translated_text = translated_text.replace("```", "")
            translated_text = translated_text.strip()

            parsed = json.loads(translated_text)
            translated_list = parsed.get("translations", [])

            if not isinstance(translated_list, list):
                last_error_message = "Translation response was not valid."
                continue

            return jsonify({
                "success": True,
                "translations": translated_list,
                "model_used": model
            })

        except Exception as error:
            print(f"Translation error using {model}:", error)
            last_error_message = "Translation failed. Please try again."
            continue

    return jsonify({
        "success": False,
        "message": last_error_message
    }), 503
    
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
        SELECT
            id,
            filename,
            created_at
        FROM voice_notes
        WHERE user_id = ?
        ORDER BY id DESC
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
        return redirect("/")

    conn = sqlite3.connect("wesiya.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, email, full_name, phone_number, date_of_birth, height
        FROM users
        WHERE id = ?
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
    SELECT id, daily_note, created_at
    FROM notes
    WHERE user_id = ?
    ORDER BY id DESC
""", (session["user_id"],))

    notes = cursor.fetchall()

    cursor.execute("""
        SELECT id, filename, created_at
        FROM voice_notes
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],))

    voice_notes = cursor.fetchall()

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        notes=notes,
        voice_notes=voice_notes
    )

@app.route("/about")
def about():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("wesiya.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, email, full_name, phone_number, date_of_birth, height
        FROM users
        WHERE id = ?
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT id, member_name, member_phone, relationship
        FROM trusted_members
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],))

    trusted_members = cursor.fetchall()

    conn.close()

    return render_template(
        "about.html",
        user=user,
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
def signup():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    full_name = request.form.get("full_name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip()
    height = request.form.get("height", "").strip()

    if not email or not password:
        return render_template(
            "login.html",
            error="Email and password are required.",
            default_form="signup",
            signup_email=email
        )

    if not full_name or not phone_number or not date_of_birth or not height:
        return render_template(
            "login.html",
            error="Please complete your personal information.",
            default_form="signup",
            signup_email=email
        )

    member_names = request.form.getlist("member_name[]")
    member_phones = request.form.getlist("member_phone[]")
    relationships = request.form.getlist("relationship[]")

    complete_members = []
    min_members = 2
    max_members = 5

    for index in range(min(len(member_names), max_members)):
        member_name = member_names[index].strip()

        member_phone = ""
        relationship = ""

        if index < len(member_phones):
            member_phone = member_phones[index].strip()

        if index < len(relationships):
            relationship = relationships[index].strip()

        if member_name and member_phone and relationship:
            complete_members.append({
                "member_name": member_name,
                "member_phone": member_phone,
                "relationship": relationship
            })

    if len(complete_members) < min_members:
        return render_template(
            "login.html",
            error="Please add at least 2 complete trusted family members.",
            default_form="signup",
            signup_email=email
        )

    conn = sqlite3.connect("wesiya.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template(
                "login.html",
                error="This email is already registered. Please login instead.",
                default_form="login",
                login_email=email
            )

        cursor.execute("""
            INSERT INTO users
            (
                email,
                password,
                created_at,
                full_name,
                phone_number,
                date_of_birth,
                height
            )
            VALUES (?, ?, datetime('now'), ?, ?, ?, ?)
        """, (
            email,
            password,
            full_name,
            phone_number,
            date_of_birth,
            height
        ))

        user_id = cursor.lastrowid

        for member in complete_members:
            cursor.execute("""
    INSERT INTO trusted_members
    (
        user_id,
        member_name,
        member_phone,
        relationship,
        created_at
    )
    VALUES (?, ?, ?, ?, datetime('now'))
""", (
    user_id,
    member["member_name"],
    member["member_phone"],
    member["relationship"]
))

        conn.commit()

        session["user_id"] = user_id
        session["email"] = email

        conn.close()
        return redirect("/home")

    except Exception as error:
        conn.rollback()
        conn.close()

        print("Signup error:", error)

        return render_template(
            "login.html",
            error=f"Signup error: {error}",
            default_form="signup",
            signup_email=email
        )
@app.route("/trusted-member/add", methods=["POST"])
def add_trusted_member():
    if "user_id" not in session:
        return redirect("/")

    member_name = request.form.get("member_name", "").strip()
    member_phone = request.form.get("member_phone", "").strip()
    relationship = request.form.get("relationship", "").strip()

    if not member_name or not member_phone or not relationship:
        return redirect("/about")

    conn = sqlite3.connect("wesiya.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM trusted_members
        WHERE user_id = ?
    """, (session["user_id"],))

    member_count = cursor.fetchone()[0]

    if member_count >= 5:
        conn.close()
        return redirect("/about")

    cursor.execute("""
    INSERT INTO trusted_members
    (
        user_id,
        member_name,
        member_phone,
        relationship,
        created_at
    )
    VALUES (?, ?, ?, ?, datetime('now'))
""", (
    session["user_id"],
    member_name,
    member_phone,
    relationship
))

    conn.commit()
    conn.close()

    return redirect("/about")


@app.route("/trusted-member/edit/<int:member_id>", methods=["POST"])
def edit_trusted_member(member_id):
    if "user_id" not in session:
        return redirect("/")

    member_name = request.form.get("member_name", "").strip()
    member_phone = request.form.get("member_phone", "").strip()
    relationship = request.form.get("relationship", "").strip()

    if not member_name or not member_phone or not relationship:
        return redirect("/about")

    conn = sqlite3.connect("wesiya.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trusted_members
        SET member_name = ?, member_phone = ?, relationship = ?
        WHERE id = ? AND user_id = ?
    """, (
        member_name,
        member_phone,
        relationship,
        member_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect("/about")


@app.route("/trusted-member/delete/<int:member_id>", methods=["POST"])
def delete_trusted_member(member_id):
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("wesiya.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM trusted_members
        WHERE user_id = ?
    """, (session["user_id"],))

    member_count = cursor.fetchone()[0]

    if member_count <= 2:
        conn.close()
        return redirect("/about")

    cursor.execute("""
        DELETE FROM trusted_members
        WHERE id = ? AND user_id = ?
    """, (member_id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect("/about")
@app.route("/note/edit/<int:note_id>", methods=["POST"])
def edit_note(note_id):
    if "user_id" not in session:
        return redirect("/")

    updated_note = request.form.get("note", "").strip()

    if not updated_note:
        return redirect("/profile")

    conn = sqlite3.connect("wesiya.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE notes
    SET daily_note = ?
    WHERE id = ? AND user_id = ?
""", (
    updated_note,
    note_id,
    session["user_id"]
))

    conn.commit()
    conn.close()

    return redirect("/profile")


@app.route("/note/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("wesiya.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM notes
        WHERE id = ? AND user_id = ?
    """, (
        note_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect("/profile")

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
    owner_full_name = request.form.get("owner_full_name", "").strip()

    member_name = request.form.get("member_name", "").strip()
    member_phone = request.form.get("member_phone", "").strip()
    relationship = request.form.get("relationship", "").strip()

    if not owner_full_name or not member_name or not member_phone or not relationship:
        return render_template(
            "trusted_access.html",
            error="Please complete all required fields."
        )

    connection = get_db_connection()
    owner = connection.execute("""
    SELECT
        users.id,
        users.email,
        COALESCE(users.full_name, user_profiles.full_name) AS full_name
    FROM users
    LEFT JOIN user_profiles ON users.id = user_profiles.user_id
    WHERE
        LOWER(TRIM(users.full_name)) = LOWER(TRIM(?))
        OR LOWER(TRIM(user_profiles.full_name)) = LOWER(TRIM(?))
    LIMIT 1
""", (owner_full_name, owner_full_name)).fetchone()

    if owner is None:
        connection.close()
        return render_template(
            "trusted_access.html",
            error="Account owner information was not found."
        )

    trusted_member = connection.execute("""
        SELECT id
        FROM trusted_members
        WHERE user_id = ?
        AND LOWER(member_name) = LOWER(?)
        AND member_phone = ?
        AND LOWER(relationship) = LOWER(?)
        LIMIT 1
    """, (
        owner["id"],
        member_name,
        member_phone,
        relationship
    )).fetchone()

    if trusted_member is None:
        connection.close()
        return render_template(
            "trusted_access.html",
            error="Trusted member information does not match this account."
        )

    session["trusted_access_user_id"] = owner["id"]
    session["trusted_access_name"] = owner["full_name"]

    connection.close()

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