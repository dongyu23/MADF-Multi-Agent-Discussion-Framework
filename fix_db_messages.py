import sqlite3

DB_FILE = "madf.db"

def add_thoughts_column():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "thoughts" in columns:
            print("Column 'thoughts' already exists in 'messages' table.")
            return

        print("Adding 'thoughts' column to 'messages' table...")
        # SQLite supports ADD COLUMN
        cursor.execute("ALTER TABLE messages ADD COLUMN thoughts TEXT")
        
        conn.commit()
        print("Column added successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_thoughts_column()
