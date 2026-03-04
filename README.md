# Catalyst: Continuous Discovery

An AI-powered Continuous Discovery dashboard for Product Managers, inspired by [Teresa Torres' Continuous Discovery Habits](https://www.producttalk.org/continuous-discovery-habits/) framework.

Catalyst ingests raw user interview transcripts and uses LLMs to extract underlying unmet needs (not feature requests), deduplicate opportunities across personas, track evidence decay over time, and generate targeted pre-meeting interview scripts — all organized into a clean opportunity hierarchy.

---

## Features

- **AI Synthesis** — Upload interview transcripts; Gemini extracts unmet needs with verbatim evidence quotes
- **Smart Deduplication** — Automatically merges similar opportunities across multiple interviews based on root-cause friction, regardless of persona
- **Opportunity Ledger** — Full hierarchy: Outcomes → Opportunities (nested) → Solutions (nested) → Experiments
- **Evidence Tracking** — Color-coded decay semaphore (Green/Yellow/Red) based on recency of supporting evidence
- **Pre-Meeting Prep** — Generates aggressive, assumption-testing interview questions per persona
- **Multi-Workspace** — Create separate product workspaces, each with isolated data
- **LLM Cost Monitor** — Token usage dashboard with per-operation breakdowns
- **Authentication** — Single-user bcrypt login with session persistence

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | [Reflex](https://reflex.dev/) v0.8.27 (Python → React/Next.js) |
| **Database** | PostgreSQL via SQLModel + Alembic migrations (with pgvector for embeddings) |
| **AI / LLM** | Google Gemini 2.5 Pro (synthesis) + Gemini 2.5 Flash (deduplication) |
| **Auth** | bcrypt password hashing via `passlib` |
| **UI** | Radix UI v3 + Tailwind CSS v4 |

---

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/) (required by Reflex for the React build)
- **Git** — [git-scm.com](https://git-scm.com/)
- **PostgreSQL 14+** with the **pgvector** extension — [postgresql.org](https://www.postgresql.org/download/) / [pgvector](https://github.com/pgvector/pgvector)
- **A Google Gemini API key** — Get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

> **pgvector on macOS:** `brew install pgvector`
> **pgvector with Docker:** use the `pgvector/pgvector:pg17` image instead of plain `postgres`.

---

## Local Setup

### macOS

```bash
# 1. Clone the repository
git clone <repository-url>
cd cont-synth

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create a PostgreSQL database and enable pgvector
createdb contsynth
psql contsynth -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 5. Copy the example env file and fill in your values
cp .env.example .env
# Edit .env: set GEMINI_API_KEY and DATABASE_URL

# 6. Apply database migrations
alembic upgrade head

# 7. Start the development server
reflex run
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

### Windows (PowerShell)

```powershell
# 1. Clone the repository
git clone <repository-url>
cd cont-synth

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create a PostgreSQL database and enable pgvector
# (run these in psql or pgAdmin)
# CREATE DATABASE contsynth;
# \c contsynth
# CREATE EXTENSION IF NOT EXISTS vector;

# 5. Copy the example env file and fill in your values
Copy-Item .env.example .env
# Edit .env: set GEMINI_API_KEY and DATABASE_URL

# 6. Apply database migrations
alembic upgrade head

# 7. Start the development server
reflex run
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

> **Windows Note:** If you get an `ExecutionPolicy` error when activating the virtual environment, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key — get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `DATABASE_URL` | Yes | PostgreSQL connection string — defaults to `postgresql://postgres:postgres@localhost:5432/contsynth` |
| `API_URL` | No (prod only) | Public URL of the backend, e.g. `https://yourdomain.com:8000` — baked into the React bundle at build time |

> The `.env` file is gitignored and will never be committed.

---

## Default Credentials

When you run migrations for the first time, the database is seeded with a default admin account:

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin1234!` |

**Change your password immediately** after first login via the account settings modal (gear icon in the sidebar).

---

## Documentation

| Guide | Description |
|---|---|
| [**Opportunities — Full Lifecycle**](docs/opportunities.md) | How Opportunities are created, evidenced, structured into a tree, explored with Solutions, validated with Experiments, and prioritized using the Torres framework (Frequency · Impact · Satisfaction Gap) |

---

## Application Pages

| Page | Description |
|---|---|
| **Synthesize** | Paste or upload a transcript — AI extracts unmet needs with source quotes |
| **Synthesis Review** | Preview extracted opportunities with highlighted evidence quotes before saving |
| **Opportunities Ledger** | Master list of all opportunities; click any row to open the evidence drawer |
| **Evidence Drawer** | 3 tabs per opportunity: Evidence quotes, Solutions backlog, Experiments |
| **Pre-Meeting Prep** | Select a persona — generate targeted, assumption-testing interview questions |
| **Interview Logs** | Table of all ingested interviews; filter by persona, click to view full transcript |
| **Interview Detail** | Full transcript with highlighted verbatim evidence quotes |
| **LLM Usage** | Token count and cost breakdown per synthesis operation |
| **Account Settings** | Change password (accessible via gear icon in the sidebar) |

---

## Data Model

```
Product (workspace)
├── Interview (transcript + persona + quality score)
├── Opportunity (unmet need, nestable via parent_id)
│   ├── InterviewOpportunityLink (verbatim source quote)
│   ├── OutcomeOpportunityLink
│   └── Solution (competing idea, nestable via parent_id)
│       └── Experiment (Draft → Running → Concluded)
├── Outcome (business goal, e.g. "Reduce churn by 5%")
├── Persona (user archetype, e.g. "Consultant", "Data Analyst")
└── KnowledgeChunk (text chunk + 384-dim pgvector embedding, for future RAG)
```

---

## Project Structure

```
cont-synth/
├── cont_synth/
│   ├── cont_synth.py          # App shell (sidebar + routing)
│   ├── models.py              # SQLModel table definitions (incl. KnowledgeChunk)
│   ├── state/                 # Mixin-based state management
│   │   ├── __init__.py        # Main State class (composition)
│   │   ├── core.py            # Shared data classes + helpers
│   │   ├── navigation.py      # Routing + data loading
│   │   ├── interviews.py      # Interview logic
│   │   ├── ledger.py          # Opportunity/solution management
│   │   └── auth.py            # Password hashing helpers
│   └── pages/                 # One file per route
├── alembic/                   # Database migrations (committed to Git)
│   ├── env.py                 # Reads DATABASE_URL env var for connection
│   └── versions/
├── scripts/
│   └── migrate_sqlite_to_postgres.py  # One-time SQLite → PostgreSQL data migration
├── prompts/                   # LLM prompt templates (plain text)
│   ├── synthesis.txt          # Opportunity extraction prompt
│   ├── dedupe.txt             # Deduplication/merge prompt
│   └── prep.txt               # Interview question generation prompt
├── schema.py                  # Pydantic schemas for LLM responses
├── rxconfig.py                # Reflex configuration (reads DATABASE_URL)
├── requirements.txt           # Python dependencies
├── .env.example               # Template for environment variables
└── .env                       # Secrets (not committed)
```

---

## Testing

The project uses [pytest](https://pytest.org/) for unit testing. Tests run entirely offline — no Gemini API key or running Reflex server is required.

### Install test dependencies

```bash
pip install -r requirements-dev.txt
```

### Run all tests

```bash
pytest
```

### Run with coverage report

```bash
pytest --cov=cont_synth --cov=schema --cov-report=term-missing
```

### Run a specific test file

```bash
pytest tests/test_auth.py
pytest tests/test_highlight.py -v
```

### Test structure

| File | What it tests |
|---|---|
| `tests/test_auth.py` | Password hashing and verification helpers |
| `tests/test_schemas.py` | Pydantic LLM response schemas (`InterviewSnapshot`, `DedupeResult`, etc.) |
| `tests/test_highlight.py` | Transcript highlight injection (`_first_sentence`, `_mark_fragment`, `_inject_mark`) |
| `tests/test_models.py` | All SQLModel database tables (CRUD, relationships) via in-memory SQLite |
| `tests/test_business_logic.py` | Evidence status computation, persona color assignment, opportunity flattening + cycle detection |
| `tests/test_data_classes.py` | All `rx.Base` UI data classes (`LedgerItem`, `SolutionItem`, `ExperimentItem`, etc.) |
| `tests/test_state_computed.py` | Computed property logic (`active_product_name`, `selected_opp_count`, quote navigation, LLM aggregates) |

> **Note:** UI page components (`cont_synth/pages/`) and state methods that call `rx.session()` require the full Reflex runtime and are covered by integration testing rather than unit tests.

---

## Database Migrations

The project uses [Alembic](https://alembic.sqlalchemy.org/) for schema versioning. All migrations live in `alembic/versions/` and are committed to Git.

```bash
# Apply all pending migrations (use alembic directly — bypasses Reflex's pre-check,
# which does not handle the pgvector column type correctly)
alembic upgrade head

# Create a new migration after changing models.py
reflex db makemigrations --message "describe your change"
# Then open the generated file and verify it before applying.
```

> **Why `alembic upgrade head` instead of `reflex db migrate`?**
> Reflex's `db migrate` command runs a pre-flight schema diff using autogenerate before applying migrations. The pgvector `Vector` column type is not recognised by the autogenerate comparison engine, so Reflex always reports "Detected database schema changes" and refuses to proceed. `alembic upgrade head` applies migrations directly without that check.

### Migrating from SQLite to PostgreSQL

If you have an existing SQLite database (`reflex.db`) and want to move its data into PostgreSQL:

```bash
# 1. Apply the schema to the new PostgreSQL database first
alembic upgrade head

# 2. Run the data migration script
python scripts/migrate_sqlite_to_postgres.py

# Optional flags:
#   --sqlite-path /path/to/reflex.db   (default: ./reflex.db)
#   --postgres-url postgresql://...    (default: $DATABASE_URL)
```

The script clears all destination tables, copies every row in FK-dependency order, and resets PostgreSQL sequences so future inserts don't collide with migrated IDs. It is safe to re-run.

---

## Development Notes

- **First run:** Reflex compiles the React frontend on first launch — this can take 1–2 minutes. Subsequent starts are much faster.
- **Hot reload:** Both the Python backend and the React frontend hot-reload automatically during `reflex run`.
- **Database:** PostgreSQL is required. The connection URL is read from `DATABASE_URL` in `.env` (or the environment). The old `reflex.db` SQLite file is no longer used.
- **pgvector:** The `vector` PostgreSQL extension must be installed on the server **and** enabled in the database (`CREATE EXTENSION IF NOT EXISTS vector`). The first Alembic migration handles the `CREATE EXTENSION` call automatically.
- **Build artifacts:** `.web/` and `.states/` are auto-generated by Reflex and gitignored.
- **Gemini costs:** The synthesis pipeline uses `gemini-2.5-pro` for extraction and `gemini-2.5-flash` for deduplication. All API costs are tracked in the LLM Usage page.

---

*Built for Product Managers who want to ship outcomes, not outputs.*
