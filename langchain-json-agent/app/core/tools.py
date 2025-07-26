from langchain_core.tools import tool
from typing import Dict
from urllib.parse import parse_qs
from app.core.embeddings import load_or_create_vector_store
from app.utils.catalog_cache import get_catalog
from bs4 import BeautifulSoup
import aiohttp
import json
import re


def parse_input(input: str) -> dict:
    input = input.strip()
    if not input:
        return {}

    def clean_string(value) -> str:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value  # Return as-is if not a string

    try:
        parsed = json.loads(input)
        if isinstance(parsed, dict):
            return {k: clean_string(v) for k, v in parsed.items()}
        elif isinstance(parsed, list):
            return {"keywords": [clean_string(i) for i in parsed]}
        else:
            return {"input": clean_string(parsed)}
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    try:
        if "=" in input:
            items = input.replace(";", "&")
            parsed = parse_qs(items)
            return {k: clean_string(v[0]) for k, v in parsed.items()}
    except Exception:
        pass

    return {"input": clean_string(input)}


PRICE_REGEX = re.compile(r"\$[\d,]+(?:\.\d{2})?")


@tool
async def semantic_product_search(query: str) -> str:
    """Returns top 5 semantically similar products based on the input query."""
    catalog = await get_catalog()
    product_texts = [
        f"{item['name']} - {item.get('description', '')}" for item in catalog
    ]
    vectorstore = load_or_create_vector_store(tuple(product_texts))
    results = vectorstore.similarity_search(query, k=5)
    return "\n".join(doc.page_content for doc in results)


@tool
async def recommend_similar_products(product_id: str) -> str:
    """Recommends up to 3 similar products based on category or tag overlap."""
    catalog = await get_catalog()
    target = next((p for p in catalog if p.get("id") == product_id), None)
    if not target:
        return "Product not found."
    category = target.get("category")
    tag_set = set(target.get("tags", []))
    similar = [
        p
        for p in catalog
        if p["id"] != product_id
        and (p.get("category") == category or tag_set.intersection(p.get("tags", [])))
    ][:3]
    return "\n".join(f"{p['name']} - {p.get('price', 'N/A')}" for p in similar)


@tool
async def list_all_products(input: str) -> Dict:
    """Lists all products in the catalog."""
    catalog = await get_catalog()
    return {"results": catalog}


@tool
async def search_similar_names(input: str) -> Dict:
    """Searches catalog for product names containing the given input."""
    params = parse_input(input)
    name = params.get("name") or params.get("input")
    if not name:
        return {"error": "Missing name"}
    catalog = await get_catalog()
    matches = [p for p in catalog if name.lower() in p.get("name", "").lower()]
    return {"results": matches or "No close matches found"}


@tool
async def get_product_details(input: str) -> Dict:
    """Returns full product details given a product_id."""
    params = parse_input(input)
    product_id = params.get("product_id") or params.get("input")
    if not product_id:
        return {"error": "Missing product_id"}
    catalog = await get_catalog()
    return next(
        (p for p in catalog if p.get("id") == product_id), {"error": "Not found"}
    )


@tool
async def get_product_by_name(input: str) -> Dict:
    """Returns product details by exact name match."""
    params = parse_input(input)
    name = params.get("name") or params.get("input")
    if not name:
        return {"error": "Missing name"}
    catalog = await get_catalog()
    return next((p for p in catalog if p.get("name") == name), {"error": "Not found"})


@tool
async def get_products_by_brand(input: str) -> Dict:
    """Returns all products matching the given brand."""
    params = parse_input(input)
    brand = params.get("brand") or params.get("input")
    if not brand:
        return {"error": "Missing brand"}
    catalog = await get_catalog()
    matches = [p for p in catalog if p.get("brand", "").lower() == brand.lower()]
    return {"results": matches or "No products found for this brand"}


@tool
async def get_products_by_category(input: str) -> Dict:
    """Returns all products belonging to the specified category."""
    params = parse_input(input)
    category = params.get("category") or params.get("input")
    if not category:
        return {"error": "Missing category"}
    catalog = await get_catalog()
    matches = [p for p in catalog if p.get("category", "").lower() == category.lower()]
    return {"results": matches or "No products found for this category"}


@tool
async def get_products_by_min_rating(input: str) -> Dict:
    """Returns products with a rating equal to or greater than the specified value."""
    params = parse_input(input)
    try:
        min_rating = float(params.get("rating") or params.get("input"))
    except (TypeError, ValueError):
        return {"error": "Invalid or missing rating"}
    catalog = await get_catalog()
    matches = [p for p in catalog if p.get("rating", 0) >= min_rating]
    return {"results": matches or "No products match this rating"}


@tool
async def get_products_by_max_price(input: str) -> Dict:
    """Returns products with a price less than or equal to the specified amount."""
    params = parse_input(input)
    try:
        max_price = float(params.get("price") or params.get("input"))
    except (TypeError, ValueError):
        return {"error": "Invalid or missing price"}
    catalog = await get_catalog()
    matches = [p for p in catalog if p.get("price", float("inf")) <= max_price]
    return {"results": matches or "No products under this price"}


@tool
async def get_all_brands(input: str) -> Dict:
    """Returns a sorted list of all available brands in the catalog."""
    catalog = await get_catalog()
    brands = sorted({p.get("brand") for p in catalog if p.get("brand")})
    return {"brands": brands}


@tool
async def compare_products_by_name_or_fallback(input: str) -> Dict:
    """Compares two products by name and returns their details or fallback messages."""
    params = parse_input(input)
    p1 = params.get("product_1")
    p2 = params.get("product_2")
    if not p1 or not p2:
        return {"error": "Missing one or both product names"}
    catalog = await get_catalog()

    def find_product(name):
        return next((p for p in catalog if p.get("name") == name), None)

    return {
        "product_1": find_product(p1) or f"{p1} not found in catalog",
        "product_2": find_product(p2) or f"{p2} not found in catalog",
    }


@tool
async def fetch_external_product_info(query: str) -> str:
    """
    Fetch real-time product descriptions, features, and prices from the web.
    Prioritizes informative, paragraph-style results over just titles/prices.
    Returns a max of 5 high-confidence results with cleaned formatting.
    """
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, data={"q": query}, headers=headers, timeout=15
            ) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                results = []

                for result in soup.select(".result__body"):
                    title_tag = result.select_one("a.result__a")
                    snippet_tag = result.select_one(".result__snippet")

                    if not title_tag or not snippet_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    snippet = snippet_tag.get_text(strip=True)

                    # Clean snippet: remove trailing URL-based junk or promo suffixes
                    snippet = re.sub(r"\s*[-–—]\s*\w+\.\w{2,}.*$", "", snippet)

                    price_matches = PRICE_REGEX.findall(f"{title} {snippet}")
                    price_text = (
                        f"💰 Price(s): {', '.join(price_matches)}"
                        if price_matches
                        else "💬 No exact price found."
                    )

                    # Full contextual paragraph output
                    product_info = (
                        f"🛒 **{title}**\n" f"📄 {snippet.strip()}\n" f"{price_text}"
                    )

                    results.append(product_info)

                if results:
                    return f"SUMMARY:\n{'\n\n'.join(results[:5])}"

                else:
                    return "❌ No detailed product information was found for the query."

    except Exception as e:
        return f"❌ Web lookup failed: {str(e)}"


@tool
def explain_missing_product(input: str) -> str:
    """Explains why a product might be missing from the catalog."""
    return (
        "The product may not exist in the current catalog, "
        "might be named differently, or is not yet released (e.g., iPhone 16). "
        "Try using similar name search or semantic search."
    )
