# tools.py

from langchain.tools import tool
from app.core.loader import load_json_data
from pydantic import BaseModel, Field, field_validator
import re

class ProductDetailInput(BaseModel):
    product_id: str = Field(..., description="ID of the product")

class PriceFilterInput(BaseModel):
    max_price: float = Field(..., description="Maximum price to filter")

    @field_validator("max_price", mode="before")
    @classmethod
    def extract_float(cls, v):
        try:
            # Extract the first float-looking number from the string
            match = re.search(r"\d+\.?\d*", str(v))
            if match:
                return float(match.group(0))
            raise ValueError()
        except Exception:
            raise ValueError(f"Could not parse a valid float from input: {v}")



@tool
def filter_products_by_price(max_price: str) -> str:
    """Returns products cheaper than or equal to max_price."""
    try:
        # Extract numeric float from string using regex
        price_val = float(re.search(r"\d+(\.\d+)?", max_price).group())
    except Exception:
        return "Invalid price format. Please specify a numeric value like '2000.0'."

    data = load_json_data()
    filtered = [
        p for p in data.get("products", []) if float(p["price"]) <= price_val
    ]
    return str(filtered)

@tool
def list_all_products(dummy_input: str) -> str:
    """Returns all products with their IDs and names."""
    data = load_json_data()
    products = data.get("products", [])
    return str([{ "id": p["id"], "name": p["name"] } for p in products])




@tool(args_schema=ProductDetailInput)
def get_product_details(product_id: str) -> str:
    """Returns details for a given product ID."""
    data = load_json_data()
    for product in data.get("products", []):
        if product["id"] == product_id:
            return str(product)
    return "Product not found."
