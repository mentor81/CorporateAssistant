from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from passlib.context import CryptContext
import pdfplumber
import re
import requests
import json
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine, Column, Integer, String, ARRAY, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ==========================================
# 1. DATABASE CONFIGURATION (PostgreSQL)
# ==========================================
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:kavian_81@localhost/ai-db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    scopes = Column(ARRAY(String))

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. SECURITY & JWT CONFIGURATION
# ==========================================
SECRET_KEY = "Kavian1381!"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def safe_parse(output: str):
    try:
        return json.loads(output)
    except:
        # Try to extract JSON block
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception as e:
                print("Second parse failed:", e)

        print("RAW OUTPUT:\n", output)  # debug
        raise ValueError("Invalid JSON from model")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    return payload

# ==========================================
# 3. PYDANTIC MODELS
# ==========================================
class PromptRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 300

class UserCreate(BaseModel):
    username: str
    password: str
    scopes: List[str]

class UserLogin(BaseModel):
    username: str
    password: str

# ==========================================
# 4. FASTAPI APP & ROUTES
# ==========================================
app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/chat"
QWEN_MODEL = "qwen3.6:27b"
GEMMA_MODEL = "gemma4:latest"

# @app.post("/register")
# def register_user(user: UserCreate, db: Session = Depends(get_db)):
#     db_user = db.query(User).filter(User.username == user.username).first()
#     if db_user:
#         raise HTTPException(status_code=400, detail="Username already registered")
#
#     hashed_pw = get_password_hash(user.password)
#     new_user = User(username=user.username, hashed_password=hashed_pw, scopes=user.scopes)
#     db.add(new_user)
#     db.commit()
#     return {"msg": f"User {user.username} created with scopes {user.scopes}"}

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    required_skills = Column(ARRAY(String))
    min_experience_months = Column(Integer)
    salary_range = Column(ARRAY(BigInteger))


# Pydantic models
class Education(BaseModel):
    field: str
    degree: str
    institution: Optional[str]


class Experience(BaseModel):
    role: str
    company: str
    type: str
    duration_months: int


class CandidateData(BaseModel):
    name: str
    last_name: str
    date_of_birth: str
    marital_status: str
    children: int
    gender: str
    skills: List[str]
    education: List[Education]
    experience: List[Experience]
    requested_position: str
    requested_wage_irr: int
    requested_wage_raw: str


class JobApplicationRequest(BaseModel):
    job_title: str
    candidate: CandidateData


def candidate_to_json_string(candidate_data: CandidateData) -> str:
    """
    Convert CandidateData Pydantic model to a formatted JSON string.
    """
    # Convert Pydantic model to dict
    data_dict = candidate_data.dict()

    # Convert to JSON string with Persian-friendly formatting
    json_string = json.dumps(
        data_dict,
        ensure_ascii=False,  # Preserve Persian characters
        indent=2  # Pretty print with 2-space indentation
    )

    return json_string

@app.post("/apply")
def apply_for_job(request: JobApplicationRequest, db: Session = Depends(get_db)):
    # Fetch job description
    job = db.query(JobDescription).filter(JobDescription.title == request.job_title).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job title '{request.job_title}' not found"
        )

    # Calculate total experience
    total_experience_months = sum(exp.duration_months for exp in request.candidate.experience)

    # Check requirements
    required_skills = set(job.required_skills)
    required_experience = int(job.min_experience_months)
    candidate_skills = set(request.candidate.skills)
    matching_skills = required_skills.intersection(candidate_skills)

    min_salary, max_salary = job.salary_range
    payload = {
        "model": GEMMA_MODEL,
        "think": False,
        "stream": False,
        "keep_alive": 0,
        "messages": [
            {
                "role": "system",
                "content": """You are an HR evaluation model.

You will receive a structured JSON CV of a candidate.
Analyze it objectively and return ONLY valid JSON.

Do NOT explain outside JSON.
Do NOT add extra text.

STRICT RULES:
- Be deterministic and consistent.
- Do NOT guess missing data.
- If a field is null, penalize the score.
- Base your evaluation ONLY on provided data.
- Do NOT assume skills or experience that are not explicitly listed.

EVALUATION CRITERIA (score each from 0 to 100):

1. skills_score:
- Relevance and usefulness of skills for the requested_position
- Penalize generic or unclear skills

2. experience_score:
- Based on duration_months and role relevance
- Less than 12 months → low score
- 12–36 months → medium
- 36+ months → high

3. education_score:
- Degree level (Bachelor < Master)
- Relevance of field to requested_position

4. salary_score:
- If requested_wage_irr is very high → penalize
- If reasonable → higher score
- If not in range, mention the expected and the applicants value


5. overall_score:
- Weighted combination:
  skills_score * 0.3 +
  experience_score * 0.3 +
  education_score * 0.2 +
  salary_score * 0.2

OUTPUT FORMAT:
{
  "scores": {
    "skills_score": integer,
    "experience_score": integer,
    "education_score": integer,
    "salary_score": integer,
    "overall_score": number
  },
  "strengths": [string],
  "weaknesses": [string],
  "summary": string
}"""
            },
            {
                "role": "user",
                "content": f"""
            'candidate': {candidate_to_json_string(request.candidate)},
            'job': {{
                'title': '{job.title}',
                'required_skills': {list(required_skills)},
                'min_experience_months': {required_experience},
                'min_max_salary': {job.salary_range}
            }}
            """
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 2048
        }
    }
    print(job.salary_range)
    response = requests.post(OLLAMA_URL, json=payload)
    # print("STATUS CODE:", response.status_code)
    # print("RAW RESULT:", response.text)
    result = response.json()

    output = result.get("message", {}).get("content", "")
    print(output)
    data = safe_parse(output)
    print(output)
    return data

@app.post("/token")
def login_for_access_token(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_credentials.username).first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": user.username, "scopes": user.scopes, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": encoded_jwt, "token_type": "bearer"}


