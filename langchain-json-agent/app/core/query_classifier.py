from fastapi import APIRouter, HTTPException
from app.core.llm import get_llm  # Async-compatible LLM client
from app.core.prompts import CLASSIFIER_PROMPT
import asyncio
from app.schemas.query import QueryResponse

router = APIRouter()


async def classify_query(input: QueryResponse):
    llm = get_llm()
    prompt = CLASSIFIER_PROMPT.format(query=input.strip())
    response = await llm.ainvoke(prompt)
    print(response.content)
    answer = response.content.strip().lower()
    if answer not in ["relevant", "irrelevant"]:
        raise HTTPException(status_code=400, detail="LLM gave invalid classification")

    return {"classification": answer}


# 🔁 Run if script
if __name__ == "__main__":
    query = QueryResponse(query="what is the weather today?")
    result = asyncio.run(classify_query(query))
    print(result)
