import logging
import os

# Imported first, for its side effect: config loads .env into the environment.
# Nothing imported it before, so .env was silently ignored and the README's
# "cp .env.example .env" step did nothing — env vars only worked if they were
# already exported in the shell. This must stay above the imports below, since
# those pull in modules that read configuration.
import config  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.interview import interview_router
from routers.interview_results import interview_results_router
from routers.session import router as session_router
from routers.voice import voice_router

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

app = FastAPI(title="MIRU Backend", version="0.2.0")


def _allowed_origins() -> list[str]:
    """Origins allowed to call the API.

    Defaults to "*" so a preview deployment of the frontend works without
    reconfiguration. Set ALLOWED_ORIGINS to a comma-separated list to lock it
    down to your production domain.
    """
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


_origins = _allowed_origins()

# allow_credentials must be False when allow_origins=["*"] (CORS spec requirement).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(session_router)
app.include_router(interview_router)
app.include_router(interview_results_router)
app.include_router(voice_router)


@app.get("/")
async def root() -> dict:
    return {"status": "MIRU backend running"}


@app.get("/health")
async def health() -> dict:
    """Liveness plus dependency readiness.

    The database is probed here rather than at startup: on serverless a
    startup probe pays its latency cost on every cold start, and an
    import-time failure would take down this endpoint too — exactly when you
    need it to tell you what is misconfigured.
    """
    from store.db import ping

    db_alive, db_detail = ping()
    return {
        "ok": True,
        "database": {"alive": db_alive, "detail": db_detail},
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "elevenlabs_key_set": bool(os.getenv("ELEVENLABS_API_KEY")),
        "elevenlabs_voice_id_set": bool(os.getenv("ELEVENLABS_VOICE_ID")),
    }
