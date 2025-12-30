from zhipuai import ZhipuAI
from config import API_KEY, MODEL_NAME
import json

client = ZhipuAI(api_key=API_KEY)

def get_chat_completion(messages, stream=False, json_mode=False):
    """
    Wrapper for ZhipuAI chat completion.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=stream,
            temperature=0.8,
            max_tokens=4096,
            top_p=0.7
        )
        return response
    except Exception as e:
        print(f"Error calling API: {e}")
        return None

def parse_json_from_response(content):
    """
    Attempts to parse JSON from a string, handling code blocks if present.
    """
    try:
        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        return json.loads(content.strip())
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {content}")
        return None
