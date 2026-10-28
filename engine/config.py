"""Central configuration for the Daily Brief engine."""
import os

REPO = os.environ.get("GITHUB_REPOSITORY", "vagharia/daily-board")
OWNER, REPO_NAME = REPO.split("/", 1)
DASHBOARD_URL = os.environ.get("DB_DASHBOARD_URL", f"https://{OWNER}.github.io/{REPO_NAME}/")

# Where the data branch is checked out / written.
DATA_DIR = os.environ.get("DB_DATA_DIR", "_data")
# Offline mode reads every URL from tests/fixtures (used for local tests).
OFFLINE = os.environ.get("DB_OFFLINE") == "1"
FIXTURES = os.environ.get("DB_FIXTURES", "tests/fixtures")
# Publish (commit + push the data branch). Disabled for local runs.
PUBLISH = os.environ.get("DB_PUBLISH", "0") == "1"
# Fixed "now" for reproducible offline tests (epoch seconds).
FIXED_NOW = int(os.environ.get("DB_NOW", "0") or 0)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

H24 = 24 * 3600
WEEK = 7 * 24 * 3600
KEEP = 7 * 24 * 3600              # news history: one week, nothing older

# Pre-crisis baseline for Hormuz transits = the year before this date.
CRISIS_START = "2026-02-28"
TG_CHANNEL = "dollar_tehran3bze"

TIER_RED = 70
TIER_ORANGE = 45

# Bump to discard stored stories / seen items after a logic change (translations are kept).
STATE_VERSION = 2

# Run budgets
MAX_FA_TRANSLATE = 320         # Persian items translated per run (the rest wait for the next run)
MAX_PAGE_FETCHES = 45          # article pages fetched for images / embedded posts
MAX_TWEET_LOOKUPS = 30
