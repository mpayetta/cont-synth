# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app in dev mode
reflex run

# Run tests
pytest

# Run a single test file
pytest tests/test_synthesis.py

# Run a single test
pytest tests/test_synthesis.py::test_function_name -v

# Run tests with coverage
pytest --cov=cont_synth

# Database migrations (use reflex db, NOT alembic CLI)
reflex db migrate
reflex db makemigrations --message "description"
```

## Architecture

**cont-synth** (PRISMA) is a product research synthesis tool built with:
- **Reflex** (Python → React) — all UI and state are Python; Reflex compiles to React
- **SQLite** (dev) / **PostgreSQL** (prod) via **SQLModel + Alembic**
- **Google Gemini** (2.5-pro for synthesis, 2.5-flash for dedup/coach)

### State Architecture

State is composed via Python mixins in `cont_synth/state/`:

```
State (cont_synth/state/__init__.py)
  ├── NavigationStateMixin  (navigation.py)  — routing, product switching, workspace members
  ├── InterviewSynthesisStateMixin  (synthesis.py)  — LLM synthesis pipeline
  ├── InterviewPrepStateMixin  (interviews.py)  — prep guides, interview CRUD
  ├── LedgerStateMixin  (ledger.py)  — opportunity/solution/experiment CRUD
  ├── ParticipantStateMixin  (participants.py)  — participant CRM
  └── KnowledgeBaseStateMixin  (knowledge_base.py)  — RAG document store
```

UI data classes (Pydantic `BaseModel`) live in `cont_synth/state/core.py`. These are separate from DB models because Reflex state vars cannot use SQLModel directly.

**Critical Reflex constraint**: Mixin methods used as `on_click` event handlers fail at compile time. Always define UI-facing event handlers directly on the `State` class, not on mixins.

### Page & Auth Flow

Every page uses `_page_layout(content, State.load_X_page)` in `cont_synth/cont_synth.py`. On mount:
1. `_ensure_auth_and_load()` checks localStorage for a session token
2. If authenticated → calls `load_data_for_current_view()`
3. If not → calls `verify_stored_session` callback → redirects to `/login` on failure

Routes are registered at the bottom of `cont_synth/cont_synth.py` via `app.add_page()`.

### Data Model

```
Product (workspace)
  └── ProductMember (user roles: admin|member|viewer)
      Outcome
        └── Opportunity (nested via parent_id, parent=Opportunity)
              └── Solution (nested via parent_id, parent=Solution)
                    └── Experiment
      Interview
        ├── InterviewOpportunityLink
        ├── InterviewParticipantLink
        └── InterviewFeedback (coach score)
      Participant ── Persona
      PrepGuideLog
      WorkspaceDocument (RAG chunks via pgvector)
```

### LLM Pipeline (`cont_synth/state/synthesis.py`)

`run_synthesis()` is an async background task that:
1. Calls `gemini-2.5-pro` with the synthesis prompt → `InterviewSnapshot` (structured output via Pydantic)
2. Calls `gemini-2.5-flash` for deduplication against existing opportunities → `DedupeResult`
3. Calls `gemini-2.5-flash` for interview coach feedback → `CoachFeedback`
4. Populates `pending_synthesis_*` state vars and navigates to `/review`

`confirm_synthesis()` does the actual DB write after user reviews results.

LLM Pydantic schemas are in `schema.py`. Prompt templates are in `prompts/*.txt`.

### Migrations

Alembic migrations live in `alembic/versions/`. The chain is long — always use `reflex db migrate` (not `alembic upgrade head` directly) because Reflex manages the DB URL.

### Tests

Tests use an in-memory SQLite fixture (`db_session` in `tests/conftest.py`). The conftest mocks `google.generativeai`, `PyPDF2`, `docx`, and `pgvector` before any project code is imported, so tests run without real API keys or optional dependencies.

When adding a new model, register it in the `conftest.py` import block so `SQLModel.metadata.create_all()` picks it up.

### Role System

There are two independent layers of roles:

**Layer 1 — Application-level** (`User.role` column):
- `admin` — full app access: can create new Product workspaces, view the LLM Usage dashboard, and create new user accounts
- `user` — can only access workspaces they have been explicitly invited to; allowed actions within those workspaces are governed by their workspace-level role

**Layer 2 — Workspace-level** (`ProductMember.role` column, scoped to the active product):
- `admin` — full workspace access: invite/remove members, change member roles, rename workspace, wipe workspace data, delete workspace
- `member` — all data operations (create/edit interviews, opportunities, solutions, experiments) **except** adding users or accessing the Danger Zone
- `viewer` — read-only; Synthesize and Pre-Meeting Prep nav items are hidden; no write actions permitted

**Key computed vars** (always use these in UI guards, never raw role strings):
- `State.is_admin` → `auth_user_role == "admin"` (app-level)
- `State.is_workspace_admin` → `workspace_role == "admin" OR auth_user_role == "admin"` (app admins are implicitly workspace admins everywhere)
- `State.is_viewer` → `workspace_role == "viewer"`

`workspace_role` is loaded per product switch in `load_products()` on `NavigationStateMixin`. Workspace owners (the user who created the Product) are always treated as workspace admins.

## Audit Log
Make sure all CRUD operations on the main entities (opportunity, solution, experiment, interview, user, product, participant, outcome, persona and workspacedocument) are tracked in the AuditLog table always. 