import json
from openai import OpenAI
from .config import settings

SYSTEM = "You are a careful career assistant. Never invent a candidate's skills, employers, degrees, dates, achievements or work authorization. Clearly mark unknowns. Return valid JSON when requested."
def client():
    if not settings.openai_api_key: return None
    return OpenAI(api_key=settings.openai_api_key)

def extract_profile(resume_text: str) -> dict:
    c = client()
    if not c: return {"headline": "", "years_experience": 0, "skills": [], "target_titles": []}
    res = c.chat.completions.create(model=settings.openai_model, temperature=0.1,
        response_format={"type":"json_object"}, messages=[{"role":"system","content":SYSTEM},
        {"role":"user","content":"Extract a factual profile from this resume. Return JSON with headline, years_experience (integer), skills (array), target_titles (array). Do not infer unsupported facts. Resume:\n"+resume_text[:18000]}])
    return json.loads(res.choices[0].message.content or "{}")

def tailor_application(resume_text: str, job: dict) -> dict:
    c = client()
    if not c: raise RuntimeError("Configure OPENAI_API_KEY to enable AI drafting.")
    res = c.chat.completions.create(model=settings.openai_model, temperature=0.2,
        response_format={"type":"json_object"}, messages=[{"role":"system","content":SYSTEM},
        {"role":"user","content":"Create an ATS-friendly tailored resume summary and a concise cover letter for this job. Do not add facts not present in resume. Return JSON keys tailored_resume and cover_letter.\nRESUME:\n"+resume_text[:14000]+"\nJOB:\n"+json.dumps(job)[:8000]}])
    return json.loads(res.choices[0].message.content or "{}")