def fix_backward_persian(text):
    if not text:
        return ""

    def protect_numbers(line):
        # protect Persian/Arabic numbers with separators
        return re.sub(r'[\d۰-۹٠-٩٬,]+', lambda m: f"__NUM_{m.group(0)}__", line)

    def restore_numbers(line):
        return re.sub(r'__NUM_(.*?)__', lambda m: m.group(1), line)

    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        protected = protect_numbers(line)

        reversed_line = protected[::-1]

        def fix_english(match):
            return match.group(0)[::-1]

        fixed_line = re.sub(r'[a-zA-Z0-9\+\/\.#]+', fix_english, reversed_line)

        restored = restore_numbers(fixed_line)

        fixed_lines.append(restored)

    return '\n'.join(fixed_lines)


def extract_pdf_text(file) -> str:
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            raw = page.extract_text()
            text += fix_backward_persian(raw) + "\n"
    return text


@app.post("/analyze-cv")
async def analyze_cv(
    file: UploadFile = File(...),
    current_user: dict = Security(get_current_user, scopes=["hr"])
):
    # Step 1: read PDF
    contents = await file.read()

    # Save temporarily (pdfplumber needs file-like)
    with open("temp.pdf", "wb") as f:
        f.write(contents)

    # Step 2: extract + fix text
    text = extract_pdf_text("temp.pdf")

    # Step 3: call Ollama (Qwen)
    payload = {
        "model": QWEN_MODEL,
        "think": False,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": """You are a CV parser.

Return ONLY valid JSON. No explanation. No extra text.

STRICT RULES:
- Follow the schema EXACTLY.
- Output must be valid JSON.
- Do NOT include trailing commas.
- Do NOT include comments.
- Do NOT wrap output in markdown.
- Do NOT truncate the output.
- Ensure all brackets and quotes are properly closed.
- Do NOT use line breaks inside JSON string values.
- Escape quotes properly inside strings.
- Use null if a field is missing.

DATA RULES:
- children must be integer.
- requested_wage_irr must be integer (remove commas and text).
- Keep date_of_birth EXACTLY as written in the CV. Do NOT convert formats.

EXTRACTION RULES:
- Skills = practical/job-related abilities (e.g., UI Design, React, Photoshop).
- DO NOT include academic majors or school subjects in skills.
- Education = degrees, majors, academic background only.
- Extract experience duration if available.
- Convert duration to total months (e.g., 1 year = 12).
- If duration is not clearly specified, use null.
- Do NOT guess missing values.
- requested_wage_irr must be extracted EXACTLY from the text.
- Convert Persian digits (۰۱۲۳۴۵۶۷۸۹) to English digits.
- Remove separators like ٬ or ,.
- Do NOT multiply, scale, or reinterpret the number.
- Do NOT convert between تومان and ریال.

SCHEMA:
{
  "name": string,
  "last_name": string,
  "date_of_birth": string,
  "marital_status": string,
  "children": integer,
  "gender": string,
  "skills": [string],
  "education": [
    {
      "field": string,
      "degree": string,
      "institution": string
    }
  ],
  "experience": [
    {
      "role": string,
      "company": string,
      "type": string,
      "duration_months": integer
    }
  ],
  "requested_position": string,
  "requested_wage_irr": integer
  "requested_wage_raw": string
}"""
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 800
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)
    result = response.json()

    output = result.get("message", {}).get("content", "")
    data = safe_parse(output)
    print(output)
    return data

@app.post("/generate")
def generate(
    req: PromptRequest,
    current_user: dict = Security(get_current_user, scopes=["r&d"])
):
    print(current_user.get('scopes'))
    payload = {
        "model": QWEN_MODEL,
        "think": False,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": req.system_prompt
            },
            {
                "role": "user",
                "content": req.user_prompt
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": req.max_tokens
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)
    result = response.json()

    output = result.get("message", {}).get("content", "")

    return {
        "response": output
    }

@app.get("/translate")
def translate(text: str,):
    payload = {
        "model": QWEN_MODEL,
        "think": False,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": 'You are an expert English to Persian translator, You will output what you have translated based on the text user gives to you.'
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 1024
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)
    result = response.json()

    output = result.get("message", {}).get("content", "")

    return {'output':output}
