import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.interview_routes import interview_router
from api.interview_results import interview_results_router
from routers.session import router as session_router

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

app = FastAPI(title="MIRU Backend", version="0.1.0")


@app.on_event("startup")
async def verify_db_connection() -> None:
    """Confirm Supabase connectivity on startup so failures surface immediately."""
    try:
        from store.db import get_cursor
        cur = get_cursor()
        cur.execute("SELECT 1")
        LOGGER.info("[STARTUP] Connected to Supabase database ✓")
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("[STARTUP] Database connection FAILED: %s", exc)

# allow_credentials must be False when allow_origins=["*"] (CORS spec requirement).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(session_router)
app.include_router(interview_router)
app.include_router(interview_results_router)


@app.get("/")
async def root() -> dict:
    return {"status": "MIRU backend running"}


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
