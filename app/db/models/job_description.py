from sqlalchemy import Column, Integer, String, ARRAY, BigInteger

from app.db.base import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    required_skills = Column(ARRAY(String))
    min_experience_months = Column(Integer)
    salary_range = Column(ARRAY(BigInteger))
