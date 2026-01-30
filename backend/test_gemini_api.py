from google import genai
from core.config import settings

print("Testing Google Gemini API...")
print(f"Model: {settings.llm_model}")
print(f"API Key: {settings.google_api_key[:20]}...")

try:
    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.llm_model,
        contents='Say hello in exactly 3 words'
    )
    print(f"\n✅ SUCCESS!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"\n❌ FAILED!")
    print(f"Error: {e}")
