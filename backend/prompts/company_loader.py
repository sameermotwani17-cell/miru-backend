from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "sources" / "miru_company_profiles.txt"


def load_company_profiles() -> str:
    """Load company profile research used by the interview AI."""
    
    if not SOURCE_FILE.exists():
        raise FileNotFoundError("Company profiles file missing")

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        return f.read()