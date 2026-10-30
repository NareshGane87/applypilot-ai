import json, io
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from pypdf import PdfReader
from docx import Document
from .config import settings
from .db import Base, engine, get_db
from .models import User, Profile, Job, Application
from .schemas import AuthIn, TokenOut, ProfileIn, ApplicationStatusIn, GenerateIn
from .security import hash_password, verify_password, create_token, current_user
from .ai import extract_profile, tailor_application
from .jobs import sync_public_boards, score_job

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="0.1.0", description="AI-assisted global job discovery and application workspace")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"status":"ok", "service":"ApplyPilot AI"}

@app.post("/api/auth/register", response_model=TokenOut)
def register(data: AuthIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=data.email).first(): raise HTTPException(409, "Email already registered")
    user = User(email=data.email, full_name=data.full_name, hashed_password=hash_password(data.password))
    db.add(user); db.flush(); db.add(Profile(user_id=user.id)); db.commit()
    return {"access_token":create_token(user.id)}

@app.post("/api/auth/login", response_model=TokenOut)
def login(data: AuthIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password, user.hashed_password): raise HTTPException(401, "Incorrect email or password")
    return {"access_token":create_token(user.id)}

@app.get("/api/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter_by(user_id=user.id).first()
    return {"id":user.id,"email":user.email,"full_name":user.full_name,"profile":profile_dict(p)}

def profile_dict(p):
    if not p: return None
    return {"headline":p.headline,"years_experience":p.years_experience,"skills":json.loads(p.skills or "[]"),"target_titles":json.loads(p.target_titles or "[]"),"locations":json.loads(p.locations or "[]"),"countries":json.loads(p.countries or "[]"),"work_modes":json.loads(p.work_modes or "[]"),"salary_min":p.salary_min,"salary_currency":p.salary_currency,"resume_filename":p.resume_filename,"onboarding_complete":p.onboarding_complete}

@app.put("/api/profile")
def save_profile(data: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter_by(user_id=user.id).first() or Profile(user_id=user.id)
    for key in ["headline","years_experience","salary_min","salary_currency"]: setattr(p,key,getattr(data,key))
    for key in ["skills","target_titles","locations","countries","work_modes"]: setattr(p,key,json.dumps(getattr(data,key)))
    p.onboarding_complete = bool(p.resume_text and data.skills)
    db.add(p); db.commit(); db.refresh(p)
    return profile_dict(p)

@app.post("/api/profile/resume")
async def upload_resume(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = file.filename or "resume"
    if not name.lower().endswith((".pdf", ".docx", ".txt")): raise HTTPException(400,"Upload a PDF, DOCX or TXT resume")
    raw = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413,"Resume exceeds upload limit")
    try:
        if name.lower().endswith(".pdf"): text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
        elif name.lower().endswith(".docx"): text = "\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
        else: text = raw.decode("utf-8", errors="replace")
    except Exception: raise HTTPException(400,"Could not read resume. Try a text-based PDF or DOCX.")
    if len(text.strip()) < 80: raise HTTPException(400,"Not enough readable text found in resume")
    p = db.query(Profile).filter_by(user_id=user.id).first() or Profile(user_id=user.id)
    p.resume_text, p.resume_filename = text[:30000], name
    try:
        extracted = extract_profile(p.resume_text)
        p.headline = extracted.get("headline", p.headline)
        p.years_experience = int(extracted.get("years_experience", p.years_experience) or 0)
        p.skills = json.dumps(extracted.get("skills", []))
        p.target_titles = json.dumps(extracted.get("target_titles", []))
    except Exception: pass
    db.add(p); db.commit(); db.refresh(p)
    return {"filename":name,"characters_extracted":len(text),"profile":profile_dict(p),"ai_enabled":bool(settings.openai_api_key)}

@app.post("/api/jobs/sync")
async def sync_jobs(q: str = Query(default="", max_length=100), user: User = Depends(current_user), db: Session = Depends(get_db)):
    count = await sync_public_boards(db, q)
    return {"added":count,"message":"Synced available public employer-board listings. Configure more employer board slugs for broader coverage."}

@app.get("/api/jobs")
def list_jobs(q: str = "", limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter_by(user_id=user.id).first()
    rows = db.query(Job).order_by(desc(Job.created_at)).limit(min(limit,100)).all()
    if q: rows = [j for j in rows if q.lower() in (j.title+j.company+j.description).lower()]
    return [{"id":j.id,"title":j.title,"company":j.company,"location":j.location,"url":j.url,"source":j.source,"description":j.description[:500],"remote":j.remote,"employment_type":j.employment_type,"posted_at":j.posted_at,"match_score":score_job(p,j) if p else 0} for j in rows]

@app.post("/api/applications")
def save_application(data: GenerateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(Job,data.job_id)
    if not job: raise HTTPException(404,"Job not found")
    existing = db.query(Application).filter_by(user_id=user.id,job_id=job.id).first()
    if existing: return {"id":existing.id,"status":existing.status,"message":"Already saved"}
    p = db.query(Profile).filter_by(user_id=user.id).first()
    if not p or not p.resume_text: raise HTTPException(400,"Upload your resume before saving jobs")
    a = Application(user_id=user.id,job_id=job.id,match_score=score_job(p,job),status="saved")
    db.add(a); db.commit(); db.refresh(a)
    return {"id":a.id,"status":a.status,"match_score":a.match_score}

@app.post("/api/applications/{application_id}/draft")
def draft_application(application_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = db.query(Application).options(joinedload(Application.job)).filter_by(id=application_id,user_id=user.id).first()
    if not a: raise HTTPException(404,"Application not found")
    p = db.query(Profile).filter_by(user_id=user.id).first()
    try: result = tailor_application(p.resume_text,{"title":a.job.title,"company":a.job.company,"description":a.job.description})
    except RuntimeError as e: raise HTTPException(503,str(e))
    a.tailored_resume=result.get("tailored_resume",""); a.cover_letter=result.get("cover_letter",""); a.status="draft_ready"
    db.commit(); return {"status":a.status,"tailored_resume":a.tailored_resume,"cover_letter":a.cover_letter}

@app.get("/api/applications")
def list_applications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Application).options(joinedload(Application.job)).filter_by(user_id=user.id).order_by(desc(Application.created_at)).all()
    return [{"id":a.id,"status":a.status,"match_score":a.match_score,"approval_granted":a.approval_granted,"tailored_resume":a.tailored_resume,"cover_letter":a.cover_letter,"notes":a.notes,"job":{"id":a.job.id,"title":a.job.title,"company":a.job.company,"location":a.job.location,"url":a.job.url,"source":a.job.source,"description":a.job.description[:500],"remote":a.job.remote,"employment_type":a.job.employment_type,"posted_at":a.job.posted_at}} for a in rows]

@app.patch("/api/applications/{application_id}/status")
def update_status(application_id: int, data: ApplicationStatusIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    allowed={"saved","draft_ready","approved","applied","interview","rejected","withdrawn"}
    if data.status not in allowed: raise HTTPException(400,"Unsupported status")
    a=db.query(Application).filter_by(id=application_id,user_id=user.id).first()
    if not a: raise HTTPException(404,"Application not found")
    if data.status == "applied":
        if not a.approval_granted: raise HTTPException(403,"Explicit approval is required before marking an application submitted")
        a.applied_at=datetime.utcnow()
    if data.status == "approved": a.approval_granted=True
    a.status=data.status; db.commit(); return {"id":a.id,"status":a.status,"approval_granted":a.approval_granted}

@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    apps=db.query(Application).filter_by(user_id=user.id).all()
    return {"jobs_saved":len(apps),"drafts_ready":sum(a.status=="draft_ready" for a in apps),"approved":sum(a.approval_granted for a in apps),"applied":sum(a.status in ("applied","interview","rejected") for a in apps),"interviews":sum(a.status=="interview" for a in apps)}
