
import orjson
from pathlib import Path
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent.parent
JSON_DATA_PATH = BASE_DIR / "data" / "product_catalog.json"

@lru_cache()
def load_json_data() -> list:
    json_path = JSON_DATA_PATH
    if not json_path.exists():
        raise FileNotFoundError(f"JSON data file not found: {json_path}")

    with open(json_path, "rb") as f:  # orjson expects bytes
        data = orjson.loads(f.read())
    
    # Defensive fix
    if isinstance(data, dict) and "products" in data:
        return data["products"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Unexpected JSON structure. Expected list or {'products': [...]}.")

