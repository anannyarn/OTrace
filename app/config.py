import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./otrace.db")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
DB_PATH = BASE_DIR / "otrace.db"
MODEL_PATH = BASE_DIR / "models" / "model.joblib"
