# MIRU - AI Interview Coaching Backend

<p align="left">
	<img src="https://img.shields.io/badge/MIRU-Backend-1D4ED8?style=for-the-badge" alt="MIRU Backend" />
	<img src="https://img.shields.io/badge/FastAPI-API-2563EB?style=for-the-badge" alt="FastAPI" />
	<img src="https://img.shields.io/badge/Pipeline-Feature%20Complete-3B82F6?style=for-the-badge" alt="Pipeline" />
	<img src="https://img.shields.io/badge/Status-Ready%20for%20Frontend-60A5FA?style=for-the-badge" alt="Status" />
</p>

MIRU is an AI-powered interview training system designed to simulate structured interviews, evaluate candidate responses, and generate actionable coaching feedback aligned with Japanese hiring culture.

The backend provides a complete pipeline for:

- Running structured interview sessions
- Evaluating candidate answers
- Generating cultural-fit scoring
- Producing coaching feedback and answer rewrites
- Delivering final interview reports
- Serving results through a FastAPI API layer

This repository contains the backend intelligence layer of MIRU.

## Features

### Structured Interview Engine

MIRU runs deterministic interview flows using a fixed question registry.

Example interview flow:

```text
Q_STD_01
Q_STD_02
Q_BEHAVIOR_01
Q_TEAM_01
Q_FAILURE_01
Q_CLOSING_01
```

This prevents AI hallucinations and enables consistent evaluation.

### Cultural Scoring Engine

Each answer is evaluated across dimensions aligned with Japanese hiring expectations.

Evaluation dimensions:

- Wa (Teamwork Harmony)
- Loyalty / Long-term Commitment
- Humility
- Kaizen (Growth Mindset)
- Cultural Fit

Example scoring output:

```json
{
	"wa_teamwork": 7,
	"loyalty_commitment": 6,
	"humility": 7,
	"kaizen_growth": 8,
	"cultural_fit": 6
}
```

### AI Coaching Feedback

MIRU generates:

- Per-question feedback
- Improvement suggestions
- Stronger rewritten answers

Example rewrite:

User answer:

```text
I solved the problem myself.
```

MIRU rewrite:

```text
I discussed the issue with my teammates and together we reached a solution.
```

### Final Interview Report

After the interview completes, MIRU produces a structured report.

Example:

```json
{
	"overall_summary": "...",
	"strengths": ["team collaboration", "learning mindset"],
	"improvement_areas": ["individual language", "commitment clarity"],
	"recommended_focus": "emphasize teamwork impact",
	"overall_scores": {"wa_teamwork": 7.4, "loyalty_commitment": 6.3, "humility": 7.1, "kaizen_growth": 8.0, "cultural_fit": 6.8}
}
```

### Radar Chart Analytics

The system provides score data for frontend visualization.

Example response:

```json
{
	"wa_teamwork": 7.4,
	"loyalty_commitment": 6.3,
	"humility": 7.1,
	"kaizen_growth": 8.0,
	"cultural_fit": 6.8
}
```

### Interview Transcript Review

The API exposes full interview history for post-interview analysis.

Example:

```json
{
	"turns": [
		{
			"question_id": "Q_STD_01",
			"question": "Please introduce yourself.",
			"answer": "I am Sameer."
		}
	]
}
```

## System Architecture

```text
Interview Session
				|
				v
Interview Engine
				|
				v
Question Registry
				|
				v
Session Turn Storage
				|
				v
Debrief Engine
				|
				v
Feedback Engine
				|
				v
Result Cache
				|
				v
Analytics Engine
				|
				v
FastAPI API Layer
```

## Core Interview Pipeline

```text
User Answer
		|
		v
run_interview_turn()
		|
		v
Question progression
		|
		v
Turn stored
		|
		v
Interview completion
		|
		v
generate_interview_debrief()
		|
		v
generate_full_feedback_package()
		|
		v
Results cached
		|
		v
API endpoints serve cached results
```

This ensures expensive AI generation only happens once per interview session.

## Project Structure

```text
miru-backend/
|
|-- api/
|   |-- interview_results.py
|
|-- services/
|   |-- question_registry.py
|   |-- interview_engine.py
|   |-- debrief_engine.py
|   |-- feedback_engine.py
|   |-- analytics_engine.py
|
|-- store/
|   |-- interview_turns.py
|   |-- interview_results.py
|   |-- sessions.py
|
|-- tests/
|   |-- test_interview_flow.py
|   |-- test_debrief_engine.py
|   |-- test_feedback_engine.py
|   |-- test_miru_full_pipeline.py
|
|-- main.py
`-- requirements.txt
```

## API Endpoints

### Radar Scores

`GET /api/interview/{session_id}/radar`

Returns radar chart metrics.

### Final Report

`GET /api/interview/{session_id}/report`

Returns the MIRU interview summary report.

### Question Feedback

`GET /api/interview/{session_id}/feedback`

Returns per-question feedback and rewrite suggestions.

### Full Results

`GET /api/interview/{session_id}/results`

Returns the full evaluation package.

### Interview Transcript

`GET /api/interview/{session_id}/transcript`

Returns full interview history.

## Performance Optimizations

### Result Caching

Final interview results are generated once per session and cached.

Flow:

```text
Interview completes
		|
		v
Generate results
		|
		v
Save results to cache
		|
		v
API reads cached results
```

This prevents repeated LLM calls.

### LLM Call Optimization

Naive architecture:

- Per-question feedback -> multiple calls
- Rewrite suggestions -> multiple calls
- Final report -> one call

Optimized architecture:

- Batch feedback generation -> 1 call
- Final report generation -> 1 call

Total:

2 LLM calls per interview

## Testing

The backend includes four test suites:

| Test | Purpose |
|---|---|
| test_interview_flow.py | question progression |
| test_debrief_engine.py | scoring engine |
| test_feedback_engine.py | feedback output |
| test_miru_full_pipeline.py | full system integration |

All tests passed successfully.

## Running the Backend

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

## Next Development Phase

Frontend development will provide:

- Interview UI
- Radar chart dashboard
- Answer review interface
- Final report viewer

Voice interaction may later be added using:

- Speech-to-text
- Text-to-speech

## Status

Backend development for MIRU is feature complete.

The system now supports:

- Structured interview simulation
- Cultural scoring
- Coaching feedback generation
- Answer rewriting
- Final interview reports
- Cached API results
- Radar chart analytics
- Transcript review

## License

MIT License