from pydantic import BaseModel
from typing import Optional
from app.core.config import settings

ALLOWED_THINK = {
    "off": False,
    "on": True,
}

ALLOWED_MODELS = {
    "gemma": settings.gemma_model,
    "qwen": settings.qwen_model,
}

class PromptRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 300
    think: str = "off"
    model: str = "qwen"