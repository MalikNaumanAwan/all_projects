#query.py
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.query import QueryRequest, QueryResponse
from app.api.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.agent import run_agent

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def handle_query(
    query_data: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        print(">> Incoming question:", query_data.question)
        response_text = await run_agent(query_data.question, db)
        print(">> Response:", response_text)
        return QueryResponse(answer=response_text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

 
