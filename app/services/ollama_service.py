import requests

from app.core.config import settings


def call_ollama(model: str, messages: list, num_predict: int, temperature: float = 0.1, think: bool = False, keep_alive: int = 0):
    payload = {
        "model": model,
        "think": think,
        "stream": False,
        "keep_alive": keep_alive,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict
        }
    }

    response = requests.post(settings.ollama_url, json=payload)
    response.raise_for_status()
    result = response.json()

    return result.get("message", {}).get("content", "")
