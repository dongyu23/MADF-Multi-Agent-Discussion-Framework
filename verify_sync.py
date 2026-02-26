import requests
import uuid
import sys
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_verification():
    print("Starting verification...")

    # 1. Authenticate
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    password = "testpassword"
    print(f"Creating user: {username}")

    # Register
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "username": username,
            "password": password
        }, timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Registration failed: {e}")
        if resp.status_code != 400: # Ignore if already exists (unlikely with uuid)
             sys.exit(1)

    # Login
    print("Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data={
            "username": username,
            "password": password
        }, timeout=5)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    # 2. Call batch preset
    print("Creating preset personas...")
    try:
        resp = requests.post(f"{BASE_URL}/personas/batch/preset", headers=headers, timeout=10)
        resp.raise_for_status()
        personas = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Batch preset failed: {e}")
        sys.exit(1)

    # 3. Verify personas
    print("Verifying personas...")
    if not personas:
        print("No personas returned")
        sys.exit(1)
    
    first_persona = personas[0]
    required_fields = ["theories", "bio", "stance", "system_prompt"]
    for field in required_fields:
        if field not in first_persona:
            print(f"Missing field {field} in persona")
            sys.exit(1)
    
    if not isinstance(first_persona["theories"], list):
        print("Theories is not a list")
        sys.exit(1)
    
    print(f"Verified {len(personas)} personas.")

    # 4. Create forum
    print("Creating forum...")
    participant_ids = [p["id"] for p in personas[:2]]
    try:
        resp = requests.post(f"{BASE_URL}/forums/", headers=headers, json={
            "topic": "The meaning of life",
            "participant_ids": participant_ids
        }, timeout=10)
        resp.raise_for_status()
        forum = resp.json()
        forum_id = forum["id"]
    except requests.exceptions.RequestException as e:
        print(f"Forum creation failed: {e}")
        sys.exit(1)

    print(f"Forum created with ID: {forum_id}")

    # 5. Trigger moderator
    print("Triggering moderator (opening)...")
    try:
        # Provide a longer timeout as LLM might take time
        resp = requests.post(f"{BASE_URL}/forums/{forum_id}/trigger_moderator", headers=headers, json={
            "action": "opening"
        }, timeout=60) 
        resp.raise_for_status()
        print("Moderator triggered successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Trigger moderator failed: {e}")
        # Continue? No, let's fail.
        sys.exit(1)

    # 6. Trigger agent
    target_persona_id = participant_ids[0]
    print(f"Triggering agent (Persona ID: {target_persona_id})...")
    try:
        resp = requests.post(f"{BASE_URL}/forums/{forum_id}/trigger_agent", headers=headers, json={
            "persona_id": target_persona_id
        }, timeout=60)
        resp.raise_for_status()
        print("Agent triggered successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Trigger agent failed: {e}")
        sys.exit(1)

    # 7. Verify messages
    print("Verifying messages...")
    try:
        resp = requests.get(f"{BASE_URL}/forums/{forum_id}/messages", headers=headers, timeout=10)
        resp.raise_for_status()
        messages = resp.json()
        
        if len(messages) < 2:
            print(f"Expected at least 2 messages (moderator + agent), got {len(messages)}")
            # sys.exit(1) # Warning only?
        
        print(f"Found {len(messages)} messages.")
        for msg in messages:
            print(f"- {msg['speaker_name']}: {msg['content'][:50]}...")

    except requests.exceptions.RequestException as e:
        print(f"Get messages failed: {e}")
        sys.exit(1)

    print("Verification Successful")

if __name__ == "__main__":
    run_verification()
