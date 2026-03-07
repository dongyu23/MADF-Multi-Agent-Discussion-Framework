import pytest
from app.db.client import fetch_one

def test_forum_flow(client, db):
    # 1. Register & Login
    client.post("/api/v1/auth/register", json={"username": "flowuser", "password": "password", "role": "admin"})
    login_res = client.post("/api/v1/auth/login", data={"username": "flowuser", "password": "password"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Persona
    persona_data = {
        "name": "FlowPersona",
        "title": "Tester",
        "bio": "A test persona",
        "theories": ["Testing"],
        "stance": "Neutral",
        "system_prompt": "You are a test.",
        "is_public": True
    }
    p_res = client.post("/api/v1/personas/", json=persona_data, headers=headers)
    assert p_res.status_code == 200
    persona_id = p_res.json()["id"]
    
    # 3. Create Forum
    forum_data = {
        "topic": "Test Flow",
        "participant_ids": [persona_id],
        "duration_minutes": 10
    }
    f_res = client.post("/api/v1/forums/", json=forum_data, headers=headers)
    assert f_res.status_code == 200
    forum_id = f_res.json()["id"]
    
    # Verify Forum in DB
    forum = fetch_one(db.execute("SELECT * FROM forums WHERE id = ?", [forum_id]))
    assert forum is not None
    assert forum.topic == "Test Flow"
    
    # 4. Start Forum
    # Note: start_forum is async and uses BackgroundTasks/Scheduler. 
    # In synchronous test client, background tasks might run? 
    # Or we might need to mock scheduler.
    # The endpoint calls `await service.start_forum`.
    # `scheduler.start_forum` uses `asyncio.create_task`.
    # In pytest-asyncio, this might work if we use async client, but TestClient is sync.
    # However, for this integration test, we just want to see if the endpoint returns success.
    # We won't wait for the loop to actually run (it sleeps 2s).
    
    s_res = client.post(f"/api/v1/forums/{forum_id}/start", headers=headers)
    assert s_res.status_code == 200
    assert s_res.json()["status"] == "started"
    
    # Verify status changed (might take a split second, but database update is synchronous before loop starts?
    # No, `start_forum` calls `scheduler.start_forum` which runs `_run_forum_loop` in background.
    # The loop updates status to "running".
    # So immediately checking might show "pending".
    # Let's just check if we can post a message.
    
    # 5. Post Message
    msg_data = {
        "forum_id": forum_id,
        "persona_id": persona_id,
        "speaker_name": "FlowPersona",
        "content": "Hello World",
        "turn_count": 1
    }
    m_res = client.post(f"/api/v1/forums/{forum_id}/messages", json=msg_data, headers=headers)
    assert m_res.status_code == 200
    msg_id = m_res.json()["id"]
    
    # 6. Get Messages
    msgs_res = client.get(f"/api/v1/forums/{forum_id}/messages", headers=headers)
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()
    assert len(msgs) >= 1
    
    # Check if our message is present
    my_msg = next((m for m in msgs if m["content"] == "Hello World"), None)
    assert my_msg is not None
    assert my_msg["speaker_name"] == "FlowPersona"
    
    # Check if moderator opening is present (since we saw it in logs)
    # The moderator name is usually "主持人" or from DB.
    # In logs it was "各位来宾..."
    # We can check if there is a message with turn_count=0 and speaker_name="主持人" (default) or "System"
    mod_msg = next((m for m in msgs if "各位" in m["content"] or m["speaker_name"] == "主持人"), None)
    # It might take a few seconds for LLM to reply, so it might not be there yet in a fast test run.
    # But the previous failure showed it WAS there.
    if mod_msg:
        assert len(mod_msg["content"]) > 10

    # 7. Get Logs
    logs_res = client.get(f"/api/v1/forums/{forum_id}/logs", headers=headers)
    assert logs_res.status_code == 200
    # Logs might be empty if loop hasn't run, but let's check structure
    assert isinstance(logs_res.json(), list)

def test_unauthorized_access(client):
    # Try to create forum without token
    res = client.post("/api/v1/forums/", json={"topic": "Fail"})
    assert res.status_code == 401
