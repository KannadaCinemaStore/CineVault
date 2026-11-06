import os
from dotenv import load_dotenv

load_dotenv()

def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default

API_ID = _int("API_ID", 0)
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cinevault")
ADMINS = {int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip().isdigit()}
FORCE_SUB_CHANNELS = [x.strip() for x in os.getenv("FORCE_SUB_CHANNELS", "").split(",") if x.strip()]
AUTO_DELETE_SECONDS = max(0, _int("AUTO_DELETE_SECONDS", 0))
RESULTS_PER_PAGE = max(1, min(10, _int("RESULTS_PER_PAGE", 8)))

if not API_ID or not API_HASH or not BOT_TOKEN or not MONGO_URI:
    raise RuntimeError("Missing required config. Copy .env.example to .env and fill API_ID, API_HASH, BOT_TOKEN and MONGO_URI.")
