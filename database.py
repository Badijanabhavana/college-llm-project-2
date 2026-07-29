import sqlite3
import os

DB_NAME = os.getenv("DB_PATH", "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            mobile TEXT,
            password TEXT
        
        
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Chat History Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            user_msg TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Unanswered Questions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS unanswered (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Feedbacks Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            stars INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    
    # Create RAG Documents Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS rag_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            source TEXT DEFAULT 'admin',
            added_by TEXT DEFAULT 'admin',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add is_admin column if it doesn't exist (safe for existing databases)
    try:
        c.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create Contact Messages Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            subject TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def save_contact(name, email, subject, message):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO contact_messages (name, email, subject, message) VALUES (?, ?, ?, ?)',
        (name, email, subject, message)
    )
    conn.commit()
    conn.close()

    seed_dummy_data()

def seed_dummy_data():
    conn = get_db_connection()
    c = conn.cursor()

    users = [
        ("admin", "admin@jntugv.edu.in", "9999999999", "admin123"),
    ]
    for u in users:
        try:
            c.execute('INSERT INTO users (username, email, mobile, password) VALUES (?, ?, ?, ?)', u)
        except sqlite3.IntegrityError:
            pass
    # Mark admin user (runs after inserts so it works on fresh DBs too)
    c.execute('UPDATE users SET is_admin = 1 WHERE username = ?', ('admin',))

    conn.commit()
    conn.close()

# Users
def add_user(username, email, mobile, password):
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, email, mobile, password) VALUES (?, ?, ?, ?)',
                     (username, email, mobile, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_user(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(row) for row in users]

def delete_user(username):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def update_password(username, new_password):
    conn = get_db_connection()
    conn.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
    conn.commit()
    conn.close()

def get_user_is_admin(username):
    conn = get_db_connection()
    row = conn.execute('SELECT is_admin FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return bool(row and row['is_admin'])

# Chat
def log_chat(username, user_msg, bot_response):
    conn = get_db_connection()
    conn.execute('INSERT INTO chat_history (username, user_msg, bot_response) VALUES (?, ?, ?)',
                 (username, user_msg, bot_response))
    conn.commit()
    conn.close()

def get_chat_history(username=None):
    conn = get_db_connection()
    if username:
        chats = conn.execute('SELECT * FROM chat_history WHERE username = ? ORDER BY timestamp ASC', (username,)).fetchall()
    else:
        chats = conn.execute('SELECT * FROM chat_history ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(row) for row in chats]

# Unanswered
def add_unanswered(username, query):
    conn = get_db_connection()
    conn.execute('INSERT INTO unanswered (username, query) VALUES (?, ?)', (username, query))
    conn.commit()
    conn.close()

def get_unanswered():
    conn = get_db_connection()
    results = conn.execute('SELECT * FROM unanswered ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(row) for row in results]

# Feedback
def add_feedback(username, message, stars):
    conn = get_db_connection()
    conn.execute('INSERT INTO feedbacks (username, message, stars) VALUES (?, ?, ?)',
                 (username, message, stars))
    conn.commit()
    conn.close()

def get_feedbacks():
    conn = get_db_connection()
    results = conn.execute('SELECT * FROM feedbacks ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(row) for row in results]

# RAG Documents
def add_rag_document(title, content, source='admin', added_by='admin'):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO rag_documents (title, content, source, added_by) VALUES (?, ?, ?, ?)',
        (title, content, source, added_by)
    )
    conn.commit()
    conn.close()

def get_rag_documents():
    conn = get_db_connection()
    results = conn.execute('SELECT * FROM rag_documents ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(row) for row in results]

def delete_rag_document(doc_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM rag_documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
