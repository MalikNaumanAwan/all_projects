import os
from typing import List
from dotenv import load_dotenv
from groq import AsyncGroq
import asyncio
from schemas.article import FinalArticle, ArticleCreate

# Load environment variables
load_dotenv()
GROQ_MODEL = "llama3-8b-8192"

client = AsyncGroq(api_key=os.getenv("OPENAI_API_KEY"))

FINAL_PROMPT_TEMPLATE = """
You are a professional AI journalist. Your task is to rewrite the following article content into a well-structured, publish-ready article.

**Instructions**:
- Retain a journalistic tone.
- Begin with a compelling headline (H1).
- Structure the article using H2 subheadings that reflect the logical flow of ideas.
- Break the article into clear, readable paragraphs.
- If appropriate, highlight key points using bullet lists or bold emphasis.
- Maintain all factual details from the original.
- Output the article in clean Markdown format (H1, H2, paragraphs, etc.).

### Raw Article Content:
\"\"\"
{raw_text}
\"\"\"
"""


async def format_article(article: ArticleCreate) -> FinalArticle:
    if not article.content or not isinstance(article.content, str):
        raise ValueError(f"Invalid article content for: {article.title}")

    raw_text = article.content.strip()
    prompt = FINAL_PROMPT_TEMPLATE.format(raw_text=raw_text)

    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional AI journalist."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        formatted_content = response.choices[0].message.content
        if not formatted_content:
            raise RuntimeError(
                f"No content returned from LLM for article: {article.title}"
            )
        url = str(article.image_url)
        return FinalArticle(
            title=article.title,
            source_url=article.source_url,
            image_url=url,
            content=formatted_content.strip(),
        )
    except Exception as e:
        # Optional: log and skip or raise
        print(f"[ERROR] Failed to format article '{article.title}': {e}")
        raise e


async def format_articles_batch(articles: List[ArticleCreate]) -> List[FinalArticle]:
    tasks = [format_article(article) for article in articles]
    return await asyncio.gather(*tasks, return_exceptions=False)
