from http import client
import logging
import os
from groq import Groq
from dotenv import load_dotenv
from app.services.extract_score import extract_score_and_justification  # Adjust path as needed
load_dotenv()  # loads variables from .env

client = Groq(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)


def generate_match_response(jd_text, resume_text, match_chunks):
    prompt = f"""
You are an AI hiring assistant. Based on the following Job Description (JD) and Resume, assess the suitability of the candidate. Extract relevant skills, experience, and provide a suitability score out of 100, along with a 3-sentence justification.

### Job Description:
{jd_text}

### Resume:
{resume_text}

### Matching Chunks:
{match_chunks}

### Respond in this format:
Score: <score>/100
Justification: <3-sentence reason>
"""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        full_text = response.choices[0].message.content.strip()
        score, justification = extract_score_and_justification(full_text)
        return {
        "score": score,
        "reasoning": justification,
        "raw": full_text
        }
    except Exception as e:
        logger.exception("❌ LLM generation failed")
        return {"error": str(e)}