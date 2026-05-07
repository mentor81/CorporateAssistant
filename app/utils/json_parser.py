import json
import re


def safe_parse(output: str):
    try:
        return json.loads(output)
    except Exception:
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception as e:
                print("Second parse failed:", e)

        print("RAW OUTPUT:\n", output)
        raise ValueError("Invalid JSON from model")
