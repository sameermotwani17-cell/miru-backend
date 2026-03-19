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
[![Railway](https://img.shields.io/badge/Railway-Deployed-0B0D0E?style=for-the-badge&logo=railway)](https://railway.app/)

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
│              https://miru-frontend.vercel.app                    │
└───────────────────────────┬──────────────────────────────────────┘
                            │  HTTP REST
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                            │
│              https://miru-backend-production.up.railway.app      │
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
├── main.py                        🚀 FastAPI entry point + CORS
│
├── api/
│   ├── interview_routes.py        🎙️ POST /interview/turn
│   └── interview_results.py       📊 GET results, radar, feedback, transcript
│
├── routers/
│   └── session.py                 🔑 POST/GET/DELETE /session/*
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
│   ├── sessions.py                💾 In-memory session dict
│   ├── interview_turns.py         📁 JSON file persistence
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
├── data/
│   └── interviews/
│       └── {session_id}.json      📂 Turn-by-turn interview records
│
├── tests/
│   ├── test_interview_flow.py     🧪 Question progression tests
│   ├── test_debrief_engine.py     🧪 Scoring accuracy tests
│   ├── test_feedback_engine.py    🧪 Coaching output tests
│   └── test_miru_full_pipeline.py 🧪 Full integration test suite
│
├── config.py                      ⚙️ dotenv loader
├── requirements.txt               📦 Python dependencies
├── Dockerfile                     🐳 Container definition
└── railway.toml                   🚂 Railway deployment config
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

```env
# .env
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=your-voice-id
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### Docker

```bash
docker build -t miru-backend .
docker run -p 8000:8000 --env-file .env miru-backend
```

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

MIRU Backend is deployed on **Railway** with automatic deploys on push:

```toml
# railway.toml
[build]
builder = "DOCKERFILE"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

Production URL: `https://miru-backend-production.up.railway.app`

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

This backend powers the [MIRU Frontend](../../miru-frontend) Next.js application.

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

*Powered by GPT-4o-mini · ElevenLabs · Supabase · Railway*

</div>
