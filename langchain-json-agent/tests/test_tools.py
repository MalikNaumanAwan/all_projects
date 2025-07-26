import ast
from typing import Union
import json


def check_tool_result_validity(input: Union[str, dict]) -> str:
    """Checks if the tool output is a valid product or product list."""
    print(input)
    try:
        if isinstance(input, str):
            input = input.strip()
            if not input:
                return "invalid"
            try:
                input = json.loads(input)  # works if valid JSON (double quotes)
            except json.JSONDecodeError:
                try:
                    input = ast.literal_eval(
                        input
                    )  # fallback for single-quoted Python-style dict
                except Exception:
                    return "invalid"
        # Case 1: Direct dict for a single product
        if isinstance(input, dict):
            if "error" in input:
                print("invalid")
                return "invalid"
            # Valid single product
            required_keys = {"id", "name", "price", "description"}
            if required_keys.issubset(input.keys()):
                print("valid")
                return "valid"
            # Wrapped in 'results'
            if "results" in input and isinstance(input["results"], list):
                return check_tool_result_validity(input["results"])
            print("invalid")
            return "invalid"

        # Case 2: List of product dicts
        if isinstance(input, list):
            if not input:
                print("invalid")
                return "invalid"
            for item in input:
                if not isinstance(item, dict):
                    print("invalid")
                    return "invalid"
                if not {"id", "name", "price", "description"}.issubset(item.keys()):
                    print("invalid")
                    return "invalid"
            print("valid")
            return "valid"
        print("invalid")
        return "invalid"

    except Exception:
        print("invalid")
        return "invalid"


check_tool_result_validity(
    {
        "id": "p007",
        "name": "iPhone 15 Pro Max",
        "brand": "Apple",
        "price": 1199.0,
        "category": "phone",
        "rating": 4.9,
        "description": "Latest flagship iPhone with A17 Pro chip and titanium design.",
    }
)
