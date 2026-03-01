from pathlib import Path

APP_NAME = "GlideGuru"
TAGLINE = "Beautiful flight routing — shortest, cheapest, smartest."
DATA_PATH = Path("data") / "airline_routes_with_price.json"

DEFAULT_MAX_HOPS = 4
DEFAULT_TOP_K = 3