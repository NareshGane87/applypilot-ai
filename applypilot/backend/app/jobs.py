import httpx
from sqlalchemy.orm import Session
from .models import Job
from .config import settings

async def sync_public_boards(db: Session, query: str = "") -> int:
    """Imports public Greenhouse and Lever job-board listings. Uses board/company slugs, not private account APIs."""
    added = 0
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent":"ApplyPilotAI/0.1 (job discovery)"}) as client:
        # These public boards are examples; production should use configured employer slugs and/or licensed aggregators.
        boards = [("greenhouse", "stripe"), ("greenhouse", "figma"), ("lever", "netflix"), ("lever", "shopify")]
        for source, slug in boards:
            try:
                if source == "greenhouse":
                    r = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
                    if r.status_code != 200: continue
                    rows = r.json().get("jobs", [])
                    for x in rows:
                        title = x.get("title", "")
                        if query and query.lower() not in title.lower() and query.lower() not in x.get("content", "").lower(): continue
                        ext = str(x.get("id"))
                        if db.query(Job).filter_by(source=source, external_id=ext).first(): continue
                        loc = (x.get("location") or {}).get("name", "Not specified")
                        db.add(Job(external_id=ext, source=source, title=title, company=slug.title(), location=loc,
                                   description=(x.get("content") or "")[:15000], url=x.get("absolute_url", ""),
                                   remote="remote" in loc.lower(), posted_at="")); added += 1
                else:
                    r = await client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
                    if r.status_code != 200: continue
                    for x in r.json():
                        title = x.get("text", "")
                        desc = x.get("descriptionPlain", "")
                        if query and query.lower() not in title.lower() and query.lower() not in desc.lower(): continue
                        ext = str(x.get("id"))
                        if db.query(Job).filter_by(source=source, external_id=ext).first(): continue
                        cats = x.get("categories") or {}
                        loc = cats.get("location", "Not specified")
                        db.add(Job(external_id=ext, source=source, title=title, company=slug.title(), location=loc,
                                   description=desc[:15000], url=x.get("hostedUrl", ""),
                                   remote="remote" in loc.lower(), employment_type=cats.get("commitment", "Not specified"))); added += 1
            except (httpx.HTTPError, ValueError, KeyError):
                continue
    db.commit()
    return added

async def sync_jsearch(db: Session, query: str = "", location: str = "India") -> int:
    """Imports live listings from the licensed JSearch API (RapidAPI), which aggregates LinkedIn, Naukri, Indeed and other boards.
    The key stays in server-side env (RAPIDAPI_KEY). No scraping is done by this app."""
    import hashlib
    if not settings.rapidapi_key:
        return 0
    search = f"{query.strip() or 'software developer'} in {location}"
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                params={"query": search, "num_pages": "1", "country": "in", "date_posted": "month"},
                headers={"X-RapidAPI-Key": settings.rapidapi_key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"},
            )
        if r.status_code != 200:
            return 0
        payload = r.json().get("data") or []
    except (httpx.HTTPError, ValueError):
        return 0
    # v5 returns {"data": {"jobs": [...], "cursor": ...}}; older versions return a plain list.
    rows = payload.get("jobs", []) if isinstance(payload, dict) else payload
    added = 0
    for x in rows:
        if not isinstance(x, dict):
            continue
        raw_id = str(x.get("job_id") or "")
        options = x.get("apply_options") or [{}]
        url = x.get("job_apply_link") or (options[0] or {}).get("apply_link") or x.get("job_google_link") or ""
        if not raw_id or not url:
            continue
        # JSearch ids can exceed 255 chars; store a stable hash instead.
        ext = raw_id if len(raw_id) <= 200 else hashlib.sha256(raw_id.encode()).hexdigest()
        publisher = (x.get("job_publisher") or "web").strip()
        source = ("jsearch:" + publisher.lower())[:40]
        if db.query(Job).filter_by(source=source, external_id=ext).first():
            continue
        loc = x.get("job_location") or ", ".join(p for p in [x.get("job_city"), x.get("job_state"), x.get("job_country")] if p) or "Not specified"
        db.add(Job(
            external_id=ext, source=source, title=(x.get("job_title") or "")[:255],
            company=(x.get("employer_name") or "Unknown")[:255], location=str(loc)[:255],
            description=(x.get("job_description") or "")[:15000], url=url,
            remote=bool(x.get("job_is_remote")), employment_type=(x.get("job_employment_type") or "Not specified")[:80],
            posted_at=str(x.get("job_posted_at_datetime_utc") or x.get("job_posted_at") or "")[:80],
        ))
        added += 1
    db.commit()
    return added

def score_job(profile, job: Job) -> float:
    import json, re
    skills = [s.lower() for s in json.loads(profile.skills or "[]")]
    titles = [s.lower() for s in json.loads(profile.target_titles or "[]")]
    text = (job.title + " " + job.description).lower()
    skill_hits = sum(1 for s in skills if s and s in text)
    skill_score = min(55, skill_hits / max(1, min(len(skills), 10)) * 55)
    title_score = 30 if any(t in job.title.lower() for t in titles if t) else 0
    remote_score = 10 if job.remote and "remote" in (profile.work_modes or "").lower() else 0
    experience_score = 5 if profile.years_experience > 0 else 0
    return round(min(100, skill_score + title_score + remote_score + experience_score), 1)
