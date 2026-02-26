import sqlite3
import pytest
import os
from database import DatabaseManager, UserManager, PersonaManager, ForumManager

TEST_DB = "test_madf.db"

@pytest.fixture
def db_manager():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    manager = DatabaseManager(TEST_DB)
    manager.init_db()
    yield manager
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_user_lifecycle(db_manager):
    user_mgr = UserManager(db_manager)
    
    # 1. Register
    assert user_mgr.register("testuser", "password123", "user") == True
    assert user_mgr.register("testuser", "password123") == False # Duplicate
    
    # 2. Login
    user = user_mgr.login("testuser", "password123")
    assert user is not None
    assert user['username'] == "testuser"
    assert user['role'] == "user"
    
    assert user_mgr.login("testuser", "wrongpass") is None

def test_persona_lifecycle(db_manager):
    user_mgr = UserManager(db_manager)
    user_mgr.register("owner", "pass")
    owner = user_mgr.login("owner", "pass")
    owner_id = owner['id']
    
    persona_mgr = PersonaManager(db_manager)
    
    # 1. Create
    p_data = {
        "name": "Socrates",
        "title": "Philosopher",
        "bio": "Known for Socratic method.",
        "theories": ["Dialectic", "Ethics"],
        "stance": "Question everything",
        "system_prompt": "You are Socrates.",
        "is_public": 1
    }
    pid = persona_mgr.create_persona(owner_id, p_data)
    assert pid is not None
    
    # 2. Read
    p = persona_mgr.get_persona(pid)
    assert p['name'] == "Socrates"
    assert "Dialectic" in p['theories']
    
    # 3. Update
    persona_mgr.update_persona(pid, {"title": "Great Philosopher"})
    p = persona_mgr.get_persona(pid)
    assert p['title'] == "Great Philosopher"
    
    # 4. Delete
    persona_mgr.delete_persona(pid)
    assert persona_mgr.get_persona(pid) is None

def test_forum_flow(db_manager):
    user_mgr = UserManager(db_manager)
    user_mgr.register("host", "pass")
    host_id = user_mgr.login("host", "pass")['id']
    
    persona_mgr = PersonaManager(db_manager)
    p1 = persona_mgr.create_persona(host_id, {"name": "P1", "theories": []})
    p2 = persona_mgr.create_persona(host_id, {"name": "P2", "theories": []})
    
    forum_mgr = ForumManager(db_manager)
    
    # 1. Create Forum
    fid = forum_mgr.create_forum(host_id, "AI Future", [p1, p2])
    assert fid is not None
    
    # 2. Add Messages
    forum_mgr.add_message(fid, p1, "P1", "Hello", 1)
    forum_mgr.add_message(fid, p2, "P2", "Hi there", 2)
    
    # 3. History
    history = forum_mgr.get_forum_history(fid)
    assert len(history) == 2
    assert history[0]['content'] == "Hello"
    
    # 4. Close
    forum_mgr.close_forum(fid)
    
    # 5. Check FK Constraints (Delete User -> Delete Forum?)
    # Since we set ON DELETE CASCADE, deleting the user should delete their forums
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (host_id,))
    conn.commit()
    
    row = conn.execute("SELECT * FROM forums WHERE id = ?", (fid,)).fetchone()
    assert row is None # Should be cascaded

if __name__ == "__main__":
    pytest.main([__file__])
