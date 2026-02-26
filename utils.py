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
    Also handles common LLM JSON errors like unescaped quotes.
    """
    try:
        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        content = content.strip()
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Standard JSON parse failed: {e}. Attempting recovery...")
        
        # Try dirtyjson
        try:
            import dirtyjson
            return dirtyjson.loads(content)
        except ImportError:
            pass
        except Exception:
            pass
            
        # Regex-based fallback for unescaped quotes in values
        # This specifically targets the pattern found in the user's error:
        # "key": "some text "quoted text" some text"
        import re
        try:
            # 1. Temporarily replace valid structure quotes
            # A valid quote is one that is preceded by : (for start of value) or followed by , or } (for end of value)
            # This is simplistic but covers many cases.
            
            # Actually, a safer bet is to use the fact that keys are standard.
            # We can try to re-construct the JSON if we know the schema, but that's hard.
            
            # Let's try a regex that looks for quotes inside string values.
            # Pattern: "key": "value" -> value might contain "
            # We can iterate over the string and track state? Too complex for here.
            
            # Specific fix for the user's case:
            # The error is likely caused by quotes inside the bio/system_prompt.
            # We can try to replace " with \" ONLY if it's not a delimiter.
            # A quote is a delimiter if:
            # 1. It's followed by \s*:
            # 2. It's preceded by \s*:\s*
            # 3. It's followed by \s*,
            # 4. It's followed by \s*}
            # 5. It's preceded by {\s*
            # 6. It's preceded by [\s*
            # 7. It's followed by \s*]
            
            # Let's try to protect delimiters.
            # This is a bit hacky but might work for LLM output.
            
            def escape_inner_quotes(s):
                 # 1. Protect keys: "key":
                 s = re.sub(r'"\s*:', '___KEY_DELIM___', s)
                 
                 # 2. Protect value start: : "
                 s = re.sub(r':\s*"', '___VAL_START___', s)
                 
                 # 3. Protect value end: ", or "} or "]
                 # Be careful not to match inner quotes followed by comma or brace inside a string
                 # This is the hardest part. "Foundation", matches ",
                 # We need to ensure it's really a value end.
                 # Heuristic: Value end usually followed by newline or space then key start or } or ]
                 # But we stripped whitespace? No, we just stripped outer whitespace.
                 
                 # Let's try a different approach:
                 # Match the full key-value pair pattern?
                 # "key": "value"
                 # We can use a regex to find strings that look like keys
                 
                 # Or: simpler heuristic.
                 # If we see " followed by , or } or ] AND preceded by a non-escaped ", it's likely a delimiter.
                 
                 # Let's try to match valid JSON string tokens and skip them? No, that's a parser.
                 
                 # Let's go back to the user's specific case:
                 # "bio": "He founded the "Foundation" successfully."
                 # The inner quotes are surrounded by text. The outer quotes are at start/end.
                 
                 # We can try to replace " with \" if it is preceded by a word char or space?
                 # Or followed by a word char or space?
                 
                 # Let's try to identify structural quotes vs content quotes.
                 # Structural quotes:
                 # - "key":
                 # - : "value"
                 # - "value",
                 # - "value"}
                 # - "value"]
                 
                 # The issue with "value", is that "Foundation", also matches.
                 # But "Foundation", is inside the string. 
                 # In valid JSON, a value end quote is followed by , or } or ] and then usually a newline or another key.
                 
                 # Let's try to protect " that are followed by \s*[,}\]]
                 # AND are NOT preceded by \ (already handled by negative lookbehind in regex?)
                 
                 # Let's rely on the fact that inner quotes are usually NOT followed immediately by structural chars
                 # unless it's the end of the sentence.
                 # But "Foundation" successfully." -> The first " is followed by F. The second by space.
                 # The end quote is followed by space/newline then } or ,
                 
                 # Let's assume standard formatting (pretty printed) often helps.
                 
                 # Protect: " at start of line (after whitespace) -> Key start
                 s = re.sub(r'^\s*"', '___START_QUOTE___', s, flags=re.MULTILINE)
                 
                 # Protect: ": " -> Key end / Value start
                 s = re.sub(r'":\s*"', '___KEY_VAL_SEP___', s)
                 
                 # Protect: ", -> Value end / Next item
                 s = re.sub(r'",\s*$', '___VAL_COMMA___', s, flags=re.MULTILINE)
                 
                 # Protect: "} -> Value end / Obj end
                 s = re.sub(r'"\s*}\s*$', '___VAL_BRACE___', s, flags=re.MULTILINE)
                 s = re.sub(r'"\s*}\s*,', '___VAL_BRACE_COMMA___', s, flags=re.MULTILINE) # } followed by ,
                 
                 # This relies on multiline structure which the LLM output seems to have.
                 
                 # Replace remaining " with \"
                 s = s.replace('"', '\\"')
                 
                 # Restore
                 s = s.replace('___START_QUOTE___', '"')
                 s = s.replace('___KEY_VAL_SEP___', '": "')
                 s = s.replace('___VAL_COMMA___', '",')
                 s = s.replace('___VAL_BRACE___', '"}')
                 s = s.replace('___VAL_BRACE_COMMA___', '"},')
                 
                 return s

            fixed_content = escape_inner_quotes(content)
            return json.loads(fixed_content)
        except Exception as e:
            print(f"Regex recovery failed: {e}")

        print(f"Failed to parse JSON content: {content}")
        return None
