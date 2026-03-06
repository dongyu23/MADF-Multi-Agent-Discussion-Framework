import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.core.hashing import Hasher
from app.models import User

# Use in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_register_user(db_session):
    # Ensure clean state
    db_session.query(User).delete()
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpassword", "role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

    # Verify user in DB
    user = db_session.query(User).filter(User.username == "testuser").first()
    assert user is not None
    assert Hasher.verify_password("testpassword", user.password_hash)

def test_register_existing_user():
    # Register again with same username
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "newpassword", "role": "user"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_login_user():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_nonexistent_user():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent", "password": "somepassword"}
    )
    assert response.status_code == 401
