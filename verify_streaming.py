import requests
import json
import sys

def test_sse():
    url = "http://localhost:8000/api/v1/god/generate_real"
    # Assuming we need a token. Let's try without first if it's local, or get a token.
    # But I can just mock the request payload.
    payload = {
        "prompt": "生成一位老师",
        "n": 1
    }
    
    # We need a valid token. Since I don't have one, I'll temporarily disable auth in the endpoint for testing
    # OR I'll just use a mock script that calls the agent directly.
    pass

if __name__ == "__main__":
    # Test the agent directly to verify it yields thought_chunk
    from app.agent.real_god import RealGodAgent
    from app.agent.god import God
    
    agent = RealGodAgent()
    prompt = "生成一位华东师范大学教授"
    
    print("Starting agent test...")
    found_thought_chunk = False
    for event in agent.run(prompt, n=1):
        event_type = event.get("type")
        content = str(event.get("content"))
        
        if "调研" in content:
            print(f"ERROR: Found banned word '调研' in event {event_type}")
            sys.exit(1)
            
        if event_type == "thought_chunk":
            found_thought_chunk = True
            print(f"SUCCESS: Received thought chunk: {content[:20]}...")
            
        if event_type == "result":
            print("SUCCESS: Received result")
            break
            
    if not found_thought_chunk:
        print("ERROR: No thought chunks received")
        sys.exit(1)
    
    print("Test passed!")
