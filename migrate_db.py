import sqlite3


DB_NAME = "wesiya.db"


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    for column in columns:
        if column[1] == column_name:
            return True

    return False


def table_exists(cursor, table_name):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
    """, (table_name,))

    return cursor.fetchone() is not None


def add_column_if_missing(cursor, table_name, column_name, column_type):
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_type}
        """)
        print(f"Added column: {table_name}.{column_name}")
    else:
        print(f"Column already exists: {table_name}.{column_name}")


def migrate():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    add_column_if_missing(cursor, "users", "full_name", "TEXT")
    add_column_if_missing(cursor, "users", "phone_number", "TEXT")
    add_column_if_missing(cursor, "users", "date_of_birth", "TEXT")
    add_column_if_missing(cursor, "users", "height", "TEXT")

    # User profiles table, kept for older code compatibility
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT,
            phone_number TEXT,
            date_of_birth TEXT,
            height TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            daily_note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Voice notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Trusted members table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trusted_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            member_phone TEXT NOT NULL,
            relationship TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # If trusted_members already existed without default created_at,
    # we cannot safely ALTER that constraint in SQLite.
    # But we can make sure old NULL values are filled.
    if table_exists(cursor, "trusted_members"):
        if column_exists(cursor, "trusted_members", "created_at"):
            cursor.execute("""
                UPDATE trusted_members
                SET created_at = CURRENT_TIMESTAMP
                WHERE created_at IS NULL
            """)

    # Sync old users into user_profiles if missing
    cursor.execute("""
        INSERT OR IGNORE INTO user_profiles
        (
            user_id,
            full_name,
            phone_number,
            date_of_birth,
            height
        )
        SELECT
            id,
            full_name,
            phone_number,
            date_of_birth,
            height
        FROM users
    """)

    connection.commit()
    connection.close()

    print("Database migration completed successfully.")


if __name__ == "__main__":
    migrate()
