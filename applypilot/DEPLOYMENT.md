# ApplyPilot AI — deployment handoff

This repository is prepared for a split deployment: FastAPI + managed PostgreSQL on Render, and the Next.js frontend on Vercel.

## What is prepared

- `render.yaml` provisions the API service and managed PostgreSQL database.
- Render generates `SECRET_KEY`; configure `OPENAI_API_KEY` and `CORS_ORIGINS` in the Render service environment.
- The backend normalizes Render PostgreSQL URLs and rejects unsafe development defaults in production.
- `frontend/vercel.json` configures the Next.js deployment.

## Deploy steps

1. Create a private GitHub repository and upload the contents of this project folder (`applypilot-ai/`) to its root.
2. In Render, choose **New → Blueprint**, connect the repository, and apply `render.yaml`.
3. In the Render API service environment, set:
   - `OPENAI_API_KEY`: your server-side OpenAI API key (never add it to the frontend or commit it).
   - `CORS_ORIGINS`: the exact Vercel production origin, e.g. `https://your-project.vercel.app` (no trailing slash; add preview origins only if needed).
4. In Vercel, import the same GitHub repository and set **Root Directory** to `frontend`.
5. Set Vercel environment variable `NEXT_PUBLIC_API_URL` to `https://<your-render-api-host>/api`, then deploy.
6. Copy the final Vercel origin into Render's `CORS_ORIGINS` and redeploy the API.
7. Verify `https://<your-render-api-host>/api/health`, register a test account, upload a sample resume, sync jobs and generate one draft.

## Required external accounts / credentials

- GitHub account/repository (for source control and deployment handoff).
- Render account (API + PostgreSQL hosting).
- Vercel account (Next.js hosting).
- OpenAI API key (AI profile extraction and application drafting).

Configure secrets only in Render/Vercel project settings. Do not paste API keys into chat, source code, GitHub, or `NEXT_PUBLIC_*` variables.

## Current MVP boundaries — read before public launch

- Current job sync is a connector demonstration using four configured public employer boards (Stripe, Figma, Netflix, Shopify). It is not comprehensive global coverage or an all-industry aggregator.
- Greenhouse and Lever expose public job-posting reads for individual employer boards. Their APIs do not provide a universal directory of every employer using those ATS platforms. Greenhouse application submission requires employer-side credentials; Lever's custom application endpoint is rate-limited. Keep external applications as user-reviewed handoffs until an approved integration and its permissions are in place. See the official docs: https://docs.greenhouse.io/job-board and https://github.com/lever/postings-api.
- The MVP does not submit applications automatically. It saves opportunities and drafts materials; candidates must review and submit through the employer's permitted application flow.
- The backend currently creates tables at startup. Before production scale, add Alembic migrations, automated tests, email verification/password reset, rate limiting, audit logging, malware scanning, private object storage for resumes, encryption/key management, data export/deletion workflows and monitoring.
- Review privacy, retention, employment, anti-discrimination and AI disclosure obligations for each launch market before public release.
