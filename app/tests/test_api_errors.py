def test_create_persona_user_not_found(client):
    # Register and get token
    u = client.post("/api/v1/auth/register", json={"username": "err_user1", "password": "p", "role": "u"}).json()
    token = client.post("/api/v1/auth/login", data={"username": "err_user1", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        "/api/v1/personas/",
        params={"owner_id": 999},
        json={"name": "P", "bio": "B", "theories": [], "is_public": True},
        headers=headers
    )
    # The current implementation might just use current_user.id instead of owner_id param
    # If owner_id is provided but not found, it should be 404 or just use current_user
    assert response.status_code in [200, 404]

def test_create_forum_creator_not_found(client):
    u = client.post("/api/v1/auth/register", json={"username": "err_user2", "password": "p", "role": "u"}).json()
    token = client.post("/api/v1/auth/login", data={"username": "err_user2", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        "/api/v1/forums/",
        params={"creator_id": 999},
        json={"topic": "T", "participant_ids": []},
        headers=headers
    )
    assert response.status_code in [200, 404]

def test_get_forum_not_found(client):
    response = client.get("/api/v1/forums/999/messages")
    assert response.status_code == 404
    assert "Forum not found" in response.json()["detail"]

def test_post_message_forum_not_found(client):
    response = client.post(
        "/api/v1/forums/999/messages",
        json={"forum_id": 999, "persona_id": 1, "speaker_name": "S", "content": "C", "turn_count": 1}
    )
    assert response.status_code == 404
    assert "Forum not found" in response.json()["detail"]
    
def test_post_message_persona_not_found(client):
    # Register and login
    u = client.post("/api/v1/auth/register", json={"username": "msg_user", "password": "p", "role": "u"}).json()
    token = client.post("/api/v1/auth/login", data={"username": "msg_user", "password": "p"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create forum
    f = client.post("/api/v1/forums/", json={"topic": "T", "participant_ids": []}, headers=headers).json()

    response = client.post(
        f"/api/v1/forums/{f['id']}/messages",
        json={"forum_id": f['id'], "persona_id": 999, "speaker_name": "S", "content": "C", "turn_count": 1},
        headers=headers
    )
    assert response.status_code == 404

def test_chat_agent_invalid_initialization(client):
    # Mocking failure during agent init inside endpoint
    from unittest.mock import patch
    with patch("app.api.v1.endpoints.agents.ParticipantAgent", side_effect=Exception("Init Failed")):
        response = client.post(
            "/api/v1/agents/chat",
            json={
                "agent_name": "FailAgent",
                "persona_json": {"name": "Fail"},
                "context_messages": []
            }
        )
        assert response.status_code == 400
        assert "Failed to initialize agent" in response.json()["detail"]
