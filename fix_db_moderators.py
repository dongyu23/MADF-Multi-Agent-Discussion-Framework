import sqlite3

DB_FILE = "madf.db"

def upgrade_db_moderators():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 1. Create moderators table
        cursor.execute("PRAGMA table_info(moderators)")
        if not cursor.fetchall():
            print("Creating 'moderators' table...")
            cursor.execute("""
                CREATE TABLE moderators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    title VARCHAR,
                    bio TEXT,
                    system_prompt TEXT,
                    greeting_template TEXT,
                    closing_template TEXT,
                    summary_template TEXT,
                    creator_id INTEGER NOT NULL,
                    created_at DATETIME,
                    FOREIGN KEY(creator_id) REFERENCES users(id)
                )
            """)
            print("Table 'moderators' created.")

        # 2. Add moderator_id to forums table
        cursor.execute("PRAGMA table_info(forums)")
        columns = [info[1] for info in cursor.fetchall()]
        if "moderator_id" not in columns:
            print("Adding 'moderator_id' column to 'forums' table...")
            cursor.execute("ALTER TABLE forums ADD COLUMN moderator_id INTEGER REFERENCES moderators(id)")
            print("Column 'moderator_id' added to 'forums'.")

        # 3. Add moderator_id to messages table
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        if "moderator_id" not in columns:
            print("Adding 'moderator_id' column to 'messages' table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN moderator_id INTEGER REFERENCES moderators(id)")
            print("Column 'moderator_id' added to 'messages'.")

        conn.commit()
        print("Database upgrade completed successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_db_moderators()
