from fastapi import APIRouter, Security

from app.core.config import settings
from app.core.security import get_current_user
from app.schemas.prompt import PromptRequest
from app.services.ollama_service import call_ollama
from app.core.prompts import EN_PER_TRANSLATE_SYSTEM_MODEL
router = APIRouter(prefix="/general", tags=["general"])


@router.post("/generate")
def generate(
    req: PromptRequest,
    current_user: dict = Security(get_current_user, scopes=["r&d"])
):
    output = call_ollama(
        model=settings.qwen_model,
        messages=[
            {"role": "system", "content": req.system_prompt},
            {"role": "user", "content": req.user_prompt},
        ],
        num_predict=req.max_tokens,
        temperature=req.temperature or 0.1
    )

    return {"response": output}

@router.get("/translate")
def translate(text: str):
    output = call_ollama(
        model=settings.qwen_model,
        messages=[
            {
                "role": "system",
                "content": EN_PER_TRANSLATE_SYSTEM_MODEL
            },
            {
                "role": "user",
                "content": text
            }
        ],
        num_predict=1024,
        temperature=0.1
    )

    return {"output": output}
