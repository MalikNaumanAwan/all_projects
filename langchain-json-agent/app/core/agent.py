from langchain.agents import initialize_agent, AgentType
from app.core.llm import get_llm
from app.core.prompts import JSON_AGENT_PROMPT
from app.core.tools import (
    get_product_details,
    filter_products_by_price,
    list_all_products,  # ✅ New tool imported
)

def get_agent():
    """Initializes and returns the LangChain agent with registered tools."""
    llm = get_llm()
    tools = [
        get_product_details,
        filter_products_by_price,
        list_all_products,  # ✅ Register new tool here
    ]

    return initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={"prompt": JSON_AGENT_PROMPT},
    )

async def run_agent(question: str, db_session=None) -> str:
    """
    Executes the agent on the given question.

    Args:
        question (str): Natural language query from user.
        db_session: Optional database session (reserved for future use).

    Returns:
        str: Agent-generated answer.
    """
    agent_executor = get_agent()
    return agent_executor.run(question)
