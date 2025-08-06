import logging
import os
import uuid
from typing import List, Tuple
from urllib.parse import urljoin, urlparse, urlsplit
from textwrap import wrap
import httpx
from playwright.async_api import async_playwright, Page
from schemas.article import ArticleChunkBase

# Configure root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

STATIC_IMAGE_DIR = os.path.join("static", "images")
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)


# Allowed content prefixes
ALLOWED_PATH_PREFIXES = [
    "/news",
    "/world",
    "/politics",
    "/business",
    "/economy",
    "/markets",
    "/technology",
    "/tech",
    "/science",
    "/health",
    "/sports",
    "/entertainment",
    "/culture",
    "/opinion",
    "/features",
    "/lifestyle",
    "/travel",
    "/environment",
    "/education",
    "/investigations",
    "/articles",
    "/stories",
    "/story",
    "/202",  # for sites like cnn.com/2023/...
    "/latest",  # frequently-used recent content route
    "/videos",  # optional: if you want video pages too
]


def get_path_depth(path: str) -> int:
    return len([seg for seg in path.split("/") if seg])


def is_allowed_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def chunk_text(text: str, max_tokens: int = 1024) -> List[str]:
    """
    Splits `text` into chunks of approximately `max_tokens`*4 characters.
    """
    max_chars = max_tokens * 4
    chunks = wrap(
        text, width=max_chars, break_long_words=False, replace_whitespace=False
    )
    return [c.strip() for c in chunks if c.strip()]


async def download_image(url: str) -> str:
    """
    Downloads the image at `url` to ./static/images and returns the local path.
    If download fails, returns empty string.
    """
    if not url:
        return ""
    path = urlsplit(url).path
    ext = os.path.splitext(path)[1] or ".jpg"
    ext = ext if len(ext) <= 5 else ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    local_path = os.path.join(STATIC_IMAGE_DIR, filename)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)
        return local_path
    except Exception as e:
        logger.warning("Image download failed for %s: %s", url, e)
        return ""


async def crawl_articles(
    domain: str, max_pages: int = 50, max_depth: int = 4
) -> List[ArticleChunkBase]:
    """
    Crawls pages under `domain` matching allowed prefixes using Playwright,
    with depth control for deeper traversal. Logs steps, extracts content,
    downloads images, chunks text, and returns article chunks.
    """
    start_url = f"https://{domain}"
    parsed_domain = urlparse(start_url).netloc

    visited: set[str] = set()
    queue: List[Tuple[str, int]] = [(start_url, 0)]
    results: List[ArticleChunkBase] = []

    logger.info(
        "Starting crawl for domain: %s with max_pages=%d, max_depth=%d",
        domain,
        max_pages,
        max_depth,
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            if depth > max_depth:
                continue

            visited.add(url)
            logger.info(
                "Visiting URL (%d/%d at depth %d): %s",
                len(visited),
                max_pages,
                depth,
                url,
            )

            page: Page = await context.new_page()
            try:
                await page.goto(url, timeout=60000)
            except Exception as e:
                logger.warning("Failed to load URL %s: %s", url, e)
                await page.close()
                continue

            # enqueue child links matching allowed prefixes
            anchors = await page.query_selector_all("a[href]")
            for a in anchors:
                href = await a.get_attribute("href")
                if not href:
                    continue
                full = urljoin(url, href)
                p = urlparse(full)
                if (
                    parsed_domain in p.netloc
                    and full not in visited
                    and is_allowed_path(p.path)
                ):
                    queue.append((full, depth + 1))
                    logger.debug("Queued URL (depth %d): %s", depth + 1, full)

            # process article if path matches and contains digits
            path = urlparse(url).path
            if is_allowed_path(path) and any(ch.isdigit() for ch in path):
                logger.info("Processing article page: %s", url)

                title = await page.title()

                # extract body
                article_el = await page.query_selector("article")
                if article_el:
                    body = await article_el.inner_text()
                else:
                    ps = await page.query_selector_all("p")
                    body = "\n".join([await p.inner_text() for p in ps])

                word_count = len(body.split())
                if word_count < 80:
                    logger.info(
                        "Skipping short content (%d words): %s", word_count, url
                    )
                    await page.close()
                    continue

                # extract and download image
                img_el = await page.query_selector(
                    "article img"
                ) or await page.query_selector("img")
                img_url = await img_el.get_attribute("src") if img_el else ""
                local_img_path = (
                    await download_image(urljoin(url, img_url)) if img_url else ""
                )

                # chunk text
                chunks = chunk_text(body)
                logger.info("Chunked into %d parts: %s", len(chunks), url)

                for idx, chunk in enumerate(chunks, start=1):
                    results.append(
                        ArticleChunkBase(
                            title=title.strip(),
                            source_url=url,
                            image_url=local_img_path,
                            chunk_index=str(idx),
                            content=[chunk],
                        )
                    )

            await page.close()

        await browser.close()

    path_depth = get_path_depth(urlparse(url).path)
    logger.info(
        "Visiting URL (%d/%d at crawl-depth %d, path-depth %d): %s",
        len(visited),
        max_pages,
        depth,
        path_depth,
        url,
    )

    return results


# Example usage
"""
if __name__ == "__main__":
    import asyncio
    articles = asyncio.run(crawl_articles("bbc.com", max_pages=50, max_depth=3))
    print(f"Collected {len(articles)} chunks.")
    for art in articles[:3]:
        print(
            f"Title: {art.title}\nURL: {art.source_url}\nImage Path: {art.image_url}\nChunk: {art.content[0][:200]}...\n"
        )
"""
