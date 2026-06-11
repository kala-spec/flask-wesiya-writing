import sqlite3

DATABASE = "wesiya.db"

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

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

print("voice_notes table created successfully.")