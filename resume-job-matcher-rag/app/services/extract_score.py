import re

def extract_score_and_justification(response_text: str):
    """
    Parses LLM text output into a structured (score, justification) tuple.
    Expected format:
    Score: <number>/100
    Justification: <text>
    """
    score_match = re.search(r"Score:\s*(\d+)", response_text)
    justification_match = re.search(r"Justification:\s*(.*)", response_text, re.DOTALL)

    score = int(score_match.group(1)) if score_match else None
    justification = justification_match.group(1).strip() if justification_match else "No justification found."

    return score, justification
