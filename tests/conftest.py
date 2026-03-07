import pytest
import os
import libsql_client
from fastapi.testclient import TestClient
from app.main import app
from app.db.client import db_manager, get_db, fetch_one
from app.core.config import settings

# Use a file-based test database
TEST_DB_URL = "file:test_madf.db"

# Override settings (if possible) or just mock the db_manager
# Since db_manager is instantiated at module level in app.db.client,
# we can modify its url attribute?
# Yes, let's try that.

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # 1. Configure DB Manager to use test DB
    original_url = db_manager.url
    original_token = db_manager.auth_token
    
    db_manager.url = TEST_DB_URL
    db_manager.auth_token = None # No token for local file
    db_manager.is_remote = False
    
    # 2. Remove existing test DB if any
    if os.path.exists("test_madf.db"):
        os.remove("test_madf.db")
        
    # 3. Initialize Schema
    # We need to make sure schema.sql is found. 
    # db_manager.init_db() uses __file__ relative path, so it should work if called from there.
    # But we are importing it.
    db_manager.init_db()
    
    yield
    
    # 4. Cleanup
    # Close any connections? libsql_client sync client closes on exit context.
    # We might need to manually remove the file.
    if os.path.exists("test_madf.db"):
        try:
            os.remove("test_madf.db")
        except PermissionError:
            pass # Windows file locking might prevent immediate deletion

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db():
    # Return a fresh connection for each test function
    conn = db_manager.get_connection()
    yield conn
    conn.close()
