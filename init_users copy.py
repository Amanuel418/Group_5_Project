import sqlite3
from config import DB_PATH

def init_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create USERS table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Check if users already exist
    cur.execute("SELECT COUNT(*) FROM USERS")
    count = cur.fetchone()[0]
    
    if count == 0:
        # Add default users
        users = [
            ('admin', 'admin123', 'librarian'),
            ('staff', 'staff123', 'assistant')
        ]
        cur.executemany("INSERT INTO USERS (username, password, role) VALUES (?, ?, ?)", users)
        print("Created default users: admin (librarian), staff (assistant)")
    else:
        print("Users table already populated.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_users()
