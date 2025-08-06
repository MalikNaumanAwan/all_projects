# app/services/summarize_articles.py
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import re
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from groq import Groq, RateLimitError
from app.article_chunk import ArticleChunkBase
from db.crud import save_articles
from schemas.article import ArticleCreate
from services.compile_final_article import format_articles_batch
from app.article_chunk import crawl_articles

# ────────────────────────────────────────────────────────────────
# ENV & CLIENT SETUP
# ────────────────────────────────────────────────────────────────
load_dotenv()
client = Groq(api_key=os.getenv("OPENAI_API_KEY"))
GROQ_MODEL = "llama3-8b-8192"

# ────────────────────────────────────────────────────────────────
# CONSTANTS
# ────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("/temp/")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_CONCURRENT_LLM_CALLS = 2
MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 5

# ────────────────────────────────────────────────────────────────
# PROMPT TEMPLATES
# ────────────────────────────────────────────────────────────────

CHUNK_SUMMARY_PROMPT = """
You are an AI journalist assistant. Your task is to summarize a content chunk from a news article.

### Title
{title}

### Content Chunk
{chunk}

### Instructions
- Summarize accurately with no hallucination.
- Maintain tone, facts, and key data.
- Be concise but professional.

Begin:
"""

FINAL_SUMMARY_PROMPT = """
You are an AI journalist tasked with writing a final article summary based on multiple summarized parts.

### Title
{title}

### Source
{source_url}

### Summarized Chunks
{intermediate_summaries}

### Instructions
- Consolidate these summaries into one cohesive article.
- Eliminate redundancy and retain critical information.
- Use a professional, news-style tone.

Begin:
"""

# ────────────────────────────────────────────────────────────────
# UTILITIES
# ────────────────────────────────────────────────────────────────

semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")[:64]


async def call_llm_with_retry(prompt: str, max_tokens: int = 512) -> str:
    """Throttled + retry-enabled LLM call."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                return content.strip() if content else "[!] Empty LLM response."

        except RateLimitError:
            delay = RETRY_BACKOFF_BASE * attempt
            print(f"[429] Rate limited. Retry {attempt}/{MAX_RETRIES} after {delay}s.")
            await asyncio.sleep(delay)

        except Exception as e:
            print(f"[!] LLM error: {e}")
            return f"[!] LLM Error: {e}"

    return "[!] Exceeded retry attempts."


# ────────────────────────────────────────────────────────────────
# SUMMARIZATION LOGIC
# ────────────────────────────────────────────────────────────────


async def summarize_chunk(chunk: str, title: str) -> str:
    prompt = CHUNK_SUMMARY_PROMPT.format(title=title, chunk=chunk)
    return await call_llm_with_retry(prompt)


async def summarize_article(article: ArticleChunkBase) -> str:
    print(
        f"[→] Processing: {article.title} ({len(article.content)} chunks)", flush=True
    )

    chunk_summaries = []
    for i, chunk in enumerate(article.content):
        print(f"   ↳ Chunk {i+1}/{len(article.content)}...")
        summary = await summarize_chunk(chunk, article.title)
        chunk_summaries.append(summary)

    combined = "\n\n".join(chunk_summaries)
    final_prompt = FINAL_SUMMARY_PROMPT.format(
        title=article.title,
        source_url=article.source_url,
        intermediate_summaries=combined,
    )
    final_summary = await call_llm_with_retry(final_prompt, max_tokens=1024)
    return final_summary


# ────────────────────────────────────────────────────────────────
# MAIN DRIVER
# ────────────────────────────────────────────────────────────────


async def summarize_and_save_all(
    articles: List[ArticleChunkBase],
) -> List[ArticleCreate]:
    summarized_articles = []

    for article in articles:
        try:
            summary = await summarize_article(article)

            summarized_article = ArticleCreate(
                title=article.title,
                source_url=article.source_url,
                image_url=article.image_url,
                content=summary,
            )

            summarized_articles.append(summarized_article)
            print(f"[✓] Summarized: {article.title}")

        except Exception as e:
            print(f"[!] Failed: {article.title} → {e}", flush=True)

    return summarized_articles


async def main():
    articles = await crawl_articles("bbc.com")
    if articles:
        articles_list = await summarize_and_save_all(articles)
        final_articles = await format_articles_batch(articles_list)
        await save_articles(final_articles)


if __name__ == "__main__":
    asyncio.run(main())
