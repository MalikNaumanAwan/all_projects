from fastapi import APIRouter, Depends, HTTPException
from app.schemas.query import QueryRequest, QueryResponse
from app.api.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.agent import run_agent
from app.utils.catalog_cache import get_catalog, get_vector_store
from app.core.query_classifier import classify_query

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def handle_query(
    query_data: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        print(">>>>> Incoming question:", query_data.question)
        classification = await classify_query(query_data.question)

        if classification["classification"] == "irrelevant":
            response_text = "❌ Your query is not related to the product catalog."
            return QueryResponse(answer=response_text)

        response_text = await run_agent(query_data.question, db)
        print(">> Response:", response_text)

        # Ensure response is stringified cleanly
        if isinstance(response_text, dict):
            response_text = response_text.get("output", str(response_text))

        return QueryResponse(answer=response_text)

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/health")
async def health_check():
    try:
        catalog = await get_catalog()
        vector_store = await get_vector_store()
        return {
            "catalog_count": len(catalog),
            "vector_store": type(vector_store).__name__,
            "status": "OK",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
