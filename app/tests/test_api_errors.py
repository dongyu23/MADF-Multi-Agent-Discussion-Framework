def test_create_persona_user_not_found(client):
    response = client.post(
        "/api/v1/personas/",
        params={"owner_id": 999},
        json={"name": "P", "bio": "B", "theories": [], "is_public": True}
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]

def test_create_forum_creator_not_found(client):
    response = client.post(
        "/api/v1/forums/",
        params={"creator_id": 999},
        json={"topic": "T", "participant_ids": []}
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]

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
    # Create forum first
    u = client.post("/api/v1/users/", json={"username": "u", "password": "p", "role": "u"}).json()
    f = client.post("/api/v1/forums/", params={"creator_id": u["id"]}, json={"topic": "T", "participant_ids": []}).json()
    
    response = client.post(
        f"/api/v1/forums/{f['id']}/messages",
        json={"forum_id": f['id'], "persona_id": 999, "speaker_name": "S", "content": "C", "turn_count": 1}
    )
    assert response.status_code == 404
    assert "Persona not found" in response.json()["detail"]

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
