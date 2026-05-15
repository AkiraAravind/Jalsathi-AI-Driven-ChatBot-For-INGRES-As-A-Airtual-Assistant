import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

print(f"--- Gemini Key Verification ---")
print(f"Key found: {api_key[:10]}...")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

try:
    response = model.generate_content("Testing INGRES connection. Respond with 'READY'.")
    print(f"Status: SUCCESS")
    print(f"Response: {response.text.strip()}")
except Exception as e:
    print(f"Status: FAILED")
    print(f"Error: {e}")
