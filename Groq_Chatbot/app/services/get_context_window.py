import os
import requests
from dotenv import load_dotenv


def test_openrouter_model(model_id: str):
    # Load API key from .env
    load_dotenv()
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

    if not MISTRAL_API_KEY:
        raise ValueError("❌ OPENROUTER_API_KEY not found in .env file")

    # Endpoint
    url = "https://api.mistral.ai/v1/chat/completions"

    # Request payload
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": "tell me a joke",
            }
        ],
        "max_tokens": 1000,
    }

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    # Send request
    response = requests.post(url, headers=headers, json=payload)

    # Print full response headers
    print("\n=== Response Headers ===")
    for k, v in response.headers.items():
        print(f"{k}: {v}")

    # Also print body for context
    print("\n=== Response Body ===")
    print(response.text)


def main():
    # Pick a test model
    model_id = "voxtral-small-latest"
    test_openrouter_model(model_id)


if __name__ == "__main__":
    main()
