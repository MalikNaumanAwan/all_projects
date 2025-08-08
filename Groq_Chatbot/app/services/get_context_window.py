import os
import requests
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def fetch_all_model_limits():
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    models = resp.json().get("data", [])

    records = []
    for m in models:
        records.append(
            {
                "model_id": m.get("id"),
                "owned_by": m.get("owned_by"),
                "context_window": m.get("context_window"),
                "max_completion_tokens": m.get("max_completion_tokens"),
                "active": m.get("active"),
                "created": m.get("created"),
            }
        )
    return records


def save_to_excel(data, filename="groq_model_limits.xlsx"):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"✅ Model limits saved to {filename}")


if __name__ == "__main__":
    if not GROQ_API_KEY:
        raise EnvironmentError("Please set the GROQ_API_KEY environment variable.")

    model_data = fetch_all_model_limits()
    save_to_excel(model_data)
