from pydantic import BaseModel
from typing import Optional


class PromptRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 300
