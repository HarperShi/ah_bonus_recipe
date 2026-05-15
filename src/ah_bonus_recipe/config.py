from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DISCOVERY_DIR = DATA_DIR / "discovery"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

AH_WEB_BONUS_URL = "https://www.ah.nl/bonus"
AH_API_BASE_URL = "https://api.ah.nl"
AH_APPLICATION = "AHWEBSHOP"

AH_CLIENT_ID = "appie-ios"
AH_CLIENT_VERSION = "9.28"
AH_USER_AGENT = "Appie/9.28 (iPhone17,3; iPhone; CPU OS 26_1 like Mac OS X)"

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
)
