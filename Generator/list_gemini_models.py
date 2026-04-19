"""Quick script to list available Gemini models"""
from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / '.env')

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

print("Available Gemini models:")
print("=" * 60)
for model in client.models.list():
    print(f"- {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"  Methods: {model.supported_generation_methods}")
