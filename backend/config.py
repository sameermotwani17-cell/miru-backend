from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from a .env file if present.
load_dotenv(BASE_DIR / ".env")
