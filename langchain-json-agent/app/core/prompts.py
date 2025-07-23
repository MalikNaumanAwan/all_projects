from langchain.prompts import PromptTemplate

JSON_AGENT_PROMPT = PromptTemplate.from_template(
    """
You are an intelligent assistant that answers user queries based on a structured product catalog in JSON format.

You can use tools like `filter_products`, `get_product_details`, or `list_categories`.

Always explain the answer in a clear and friendly tone.

Question: {input}

{agent_scratchpad}
"""
)
 
