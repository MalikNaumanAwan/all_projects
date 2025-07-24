# tools.py
from langchain.tools import tool 
from app.core.loader import load_json_data
from pydantic import BaseModel, Field, field_validator
import re
from typing import List
from app.core.embeddings import load_or_create_vector_store
from collections import Counter

class KeywordInput(BaseModel):
    keywords: List[str]

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_str_input(cls, v):
        # If input is passed as a string, try to eval or parse it
        if isinstance(v, str):
            try:
                return eval(v) if v.startswith("[") else [v]
            except Exception:
                raise ValueError("Keywords must be a list of strings")
        return v

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
def semantic_product_search(query: str) -> str:
    """Use this tool to search for products that semantically match the query using vector similarity search."""
    catalog = load_json_data()
    
    products = catalog  

    product_texts = [
    f"{item['name']} - {item.get('description', '')}" for item in products
    ]
    vectorstore = load_or_create_vector_store(tuple(product_texts))  # tuple required for lru_cache
    results = vectorstore.similarity_search(query, k=5)
    return "\n".join(doc.page_content for doc in results)


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
        p for p in data if float(p["price"]) <= price_val
    ]
    return str(filtered)

@tool
def list_all_products(dummy_input: str) -> str:
    """Returns all products with their IDs and names."""
    data = load_json_data()
    products = data
    return str([{ "id": p["id"], "name": p["name"] } for p in products])



@tool(args_schema=ProductDetailInput)
def get_product_details(product_id: str) -> str:
    """Returns details for a given product ID."""
    try:
        data = load_json_data()
        for product in data:
            if product.get("id") == product_id:
                return str(product)
        return "Product not found."
    except Exception as e:
        return f"Error retrieving product details: {str(e)}"

@tool
def get_product_id_by_name(name: str) -> str:
    """Returns the product ID for a given product name."""
    data = load_json_data()
    for product in data:
        if product["name"].lower() == name.lower():
            return product["id"]
    return "Product ID not found."


@tool
def list_top_rated_products(n: str = "5") -> str:
    """
    Returns the top-N products with the highest average customer rating.
    """
    try:
        num = int(n.split()[0])
    except (ValueError, IndexError):
        num = 5

    catalog = load_json_data()

    # 🔐 Filter out any non-dict items
    valid_items = [item for item in catalog if isinstance(item, dict)]

    sorted_items = sorted(valid_items, key=lambda x: x.get("rating", 0), reverse=True)
    top_items = sorted_items[:num]

    if not top_items:
        return "No products with ratings found."

    return "\n".join(f"{item.get('name', 'Unnamed')} - {item.get('rating', 'N/A')}⭐" for item in top_items)



@tool
def get_cheapest_product(dummy_input: str = "") -> str:
    """
    Returns the cheapest product overall across all categories.
    """
    try:
        catalog = load_json_data()
        if not isinstance(catalog, list) or not catalog:
            return "Product catalog is empty or not a valid list."

        cheapest = min(catalog, key=lambda p: float(p.get("price", float("inf"))))

        return (
            f"Cheapest Product:\n"
            f"Name: {cheapest.get('name')}\n"
            f"ID: {cheapest.get('id')}\n"
            f"Price: ${cheapest.get('price')}\n"
            f"Category: {cheapest.get('category')}"
        )

    except Exception as e:
        return f"Error determining the cheapest product: {str(e)}"

@tool
def recommend_similar_products(product_id: str) -> str:
    """
    Given a product ID, returns 3 similar products from the same category or tag.
    """
    catalog = load_json_data()
    target = next((p for p in catalog if p.get("id") == product_id), None)
    if not target:
        return "Product not found."

    category = target.get("category")
    tag_set = set(target.get("tags", []))

    similar = [
        p for p in catalog
        if p["id"] != product_id and (
            p.get("category") == category or tag_set.intersection(p.get("tags", []))
        )
    ][:3]

    return "\n".join(f"{p['name']} - {p.get('price', 'N/A')}" for p in similar)


@tool
def get_inventory_summary(input: str) -> str:
    """
    Returns the number of products per category in the catalog.
    """
    catalog = load_json_data()

    # ✅ Keep only dicts that have a 'category' field
    valid_items = [p for p in catalog if isinstance(p, dict) and "category" in p]

    if not valid_items:
        return "No category data found in the catalog."

    counts = Counter(p["category"] for p in valid_items)
    return "\n".join(f"{cat}: {count} items" for cat, count in counts.items())


@tool(args_schema=KeywordInput)
def find_products_matching_keywords(keywords: list[str]) -> list[dict]:
    """Search for products whose name, category, or description includes any of the provided keywords."""
    products = load_json_data()
    keywords = [kw.lower() for kw in keywords]

    results = []
    for product in products:
        name = product.get("name", "").lower()
        category = product.get("category", "").lower()
        desc = product.get("description", "").lower()
        if any(kw in name or kw in category or kw in desc for kw in keywords):
            results.append(product)
    return results


