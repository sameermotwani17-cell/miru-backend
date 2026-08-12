# MIRU

Japanese interview simulation and cultural-fit evaluation. One repository,
two deployables, both on Vercel.

```
miru/
├── frontend/    Next.js 16 · React 19 · Tailwind 4      → Vercel project #1
└── backend/     FastAPI · Postgres · gpt-4o-mini        → Vercel project #2
```

The frontend and backend used to live in separate repositories. They are now
merged here with their histories intact — `git log --follow frontend/<file>`
still reaches the original commits.

---

## Deploying

Two Vercel projects, both created from **this** repository. They differ only
in Root Directory.

| | Frontend | Backend |
|---|---|---|
| Root Directory | `frontend` | `backend` |
| Framework Preset | Next.js | Other |
| Env vars | `NEXT_PUBLIC_API_URL` | `DATABASE_URL`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |

Deploy the backend first, then set the frontend's `NEXT_PUBLIC_API_URL` to the
backend's deployment URL.

To stop each project rebuilding when the other half changes, set an **Ignored
Build Step** in Vercel:

```bash
# frontend project
git diff --quiet HEAD^ HEAD -- ../frontend
# backend project
git diff --quiet HEAD^ HEAD -- ../backend
```

### Why two projects rather than one

A single project with same-origin `/api` routes would remove CORS and the
`NEXT_PUBLIC_API_URL` round trip, but it requires the Next.js app to sit at
the repository root alongside the Python modules, and Vercel turns every
`.py` file under `api/` into its own function — the Hobby plan allows 12.
Two projects keep each half's build unambiguous. Details in
[`backend/README.md`](backend/README.md#-deployment).

---

## Running locally

```bash
# backend  → http://localhost:8000
cd backend
pip install -r requirements.txt
cp .env.example .env      # fill in DATABASE_URL and OPENAI_API_KEY
uvicorn main:app --reload --port 8000

# frontend → http://localhost:3000
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

## Verifying

```bash
cd backend

# unit tests
python -m pytest tests/ -q

# full lifecycle against a live server, no API keys required
MIRU_STUB_LLM=1 python tests/gauntlet.py --spawn

# or against a deployment
python tests/gauntlet.py --base-url https://<your-backend>.vercel.app
```

The gauntlet asserts every lifecycle claim in `backend/README.md` and checks
each response against the TypeScript types in `frontend/src/lib/types.ts`. It
reports missing secrets and an unreachable database as warnings, so a broken
contract is distinguishable from an unconfigured environment.

`GET /health` reports which dependencies a running deployment actually has.
