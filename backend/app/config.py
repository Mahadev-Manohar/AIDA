import os
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Default Groq model
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
