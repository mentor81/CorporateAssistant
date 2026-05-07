from pydantic import BaseModel
from typing import Optional, List


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
