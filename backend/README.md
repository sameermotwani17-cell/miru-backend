<div align="center">

```
███╗   ███╗██╗██████╗ ██╗   ██╗
████╗ ████║██║██╔══██╗██║   ██║
██╔████╔██║██║████╔╝██║   ██║
██║╚██╔╝██║██║██╔══██╗██║   ██║
██║ ╚═╝ ██║██║██║  ██║╚██████╔╝
╚═╝     ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝
     ミル — AI Interview Intelligence
```

**The brain behind Japan's most realistic interview simulator**

*Evaluate. Score. Coach. Repeat.*

---

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python)](https://python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai)](https://openai.com/)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-FF6B35?style=for-the-badge)](https://elevenlabs.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=for-the-badge&logo=postgresql)](https://supabase.com/)
[![Vercel](https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel)](https://vercel.com/)

</div>

---

## 🧠 What is MIRU Backend?

The **MIRU Backend** is a FastAPI-powered intelligence engine that simulates the inner workings of a Japanese HR department. It doesn't just answer questions — it *evaluates, scores, coaches, and reports* on every word your candidates speak.

Built around **GPT-4o-mini with JSON schema enforcement**, it delivers structured, reproducible interview sessions while measuring cultural alignment across five Japanese corporate dimensions. After each interview, it synthesizes a full coaching debrief — all in just **2 LLM calls per session**.

> *"Two calls. Five dimensions. One verdict: Hire or No Hire."*

---

## ✨ What It Does

| Capability | Details |
|-----------|---------|
| 🎯 **Interview Orchestration** | Time-bounded, turn-limited sessions with graceful completion |
| 🧮 **Cultural Scoring** | 5 Japanese HR dimensions scored live per answer turn |
| 🗣️ **Multilingual AI Persona** | HR interviewer voices in English and Japanese |
| 🔊 **Text-to-Speech** | ElevenLabs integration returning base64 MP3 audio |
| 📋 **Coaching Engine** | Per-question feedback + stronger rewritten answers |
| 📊 **Radar Analytics** | 5-dimension radar scores for frontend visualization |
| 💾 **Persistent Storage** | Turns → JSON files · Results → PostgreSQL (Supabase) |
| 🔁 **Resilient Architecture** | In-memory fallbacks, retry logic, anti-hallucination guards |

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND                             │
│         Vercel Next.js project (frontend/)                       │
└───────────────────────────┬──────────────────────────────────────┘
                            │  HTTP REST
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                            │
│         Vercel Python Function (backend/api/index.py)            │
│                                                                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  /session   │  │  /interview  │  │   /interview/results    │ │
│  │   Router    │  │    Router    │  │        Router           │ │
│  └──────┬──────┘  └──────┬───────┘  └────────────┬────────────┘ │
└─────────┼────────────────┼───────────────────────┼──────────────┘
          │                │                        │
          ▼                ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│                                                                   │
│  interview_engine ──► debrief_engine ──► feedback_engine        │
│       │                    │                    │                │
│       ▼                    ▼                    ▼                │
│  system_prompt         llm_client          voice_service        │
│  (4-layer assembly)   (gpt-4o-mini)       (ElevenLabs TTS)      │
└─────────────────────────────────────────────────────────────────┘
          │                │
          ▼                ▼
┌──────────────┐  ┌────────────────────────────────────────────── ┐
│  JSON Files  │  │           PostgreSQL (Supabase)                │
│  data/       │  │  interview_results(session_id, results JSONB) │
│  interviews/ │  │                                                │
│  {id}.json   │  └───────────────────────────────────────────────┘
└──────────────┘
```

---

## 🔄 Interview Lifecycle

```
  POST /api/session/start
          │
          ▼
   SessionState created
   (in-memory, timer set)
          │
          ▼
  POST /api/interview/turn  ◄─────────────────────────┐
          │                                             │
          ▼                                             │
  Reconstruct history                                  │
  from JSON turns (anti-injection)                     │
          │                                             │
          ▼                                             │
  Assemble 4-layer system prompt                       │
          │                                             │
          ▼                                             │
  ┌───────────────────────┐                            │
  │   OpenAI gpt-4o-mini  │                            │
  │   JSON schema output  │                            │
  │ ┌─────────────────────┤                            │
  │ │ interviewer_response│                            │
  │ │ next_question       │                            │
  │ │ scores (5 dims)     │                            │
  │ │ is_wrapping_up      │                            │
  └─┴─────────────────────┘                            │
          │                                             │
          ▼                                             │
  Duplicate question check                             │
  (difflib ≥75% similarity blocked)                   │
          │                                             │
          ▼                                             │
  Store turn to JSON file                              │
          │                                             │
          ▼                                             │
  TTS via ElevenLabs (optional)                        │
          │                                             │
          ▼                                             │
  Return JSON to frontend ────────────────────────────►┘
          │
   interview_complete?
          │
          ▼
  ┌───────────────────────────────────────────────────┐
  │              DEBRIEF PIPELINE                     │
  │                                                   │
  │  generate_interview_debrief()                     │
  │    └─► evaluate all answers → overall_scores      │
  │                                                   │
  │  generate_full_feedback_package()                 │
  │    └─► batch per-question coaching (1 LLM call)   │
  │    └─► final report generation (1 LLM call)       │
  │                                                   │
  │  save_interview_results() → Postgres + cache      │
  └───────────────────────────────────────────────────┘
          │
          ▼
  GET /api/interview/results
  (frontend polls until status="ready")
```

---

## 🗂️ Project Structure

```
miru-backend/
│
├── api/
│   └── index.py                   ▲ Vercel function entrypoint (only file here)
│
├── main.py                        🚀 FastAPI app + CORS + /health
│
├── routers/
│   ├── session.py                 🔑 POST/GET/DELETE /session/*
│   ├── interview.py               🎙️ POST /interview/turn
│   ├── interview_results.py       📊 GET results, radar, feedback, transcript
│   └── voice.py                   🔊 POST /voice/tts (server-side ElevenLabs)
│
├── services/
│   ├── interview_engine.py        🧠 Core interview orchestration (667 lines)
│   ├── debrief_engine.py          📋 Post-interview scoring & analysis
│   ├── feedback_engine.py         💬 Coaching feedback + answer rewrites
│   ├── analytics_engine.py        📡 Radar chart data formatting
│   ├── llm_client.py              🤖 OpenAI wrapper (JSON schema enforced)
│   ├── voice_service.py           🔊 ElevenLabs TTS → base64 MP3
│   └── score_dimensions.py        📐 5 Japanese HR dimension definitions
│
├── models/
│   ├── session.py                 📦 SessionState dataclass
│   └── interview_turn.py          📝 InterviewTurn dataclass
│
├── store/
│   ├── sessions.py                💾 Postgres-backed session state
│   ├── interview_turns.py         🗄️ Postgres-backed turn transcript
│   ├── interview_results.py       🗄️ Postgres + in-memory fallback
│   └── db.py                      🔌 PostgreSQL connection manager
│
├── prompts/
│   ├── system_prompt.py           🏗️ 4-layer prompt assembler
│   ├── hr_personality.py          👔 Base HR persona
│   ├── company_loader.py          🏢 Company profile loader
│   ├── hr_en.txt                  🇺🇸 English HR prompt
│   ├── hr_jp.txt                  🇯🇵 Japanese HR prompt
│   └── companies/
│       ├── toyota_en.txt          🚗 Toyota EN profile
│       ├── toyota_jp.txt          🚗 Toyota JP profile
│       └── ...                    (Rakuten, Sony, SoftBank, Uniqlo)
│
├── tests/
│   ├── gauntlet.py                🎯 End-to-end README lifecycle harness
│   ├── test_interview_engine.py   🧪 Engine + results unit tests
│   └── test_voice_service.py      🧪 TTS smoke test
│
├── config.py                      ⚙️ dotenv loader
├── requirements.txt               📦 Python dependencies
└── vercel.json                    ▲ Function config + catch-all rewrite
```

---

## 📡 API Reference

### Session Management

```http
POST /api/session/start
Content-Type: application/json

{
  "user_name": "Sameer",
  "target_role": "Software Engineer",
  "company": "toyota",
  "language_mode": "en",
  "duration_mins": 15,
  "cv_text": "..."
}
```

```json
{
  "session_id": "uuid-v4-here",
  "timer_end_epoch": 1742412345678
}
```

---

```http
GET /api/session/{session_id}/state
DELETE /api/session/{session_id}
```

---

### Interview Turn

```http
POST /api/interview/turn
Content-Type: application/json

{
  "session_id": "uuid-v4-here",
  "user_message": "I led a cross-functional team to deliver the project.",
  "force_complete": false,
  "voice_mode": true
}
```

```json
{
  "interviewer_response": "Thank you for sharing that experience.",
  "next_question": "How did you handle conflict within your team?",
  "scores": {
    "wa_teamwork": 7,
    "loyalty_commitment": 6,
    "humility": 8,
    "kaizen_growth": 7,
    "cultural_fit": 7
  },
  "interview_complete": false,
  "debrief_ready": false,
  "voice_audio": "base64-encoded-mp3..."
}
```

---

### Results & Analytics

| Endpoint | Returns |
|----------|---------|
| `GET /api/interview/results?session_id=` | Full results package (poll until `status: "ready"`) |
| `GET /api/interview/{id}/radar` | 5-dimension radar scores |
| `GET /api/interview/{id}/feedback` | Per-question coaching + rewrites |
| `GET /api/interview/{id}/report` | Final HR assessment report |
| `GET /api/interview/{id}/transcript` | Full Q&A history |
| `GET /api/interview/{id}/debrief-status` | `processing` \| `ready` |

---

### Health Checks

```http
GET /          →  {"status": "MIRU backend running"}
GET /health    →  {"ok": true}
```

---

## 🎭 The 5 Japanese HR Dimensions

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                    │
│  和  WA (TEAMWORK HARMONY)           協調性                       │
│      High: "We achieved" · credits team · group outcomes         │
│      Low:  "I did it alone" · dominant I-language                │
│                                                                    │
│  忠  LOYALTY & COMMITMENT            忠誠心                       │
│      High: Long-term signals · stability language                │
│      Low:  "stepping stone" · job-hopping references             │
│                                                                    │
│  謙  HUMILITY                        謙虚さ                       │
│      High: Achievements credited to team/circumstances           │
│      Low:  "I am the best" · overconfidence                      │
│                                                                    │
│  改  KAIZEN (GROWTH MINDSET)         成長意欲                     │
│      High: Improve within company · continuous improvement       │
│      Low:  "start own company" · personal skill expansion        │
│                                                                    │
│  文  CULTURAL FIT                    文化適合                     │
│      High: Company value refs · process respect · keigo-aware    │
│      Low:  Casual language · ignoring hierarchy · WLB complaints │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Hiring Signal Thresholds

```python
avg = sum(scores.values()) / 5

avg >= 7.5  →  ✅ "Strong Hire"
avg >= 6.0  →  ✅ "Hire"
avg >= 4.5  →  ⚠️  "Borderline"
avg <  4.5  →  ❌ "No Hire"
```

---

## 🧠 The 4-Layer Prompt Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1 — HR PERSONA                                           │
│  Role definition · Interview style · Evaluation framework       │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2 — COMPANY PROFILE                                       │
│  Mission/values · Hiring personality · Cultural signals         │
│  Source: prompts/companies/{company}_{lang}.txt                 │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3 — CANDIDATE & SESSION CONTEXT                           │
│  Name · Role · CV text · Language mode · Duration               │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 4 — OUTPUT FORMAT & RULES                                 │
│  JSON schema enforcement · Scoring guidance                     │
│  interviewer_response: NO question marks allowed                │
│  next_question: MUST contain exactly one ?                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance Design

### 2 LLM Calls Per Interview

```
Traditional (naive) approach:
├── Per-question feedback  →  N calls
├── Rewrite suggestions    →  N calls
└── Final report           →  1 call
Total: 2N + 1 calls per interview

MIRU optimized approach:
├── Batch feedback generation  →  1 call
└── Final report generation    →  1 call
Total: 2 calls per interview  ✅
```

### Result Caching Pipeline

```
Interview completes
       │
       ▼
Generate debrief (1 LLM call)
       │
       ▼
Generate feedback + report (1 LLM call)
       │
       ▼
Save to Postgres + in-memory cache
       │
       ▼
All subsequent GET requests → instant cache hits
```

---

## 🛡️ Anti-Hallucination Safeguards

| Guard | Mechanism |
|-------|-----------|
| **Duplicate detection** | `difflib.SequenceMatcher` blocks questions with ≥75% similarity |
| **History reconstruction** | Turns rebuilt from JSON files — client cannot inject or override |
| **JSON schema enforcement** | OpenAI forced to return structured output with field validation |
| **Score conservatism** | Scores of 8+ require explicit behavioral evidence in the prompt |
| **TTS degradation** | Returns empty string if ElevenLabs fails — never crashes turn |
| **DB fallback** | In-memory dict catches Postgres outages transparently |

---

## 🗄️ Data Models

### SessionState (In-Memory)

```python
@dataclass
class SessionState:
    session_id: str
    user_name: str
    target_role: str
    company: str                      # "toyota" | "rakuten" | ...
    language_mode: str                # "en" | "jp"
    duration_mins: int
    timer_end_epoch: int              # ms since epoch
    conversation_history: List[Any]
    turn_count: int
    running_scores: Dict[str, float]  # 5 dimensions
    cv_context: Optional[str]
```

### Interview Turn (JSON → `data/interviews/{id}.json`)

```json
{
  "turn_index": 3,
  "question_id": "Q_TEAM_01",
  "question": "Tell me about a time you resolved a conflict.",
  "answer": "I discussed the issue directly with the team.",
  "interviewer_response": "That shows good communication awareness.",
  "scores": {
    "wa_teamwork": 7,
    "loyalty_commitment": 6,
    "humility": 7,
    "kaizen_growth": 6,
    "cultural_fit": 7
  },
  "feedback": "Good collaborative framing, but credit the team more.",
  "better_example": "We as a team worked through the conflict together...",
  "timestamp": "2026-03-19T12:34:56Z"
}
```

### PostgreSQL Schema

```sql
CREATE TABLE interview_results (
    session_id  TEXT        PRIMARY KEY,
    results     JSONB       NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 🚀 Running the Backend

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Fill in your API keys (see below)

# Start the server
uvicorn main:app --reload --port 8000
```

API will be live at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

### Environment Variables

Set these in the Vercel **backend** project (Settings → Environment Variables),
and in a local `.env` for development:

| Variable | Required | Purpose | If missing |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | Postgres/Supabase connection | State is memory-only and lost on every cold start |
| `OPENAI_API_KEY` | **Yes** | gpt-4o-mini interview + scoring | Turn endpoint 500s; debrief falls back to canned text |
| `ELEVENLABS_API_KEY` | No | Server-side TTS | `voice_audio` is empty, interview still works |
| `ELEVENLABS_VOICE_ID` | No | Voice selection | Falls back to the built-in default voice |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS allowlist | Defaults to `*` |
| `MIRU_STUB_LLM` | No | Dev only: canned LLM responses | Unset in production |

```env
# .env
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=your-voice-id
DATABASE_URL=postgresql://user:pass@host:6543/postgres?sslmode=require
```

> Use Supabase's **pooler** connection string (port `6543`), not the direct
> database host. Each serverless invocation can open its own connection, and
> a direct connection will exhaust Postgres' connection limit under load.

Check what the running deployment actually has:

```bash
curl https://<your-backend>.vercel.app/health
```

```json
{
  "ok": true,
  "database": { "alive": true, "detail": "connected" },
  "openai_key_set": true,
  "elevenlabs_key_set": true,
  "elevenlabs_voice_id_set": true
}
```

---

## 🎯 The Gauntlet

`tests/gauntlet.py` turns each promise in this README into an assertion and
runs them against a live server, looping until they pass or the round budget
runs out. It is the check that this document is still true.

```bash
# Locally, no API keys needed — stubs the LLM, uses in-memory state
MIRU_STUB_LLM=1 python tests/gauntlet.py --spawn

# Against a deployment
python tests/gauntlet.py --base-url https://<your-backend>.vercel.app
```

It walks the documented lifecycle end to end — `session/start` →
`interview/turn` loop → `interview_complete` → poll `results` until
`status: "ready"` → every debrief endpoint → `DELETE session` — and checks
each response against the TypeScript types the frontend is written to.
Missing keys, out-of-range scores and non-terminating polls all fail loudly.
Missing API keys and an unreachable database are reported as warnings rather
than failures, so you can tell a broken contract apart from a missing secret.

Exit code is 0 only when every check passes.

---

## 🧪 Test Suite

```bash
# Run all tests
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_interview_flow.py      # Question progression
python -m pytest tests/test_debrief_engine.py      # Scoring accuracy
python -m pytest tests/test_feedback_engine.py     # Coaching output
python -m pytest tests/test_miru_full_pipeline.py  # Full integration
```

| Suite | Validates |
|-------|-----------|
| `test_interview_flow` | Question ordering, turn limits, completion triggers |
| `test_debrief_engine` | Score calculation across 5 dimensions |
| `test_feedback_engine` | Coaching text quality, rewrite structure |
| `test_miru_full_pipeline` | End-to-end session lifecycle |

---

## 📦 Dependencies

```
fastapi==0.115.0          # Async web framework
uvicorn==0.30.0           # ASGI server
openai==1.58.0            # GPT-4o-mini (primary LLM)
elevenlabs==1.13.0        # Text-to-speech
pydantic==2.9.0           # Data validation + serialization
psycopg2-binary==2.9.11   # PostgreSQL driver
python-multipart==0.0.18  # Multipart form data (CV upload)
python-dotenv==1.0.1      # Environment variable loading
anthropic==0.40.0         # Installed (reserved for future use)
```

---

## 🌐 Deployment

MIRU Backend runs as a **single Vercel Python Function**.

Create a Vercel project from this repository with **Root Directory =
`backend`** and Framework Preset **Other**. `vercel.json` does the rest:

```json
{
  "functions": { "api/index.py": { "memory": 1024, "maxDuration": 60 } },
  "rewrites": [{ "source": "/(.*)", "destination": "/api/index" }]
}
```

Every path is rewritten to the one function, and Vercel passes the original
URL through, so FastAPI still matches `/api/session/start` and friends.

`api/` deliberately contains only `index.py`: Vercel turns every `.py` file
under `api/` into its own function, and the Hobby plan caps you at 12.

### Serverless constraints this design accounts for

| Constraint | Consequence |
|---|---|
| No durable local disk | Session state and turns live in Postgres, not memory or JSON files |
| Instances freeze between requests | DB connections are re-checked and reconnected per request |
| 60s function ceiling (Hobby) | Debrief runs inline; a long interview can approach the limit |
| 4.5 MB response cap | Long `voice_audio` base64 payloads could exceed it |

---

## 🏢 Supported Companies

| Company | Interview Focus |
|---------|---------------|
| 🚗 **Toyota** | Kaizen mindset, nemawashi process respect, long-term loyalty |
| 🛍️ **Rakuten** | Englishization, entrepreneurial energy, Rakuten-ism alignment |
| 🎵 **Sony** | Creative innovation, maker culture, global thinking |
| 📱 **SoftBank** | Visionary disruption, 300-year plan ambition, speed |
| 👕 **Uniqlo** | Craftsmanship, Zenkai spirit, retail excellence |

---

## 🔗 Frontend Connection

This backend powers the Next.js frontend in [`../frontend`](../frontend).

The integration contract:
1. Frontend calls `/api/session/start` → receives `session_id`
2. Frontend loops `/api/interview/turn` → drives the interview
3. On `interview_complete: true && debrief_ready: true` → frontend navigates to debrief
4. Frontend polls `/api/interview/results?session_id=` → waits for `status: "ready"`
5. Frontend renders full debrief from results payload

---

## 📄 License

MIT License — built with 💙 for cultural bridges.

---

<div align="center">

**ミル — We evaluate what others can't see.**

*Powered by GPT-4o-mini · ElevenLabs · Supabase · Vercel*

</div>
