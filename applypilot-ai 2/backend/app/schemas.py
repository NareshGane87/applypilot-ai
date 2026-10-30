from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""
class TokenOut(BaseModel): access_token: str; token_type: str = "bearer"
class ProfileIn(BaseModel):
    headline: str = ""
    years_experience: int = Field(default=0, ge=0, le=60)
    skills: list[str] = []
    target_titles: list[str] = []
    locations: list[str] = ["Remote"]
    countries: list[str] = ["Global"]
    work_modes: list[str] = ["Remote", "Hybrid", "On-site"]
    salary_min: Optional[int] = None
    salary_currency: str = "USD"
class ApplicationStatusIn(BaseModel): status: str
class GenerateIn(BaseModel): job_id: int
class JobOut(BaseModel):
    id: int; title: str; company: str; location: str; url: str; source: str
    description: str; remote: bool; employment_type: str; posted_at: str
    class Config: from_attributes = True
class ApplicationOut(BaseModel):
    id: int; status: str; match_score: float; approval_granted: bool
    tailored_resume: str; cover_letter: str; notes: str
    job: JobOut
    class Config: from_attributes = True
