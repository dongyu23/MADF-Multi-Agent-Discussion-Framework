import pytest
from app.db.client import fetch_one
from app.core.hashing import Hasher

def test_register_user(client, db):
    # Ensure clean state (if needed, but session fixture handles global setup)
    # We might need to clean up the table if previous tests run.
    # For now, let's assume we start fresh or clear tables.
    db.execute("DELETE FROM users")
    
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpassword", "role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

    # Verify user in DB
    rs = db.execute("SELECT * FROM users WHERE username = ?", ["testuser"])
    user = fetch_one(rs)
    assert user is not None
    assert Hasher.verify_password("testpassword", user.password_hash)

def test_register_existing_user(client):
    # Register again with same username
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "newpassword", "role": "user"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_login_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_nonexistent_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent", "password": "somepassword"}
    )
    assert response.status_code == 401
