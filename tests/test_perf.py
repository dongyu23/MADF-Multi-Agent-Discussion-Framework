import pytest
import time
from app.db.client import fetch_one

def test_message_spam(client, db):
    # 1. Register & Login
    client.post("/api/v1/auth/register", json={"username": "perfuser", "password": "password", "role": "admin"})
    login_res = client.post("/api/v1/auth/login", data={"username": "perfuser", "password": "password"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Persona
    persona_data = {"name": "PerfPersona", "is_public": True}
    p_res = client.post("/api/v1/personas/", json=persona_data, headers=headers)
    persona_id = p_res.json()["id"]
    
    # 3. Create Forum
    forum_data = {"topic": "Perf Test", "participant_ids": [persona_id]}
    f_res = client.post("/api/v1/forums/", json=forum_data, headers=headers)
    forum_id = f_res.json()["id"]
    
    # 4. Spam Messages
    N_MESSAGES = 50
    start_time = time.time()
    
    for i in range(N_MESSAGES):
        msg_data = {
            "forum_id": forum_id,
            "persona_id": persona_id,
            "speaker_name": "PerfPersona",
            "content": f"Message {i}",
            "turn_count": i
        }
        res = client.post(f"/api/v1/forums/{forum_id}/messages", json=msg_data, headers=headers)
        assert res.status_code == 200
        
    duration = time.time() - start_time
    print(f"\nPosted {N_MESSAGES} messages in {duration:.2f}s ({N_MESSAGES/duration:.2f} msg/s)")
    
    # 5. Verify Count
    rs = db.execute("SELECT COUNT(*) as count FROM messages WHERE forum_id = ?", [forum_id])
    count = fetch_one(rs).count
    # Note: moderator might post opening too, so count >= N_MESSAGES
    assert count >= N_MESSAGES

def test_invalid_data(client, db):
    # Test DB constraints
    # Try to create user with same username
    client.post("/api/v1/auth/register", json={"username": "unique", "password": "pwd", "role": "user"})
    res = client.post("/api/v1/auth/register", json={"username": "unique", "password": "pwd", "role": "user"})
    assert res.status_code == 400 # Application logic handles this
    
    # Direct DB access to verify unique constraint
    try:
        db.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ["unique", "hash", "user"])
        assert False, "Should raise IntegrityError"
    except Exception as e:
        # libsql_client.LibsqlError or similar
        assert "UNIQUE constraint failed" in str(e) or "constraint failed" in str(e) or "unique" in str(e).lower()
