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
from app.db.models.job_description import JobDescription
from app.schemas.candidate import JobApplicationRequest
from app.services.candidate_service import candidate_to_json_string
from app.core.prompts import CV_EVALUATION_SYSTEM_PROMPT, build_hr_evaluation_user_prompt, CV_PARSER_SYSTEM_PROMPT


router = APIRouter(prefix="/hr", tags=["hr"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/apply")
def apply_for_job(request: JobApplicationRequest, db: Session = Depends(get_db)):
    job = db.query(JobDescription).filter(JobDescription.title == request.job_title).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job title '{request.job_title}' not found"
        )

    required_skills = set(job.required_skills)
    required_experience = int(job.min_experience_months)

    output = call_ollama(
        model=settings.gemma_model,
        messages=[
            {
                "role": "system",
                "content": CV_EVALUATION_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": build_hr_evaluation_user_prompt(candidate_json=candidate_to_json_string(request.candidate), job=job)
            }
        ],
        num_predict=2048,
        temperature=0.1
    )

    return safe_parse(output)


@router.post("/analyze-cv")
async def analyze_cv(
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
            model=settings.qwen_model,
            messages=[
                {
                    "role": "system",
                    "content": CV_PARSER_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            num_predict=800,
            temperature=0.1
        )

        data = safe_parse(output)
        return data
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)