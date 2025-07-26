import asyncio
from langchain.agents import initialize_agent, AgentType
from app.core.llm import get_llm
from app.core.prompts import JSON_AGENT_PROMPT_V2, PromptTemplate
from app.core.tools import (
    get_product_details,
    get_product_by_name,
    get_products_by_brand,
    get_products_by_category,
    get_products_by_min_rating,
    get_products_by_max_price,
    list_all_products,  # Optional, useful during dev/debug
    get_all_brands,
    search_similar_names,
    explain_missing_product,
    fetch_external_product_info,
    compare_products_by_name_or_fallback,
)


async def get_agent():
    """Initializes and returns the LangChain agent with registered tools."""
    llm = get_llm()  # Ensure this returns an **async-compatible LLM**
    tools = [
        get_product_details,
        get_product_by_name,
        get_products_by_brand,
        get_products_by_category,
        get_products_by_min_rating,
        get_products_by_max_price,
        list_all_products,  # Optional, useful during dev/debug]
        get_all_brands,
        search_similar_names,
        explain_missing_product,
        fetch_external_product_info,
        compare_products_by_name_or_fallback,
    ]
    return initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=30,
        agent_kwargs={"prompt": JSON_AGENT_PROMPT_V2},
    )


async def get_classifier():
    """Initializes and returns the LangChain agent with registered tools."""
    llm = get_llm()  # Ensure this returns an **async-compatible LLM**
    return initialize_agent(
        llm=llm,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=30,
        agent_kwargs={"prompt": PromptTemplate},
    )


async def run_agent(question: str, db_session=None, timeout: int = 120) -> str:
    """
    Executes the LangChain agent asynchronously with a hard timeout.
    """
    agent_executor = await get_agent()
    try:
        return await asyncio.wait_for(agent_executor.ainvoke(question), timeout=timeout)
    except asyncio.TimeoutError:
        raise RuntimeError("❌ Agent execution timed out")
