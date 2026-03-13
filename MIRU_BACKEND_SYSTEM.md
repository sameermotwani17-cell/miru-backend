# MIRU Backend System

## Overview

MIRU backend provides a deterministic Japanese interview simulation and evaluation pipeline.

Core capabilities:
- Deterministic interview flow using fixed question IDs and category progression.
- Per-turn evaluation with structured scoring output.
- Debrief scoring across cultural-fit dimensions.
- Feedback generation and final report assembly.
- Cache-first results retrieval endpoints.
- Transcript retrieval endpoint for frontend display.

## Main Modules

- `services/`
  - Interview turn orchestration
  - Debrief scoring engine
  - Feedback/report generation
  - Analytics transformations

- `api/`
  - Result endpoints (`/radar`, `/report`, `/feedback`, `/results`)
  - Transcript endpoint (`/transcript`)

- `store/`
  - Session and turn persistence
  - Cached interview result storage

- `tests/`
  - Interview flow and pipeline validation
  - Debrief and feedback behavior checks

## Runtime Notes

- API is built with FastAPI.
- Python dependencies are listed in `requirements.txt`.
- Entry point is `main.py`.