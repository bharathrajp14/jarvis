"""Quick API key format test."""
import sys, os
sys.path.insert(0, '.')
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

key = os.environ.get('GEMINI_API_KEY','')
print('Key prefix:', key[:6] if key else 'NONE')
print('Key length:', len(key))

# Try a simple Gemini call
try:
    from google import genai
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Say "JARVIS WORKS" and nothing else.'
    )
    print('API Response:', resp.text.strip())
    print('STATUS: SUCCESS')
except Exception as e:
    print('API Error:', type(e).__name__, str(e)[:200])
    print('STATUS: FAILED')
