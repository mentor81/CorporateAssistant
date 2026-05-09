import os
import tempfile

from fastapi import APIRouter, UploadFile, File, Security, Depends, HTTPException, status
from app.core.config import settings
from app.core.security import get_current_user
from app.services.pdf_service import extract_pdf_text
from app.services.ollama_service import call_ollama
from app.utils.json_parser import safe_parse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.prompts import DATASHEET_PARSER_SYSTEM_PROMPT, SUMMARY_HTML_SYSTEM_PROMPT
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/rnd", tags=["R&D"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/analyze-datasheet")
async def analyze_datasheet(
    file: UploadFile = File(...),
    current_user: dict = Security(get_current_user, scopes=["hr"])
):
    contents = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name

    try:
        text = extract_pdf_text(temp_path)

        output = call_ollama(
            model=settings.gemma_model,
            think=True,
            messages=[
                {
                    "role": "system",
                    "content": DATASHEET_PARSER_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            num_predict=2048,
            temperature=0.1
        )
        print(output)
        # data = safe_parse(output)
        return {'data': output}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/summary-page", response_class=HTMLResponse)
async def summary_page(
    text: str,
    current_user: dict = Security(get_current_user, scopes=["hr"])
):
    output = call_ollama(
        model=settings.gemma_model,
        think=True,
        messages=[
            {
                "role": "system",
                "content": SUMMARY_HTML_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ],
        num_predict=8192,
        temperature=0.1
    )

    return HTMLResponse(content=output)