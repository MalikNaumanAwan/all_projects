import aiofiles
import orjson
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
JSON_DATA_PATH = BASE_DIR / "data" / "product_catalog.json"


async def load_json_data_async() -> list:
    if not JSON_DATA_PATH.exists():
        raise FileNotFoundError(f"JSON data file not found: {JSON_DATA_PATH}")

    async with aiofiles.open(JSON_DATA_PATH, "rb") as f:
        file_bytes = await f.read()
        data = orjson.loads(file_bytes)

    if isinstance(data, dict) and "products" in data:
        return data["products"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError(
            "Unexpected JSON structure. Expected list or {'products': [...]}."
        )
