from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    headline: Mapped[str] = mapped_column(String(240), default="")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    skills: Mapped[str] = mapped_column(Text, default="[]")
    target_titles: Mapped[str] = mapped_column(Text, default="[]")
    locations: Mapped[str] = mapped_column(Text, default='["Remote"]')
    countries: Mapped[str] = mapped_column(Text, default='["Global"]')
    work_modes: Mapped[str] = mapped_column(Text, default='["Remote","Hybrid","On-site"]')
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="USD")
    resume_text: Mapped[str] = mapped_column(Text, default="")
    resume_filename: Mapped[str] = mapped_column(String(255), default="")
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="profile")

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_source_external"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), default="Unknown")
    location: Mapped[str] = mapped_column(String(255), default="Not specified")
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
    employment_type: Mapped[str] = mapped_column(String(80), default="Not specified")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="saved")
    match_score: Mapped[float] = mapped_column(Float, default=0)
    tailored_resume: Mapped[str] = mapped_column(Text, default="")
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    approval_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[User] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship()
