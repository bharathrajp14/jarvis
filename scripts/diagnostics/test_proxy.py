"""Live proxy test — calls the local proxy directly."""
import sys
sys.path.insert(0, '.')
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

import os
print("=== BR JARVIS Proxy Live Test ===")
print("Proxy URL:", os.environ.get('OPENAI_BASE_URL'))
print("Proxy key:", os.environ.get('OPENAI_API_KEY','')[:20] + '...')
print()

try:
    from openai import OpenAI
    client = OpenAI(
        base_url=os.environ.get('OPENAI_BASE_URL', 'http://localhost:8045/v1'),
        api_key=os.environ.get('OPENAI_API_KEY', 'none')
    )
    print("Testing gemini-3.5-flash via proxy...")
    resp = client.chat.completions.create(
        model="gemini-3.5-flash",
        messages=[{"role": "user", "content": "Say exactly: JARVIS PROXY WORKS"}],
        max_tokens=50
    )
    print("Response:", resp.choices[0].message.content.strip())
    print("STATUS: SUCCESS")
except Exception as e:
    print("Error:", type(e).__name__, str(e)[:300])
    print("STATUS: FAILED")
    print()
    print("Make sure your proxy is running at localhost:8045")
