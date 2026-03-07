import pytest
import os
from fastapi.testclient import TestClient
import libsql_client

from app.db.client import get_db, db_manager
from app.main import app as fastapi_app

# Use a temporary file for SQLite testing
TEST_DB_PATH = "test_madf.db"
TEST_DB_URL = f"file:{TEST_DB_PATH}"

@pytest.fixture(scope="function")
def db():
    # Setup: Create a fresh database for each test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Update db_manager to use test DB
    original_url = db_manager.url
    db_manager.url = TEST_DB_URL
    db_manager.is_remote = False
    
    # Initialize schema
    db_manager.init_db()
    
    client = db_manager.get_connection()
    try:
        yield client
    finally:
        client.close()
        # Teardown: Remove test database
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except:
                pass
        db_manager.url = original_url

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        client = db_manager.get_connection()
        try:
            yield client
        finally:
            client.close()
    
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
