from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.interview_results import interview_results_router
from routers.session import router as session_router


app = FastAPI(title="MIRU Backend", version="0.1.0")

# Allow all origins for now; tighten in production if needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(session_router)
app.include_router(interview_results_router)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
