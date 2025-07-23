import orjson
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
JSON_DATA_PATH = BASE_DIR / "data" / "product_catalog.json"
def load_json_data() -> dict:
    json_path = JSON_DATA_PATH
    if not json_path.exists():
        raise FileNotFoundError(f"JSON data file not found: {json_path}")
    
    with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
        return orjson.loads(f.read())
 
