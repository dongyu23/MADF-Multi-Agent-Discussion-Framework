import sqlite3

DB_FILE = "madf.db"

def fix_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Disable foreign keys
    cursor.execute("PRAGMA foreign_keys=OFF")
    
    # 2. Start transaction
    cursor.execute("BEGIN TRANSACTION")
    
    try:
        # 3. Get existing table schema to verify
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='forums'")
        row = cursor.fetchone()
        if not row:
            print("Table 'forums' not found.")
            return
            
        create_sql = row[0]
        print(f"Original Schema: {create_sql}")
        
        # 4. Rename old table
        cursor.execute("ALTER TABLE forums RENAME TO forums_old")
        
        # 5. Create new table without the CHECK constraint
        # Using a generic definition that matches the SQLAlchemy model
        new_create_sql = """
        CREATE TABLE forums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic VARCHAR NOT NULL,
            creator_id INTEGER NOT NULL,
            status VARCHAR DEFAULT 'active',
            summary_history TEXT DEFAULT '[]',
            start_time DATETIME,
            end_time DATETIME,
            duration_minutes INTEGER DEFAULT 30,
            FOREIGN KEY(creator_id) REFERENCES users(id)
        );
        """
        
        cursor.execute(new_create_sql)
        
        # 6. Copy data
        # We assume columns match. If status was invalid before, it wouldn't be in the DB.
        # But we are fixing it so we can insert new invalid statuses.
        cursor.execute("""
            INSERT INTO forums (id, topic, creator_id, status, summary_history, start_time, end_time, duration_minutes)
            SELECT id, topic, creator_id, status, summary_history, start_time, end_time, duration_minutes
            FROM forums_old
        """)
        
        # 7. Drop old table
        cursor.execute("DROP TABLE forums_old")
        
        # 8. Recreate index
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_forums_id ON forums (id)")
        
        conn.commit()
        print("Database fixed successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_db()
