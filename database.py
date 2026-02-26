import sqlite3
import json
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_FILE = "madf.db"

class DatabaseManager:
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        # Enable Foreign Key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        """Initialize the database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin', 'god')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Personas Table (Characters)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            title TEXT,
            bio TEXT,
            theories TEXT, -- JSON Array
            stance TEXT,
            system_prompt TEXT,
            is_public BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        # Index for faster lookup of user's personas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_personas_owner ON personas(owner_id);")

        # 3. Forums Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS forums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            creator_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'finished')),
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME,
            FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_forums_creator ON forums(creator_id);")

        # 4. Forum Participants (Many-to-Many)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS forum_participants (
            forum_id INTEGER NOT NULL,
            persona_id INTEGER NOT NULL,
            PRIMARY KEY (forum_id, persona_id),
            FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE,
            FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE
        );
        """)

        # 5. Messages Table (Posts)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forum_id INTEGER NOT NULL,
            persona_id INTEGER, -- NULL for Moderator/System
            speaker_name TEXT NOT NULL,
            content TEXT NOT NULL,
            turn_count INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE,
            FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE SET NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_forum ON messages(forum_id);")

        # 6. Observations Table (User watching a forum)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            forum_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            left_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_user_forum ON observations(user_id, forum_id);")

        # 7. God Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS god_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            god_user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT, -- JSON
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (god_user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_file}")

class UserManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def register(self, username, password, role='user'):
        conn = self.db.get_connection()
        try:
            # Simple hash for demo; in production use bcrypt/argon2
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, pwd_hash, role)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def login(self, username, password):
        conn = self.db.get_connection()
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ?",
            (username, pwd_hash)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_id(self, user_id):
        conn = self.db.get_connection()
        user = conn.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None

class PersonaManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_persona(self, owner_id, persona_data: Dict[str, Any]):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        theories_json = json.dumps(persona_data.get('theories', []))
        
        cursor.execute("""
            INSERT INTO personas (owner_id, name, title, bio, theories, stance, system_prompt, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            owner_id,
            persona_data['name'],
            persona_data.get('title'),
            persona_data.get('bio'),
            theories_json,
            persona_data.get('stance'),
            persona_data.get('system_prompt'),
            persona_data.get('is_public', 0)
        ))
        conn.commit()
        pid = cursor.lastrowid
        conn.close()
        return pid

    def get_persona(self, persona_id):
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone()
        conn.close()
        if row:
            d = dict(row)
            d['theories'] = json.loads(d['theories']) if d['theories'] else []
            return d
        return None

    def list_personas(self, owner_id=None):
        conn = self.db.get_connection()
        if owner_id:
            rows = conn.execute("SELECT * FROM personas WHERE owner_id = ?", (owner_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM personas WHERE is_public = 1").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_persona(self, persona_id, updates: Dict[str, Any]):
        allowed_fields = {'name', 'title', 'bio', 'theories', 'stance', 'system_prompt', 'is_public'}
        fields = []
        values = []
        
        for k, v in updates.items():
            if k in allowed_fields:
                fields.append(f"{k} = ?")
                if k == 'theories' and isinstance(v, list):
                    values.append(json.dumps(v))
                else:
                    values.append(v)
        
        if not fields:
            return False
            
        values.append(persona_id)
        sql = f"UPDATE personas SET {', '.join(fields)} WHERE id = ?"
        
        conn = self.db.get_connection()
        conn.execute(sql, values)
        conn.commit()
        conn.close()
        return True

    def delete_persona(self, persona_id):
        conn = self.db.get_connection()
        conn.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
        conn.commit()
        conn.close()

class ForumManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_forum(self, creator_id, topic, participant_ids: List[int]):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO forums (topic, creator_id) VALUES (?, ?)", (topic, creator_id))
            forum_id = cursor.lastrowid
            
            for pid in participant_ids:
                cursor.execute("INSERT INTO forum_participants (forum_id, persona_id) VALUES (?, ?)", (forum_id, pid))
            
            conn.commit()
            return forum_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def add_message(self, forum_id, persona_id, speaker_name, content, turn_count):
        conn = self.db.get_connection()
        conn.execute("""
            INSERT INTO messages (forum_id, persona_id, speaker_name, content, turn_count)
            VALUES (?, ?, ?, ?, ?)
        """, (forum_id, persona_id, speaker_name, content, turn_count))
        conn.commit()
        conn.close()

    def get_forum_history(self, forum_id):
        conn = self.db.get_connection()
        rows = conn.execute("SELECT * FROM messages WHERE forum_id = ? ORDER BY id ASC", (forum_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def close_forum(self, forum_id):
        conn = self.db.get_connection()
        conn.execute("UPDATE forums SET status = 'finished', end_time = ? WHERE id = ?", (datetime.now(), forum_id))
        conn.commit()
        conn.close()

class GodManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def log_action(self, god_user_id, action, details: Dict):
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO god_logs (god_user_id, action, details) VALUES (?, ?, ?)",
            (god_user_id, action, json.dumps(details))
        )
        conn.commit()
        conn.close()

# Singleton instance for easy import
db = DatabaseManager()

if __name__ == "__main__":
    # Initialize DB when running this script directly
    db.init_db()
