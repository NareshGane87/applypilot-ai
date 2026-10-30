# ApplyPilot AI — Global job search & application workspace

An MVP starter for a standalone AI-assisted job application SaaS. It includes a Next.js dashboard, FastAPI API, user authentication, resume parsing, AI profile extraction/drafting, public Greenhouse/Lever job-board discovery, job matching, saved applications and an approval-gated application tracker.

## Important product boundaries

- This MVP **does not automatically submit applications**. It saves jobs, drafts application materials and opens the employer's official application page. The user remains in control.
- Job-board coverage is intentionally limited to configured public employer boards. Global, all-industry coverage requires a production job-data provider contract/API or an expanded list of public employer boards. Do not scrape sites or bypass CAPTCHAs, logins, rate limits or terms of service.
- AI-generated resume and cover-letter drafts must be checked by the candidate. The model is instructed not to invent credentials or experience.
- This is an MVP scaffold, not a production-certified service. Before public launch add managed Postgres, object storage, email verification, password reset, rate limits, audit logs, encryption/key management, malware scanning, privacy/deletion workflows, observability, tests and legal review.

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Set SECRET_KEY to a random secret. Set OPENAI_API_KEY to enable AI features.
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. Backend URL defaults to http://localhost:8000/api.

### 3. Docker Compose

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local`, configure secrets, then run:

```bash
docker compose up --build
```

## Current API

- `POST /api/auth/register`, `POST /api/auth/login`
- `GET /api/me`, `PUT /api/profile`, `POST /api/profile/resume`
- `POST /api/jobs/sync`, `GET /api/jobs`
- `POST /api/applications`, `GET /api/applications`
- `POST /api/applications/{id}/draft`
- `PATCH /api/applications/{id}/status`
- `GET /api/dashboard`

## Job data expansion

Configure employer board identifiers in `backend/app/jobs.py` or integrate a licensed aggregator (for example Adzuna or another provider available in each target market). Store provider credentials only in server-side environment secrets. Normalize source records and deduplicate by provider + external ID. Respect provider terms, attribution and refresh limits.

## Production architecture recommendation

- Frontend: Vercel or Cloudflare Pages
- API: AWS ECS/Fargate, Render or Fly.io
- Database: managed PostgreSQL
- Resume objects: private S3/R2 bucket with short-lived signed URLs
- Async workflow: Celery/RQ + Redis for discovery, parsing and draft generation
- Secrets: cloud secret manager
- Email: verified transactional email provider
- Monitoring: structured logs, error tracking and audit events

## Suggested next milestones

1. Add PostgreSQL migrations (Alembic), automated tests and tenant-safe authorization.
2. Add configurable employer-board registry and licensed job aggregator integration.
3. Add robust profile onboarding, resume versioning and candidate-controlled resume variants.
4. Add consent-based email alerts and interview scheduling.
5. Add browser-assisted application workflows only for sites where permitted, with explicit per-application user confirmation and a complete audit trail.
6. Add billing, usage limits and admin console.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Render + PostgreSQL API and Vercel frontend deployment handoff. Never commit API keys.
