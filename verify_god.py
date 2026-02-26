import requests
import uuid
import sys
import json

BASE_URL = "http://localhost:8000/api/v1"

def run_god_verification():
    print("Starting God Agent verification...")

    # 1. Authenticate
    username = f"goduser_{uuid.uuid4().hex[:8]}"
    password = "testpassword"
    print(f"Creating user: {username}")

    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "username": username,
            "password": password
        }, timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Registration failed: {e}")
        sys.exit(1)

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

    # 2. Call God Generate
    prompt = "一个沉迷于量子物理但生活邋遢的疯狂科学家"
    print(f"Sending prompt: {prompt}")
    
    try:
        # Long timeout for LLM generation
        resp = requests.post(f"{BASE_URL}/god/generate", headers=headers, json={
            "prompt": prompt,
            "n": 1
        }, timeout=120)
        
        if resp.status_code != 200:
            print(f"God generation failed: {resp.status_code} - {resp.text}")
            sys.exit(1)
            
        personas = resp.json()
        print(f"Generated {len(personas)} personas.")
        
        if not personas:
            print("No personas returned.")
            sys.exit(1)
            
        p = personas[0]
        print(f"Name: {p['name']}")
        print(f"Title: {p['title']}")
        print(f"Bio: {p['bio'][:50]}...")
        print(f"Theories: {p['theories']}")
        
        if not p['bio'] or len(p['bio']) < 10:
             print("Bio is too short or empty")
             sys.exit(1)
             
        if not isinstance(p['theories'], list) or len(p['theories']) == 0:
             print("Theories is not a valid list")
             sys.exit(1)

        print("God Agent Verification Successful")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_god_verification()
