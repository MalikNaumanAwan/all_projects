import os
import httpx
from dotenv import load_dotenv

# Load SERPER_API_KEY from .env
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not SERPER_API_KEY:
    raise ValueError("❌ Missing SERPER_API_KEY in .env file")


async def web_search_serper(query: str, count: int = 5):
    print("🔍 Searching web with Serper.dev...")

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    results = []
    for item in data.get("organic", []):
        if "title" in item and "snippet" in item and "link" in item:
            results.append(
                {
                    "title": item["title"],
                    "snippet": item["snippet"],
                    "url": item["link"],
                }
            )
        if len(results) >= count:
            break

    if results:
        print(f"✅ Found {len(results)} results:")
        for r in results:
            print(f"📄 Title: {r['title']}")
            print(f"📝 Snippet: {r['snippet']}")
            print(f"🔗 URL: {r['url']}")
            print("-" * 50)
    else:
        print("⚠️ No results found.")

    return results


def build_search_augmented_prompt(user_query, search_results):
    context = "\n".join(
        [
            f"{i+1}. {r['title']} — {r['snippet']} ({r['url']})"
            for i, r in enumerate(search_results)
        ]
    )
    return f"""
Use the following search results to answer the user's question factually.
Cite URLs when appropriate.

Search Results:
{context if context else 'No relevant search results found.'}

Question:
{user_query}
"""
