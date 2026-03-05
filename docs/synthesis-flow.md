# Synthesis Flow — "Run Synthesis"

**Entry point:** `run_synthesis()` in `cont_synth/state/interviews.py`

When the user clicks "Run Synthesis" on the `/synthesize` page, the following pipeline executes entirely on the backend before the browser transitions to the `/review` page. Nothing is written to the database until the user clicks "Confirm" on the review step.

---

## Step 0 — Validation & DB Snapshot

**File:** `cont_synth/state/interviews.py:235`

- Validates that both `persona_input` and `transcript_text` are non-empty; surfaces an inline error if not.
- Sets `is_processing = True` and `yield`s immediately so the loading spinner appears in the UI before any blocking work begins.
- Queries Postgres for all `Opportunity` rows belonging to the current product workspace, building two dictionaries:
  - `existing_opps_dict` → `{id: statement}` — sent to the deduplication model.
  - `existing_opps_themes` → `{id: theme}` — used to build the `existing_themes_str` passed to the synthesis prompt, so the LLM reuses existing vocabulary instead of coining new theme names.

---

## Step 1 — RAG Context Retrieval *(skipped if KB is empty)*

**File:** `cont_synth/kb_ingest.py:124` — `get_rag_context()`

### 1a. Fast-path check
Queries the `workspacedocument` table. If zero documents exist for this product, returns `""` immediately — no further work done.

### 1b. Transcript summarization — `gemini-2.5-flash`
**Prompt file:** `prompts/rag_summarize.txt`

Sends the first 4,000 characters of the raw transcript to `gemini-2.5-flash` and asks it to produce a 2–3 sentence summary of the core product areas, features, and workflows discussed. This summary becomes the semantic query for the vector search. Sending the full transcript directly as a query vector would dilute the signal with filler words and interview scaffolding; the summary focuses on meaningful product concepts.

### 1c. Local embedding — `all-MiniLM-L6-v2`
The summary text is passed to `SentenceTransformer('all-MiniLM-L6-v2')` running locally in-process (no network call). Produces a 384-dimensional float vector. The model is lazy-loaded on first use and cached in a module-level singleton for subsequent calls.

### 1d. Cosine similarity search — pgvector
Executes raw SQL against Postgres using the `<=>` cosine distance operator from the pgvector extension:

```sql
SELECT chunk_text FROM documentchunk
WHERE document_id = ANY(:doc_ids)
ORDER BY embedding <=> CAST(:qv AS vector)
LIMIT 5
```

Returns the 5 `DocumentChunk` rows whose stored embeddings are closest in semantic space to the query vector. Lower `<=>` value = higher similarity.

### 1e. Context block assembly
The 5 retrieved `chunk_text` values are joined with `\n\n---\n\n` separators and wrapped in the template from `prompts/rag_context_block.txt`, producing:

```
<Workspace_Context>
The following are the most relevant excerpts from this product's documentation...

{chunk 1}

---

{chunk 2}
...
</Workspace_Context>
```

This block is appended to the synthesis system prompt. If any sub-step (1b–1e) throws an exception, the entire RAG block is silently skipped via a `try/except` — synthesis continues without product context.

---

## Step 2 — Opportunity Extraction — `gemini-2.5-pro`

**Prompt file:** `prompts/synthesis.txt` (+ `prompts/rag_context_block.txt` if RAG returned content)

**File:** `cont_synth/state/interviews.py:277`

The primary, most expensive LLM call. The full message sent to the model is:

```
{synthesis_prompt}          ← synthesis.txt filled with existing_themes + optional <Workspace_Context>

Transcript:
{full raw transcript text}
```

The model is constrained to respond in structured JSON matching the `InterviewSnapshot` schema (`schema.py`):

```python
class InterviewSnapshot:
    quality_check:   QualityCheck        # score 1-10, feedback string
    opportunities:   list[OpportunityExtraction]  # theme, statement, source_quote
    memorable_quote: str
    metadata:        InterviewMetadata   # duration, date, participant names + roles
```

Token usage is immediately recorded in a `PendingLlmUsage` object, held in memory until `confirm_synthesis()` has an `interview_id` to attach the log to.

---

## Step 3 — Deduplication — `gemini-2.5-flash` *(skipped if no existing opps)*

**Prompt file:** `prompts/dedupe.txt`

**File:** `cont_synth/state/interviews.py:311`

If the workspace has existing opportunities, a second LLM call resolves whether each newly extracted opportunity is truly new or is the same root cause as an existing one.

Input sent to the model:
- `existing_opps_dict` — the full `{id: statement}` map of every existing opportunity.
- `new_opps_list` — only the statement strings extracted in Step 2.

Returns `DedupeResult` — for each new opportunity: either a `matched_existing_id` (merge) or `null` (create new). The prompt instructs the model to match by **root cause**, not wording similarity, and to prefer merging when in doubt.

When a match is found, the new opportunity **inherits the theme of the existing one**, keeping the workspace taxonomy stable rather than introducing synonymous themes.

---

## Step 4 — Interview Coach Feedback — `gemini-2.5-flash` *(non-fatal)*

**Prompt file:** `prompts/coach.txt`

**File:** `cont_synth/state/interviews.py:385`

A third Flash call that evaluates the interviewer's technique using the Mom Test methodology. The entire block is wrapped in `try/except` — a failure here does not abort synthesis.

Input:
- `history_context` — JSON of the last 3 `InterviewFeedback` records (date, score, keep/stop lists), fetched via `_get_coach_history_context()` to enable trend-aware feedback.
- `transcript` — the full raw transcript.

Returns a score (1–10) plus `keep_doing`, `stop_doing`, `start_doing` lists and a `trend_analysis` string. All stored in `pending_coach_*` state fields.

---

## Step 5 — State Assembly *(no DB writes)*

**File:** `cont_synth/state/interviews.py:369`

All results are packed into `pending_*` Reflex state fields:

| Field | Content |
|---|---|
| `pending_synthesis_opps` | `list[PendingOppItem]` — all pre-selected `True`; shows matched existing statement when deduped |
| `pending_synthesis_quality` | Quality score from Step 2 |
| `pending_synthesis_memorable_quote` | Best quote for the interview card |
| `pending_synthesis_feedback` | Quality feedback text |
| `pending_synthesis_participants` | LLM-extracted participant names |
| `pending_synthesis_participant_roles` | Parallel roles list (`"interviewee"` or `"interviewer"`) |
| `pending_synthesis_duration` | Extracted interview duration in minutes |
| `pending_synthesis_interview_date` | ISO date string if detectable |
| `pending_coach_score/keep/stop/start/trend` | Coach feedback |
| `pending_llm_usages` | Token logs held until `interview_id` exists |

The first opportunity's `source_quote` is set as `highlighted_quote_text` so the transcript panel immediately scrolls to and highlights it on load.

**Nothing has been written to the database yet.**

---

## Step 6 — Navigate to `/review`

`yield rx.redirect("/review")` sends the browser to the synthesis review page. The user can:
- Toggle/deselect individual opportunities.
- Inspect highlighted source quotes in the transcript panel.
- Edit participant roles (interviewee vs. interviewer).
- Review quality score and coach feedback.

---

## Step 7 — `confirm_synthesis()` — DB Writes

**File:** `cont_synth/state/interviews.py` — called on user click

Writes to the database in strict FK-safe order:

1. **`Persona`** — upserted by name (unique constraint).
2. **`Interview`** — created, yielding the `interview_id` needed for all FK children.
3. **`LlmUsageLog`** — all `pending_llm_usages` written now that `interview_id` exists (synthesis + dedupe + coach calls).
4. **`Participant` + `InterviewParticipantLink`** — auto-created from LLM-extracted names. `is_team_member = True` for `"interviewer"` role; only interviewees get an `InterviewParticipantLink` bridge row.
5. **`Opportunity`** — for each selected `PendingOppItem`: create new or find the matched existing one and update `date_last_validated`. Skips if already linked to this interview.
6. **`InterviewOpportunityLink`** — bridge row with `source_quote` for each opportunity.
7. **`InterviewFeedback`** — written if `pending_coach_score > 0`.

Pending state is then cleared, the ledger and history are reloaded, and the browser is redirected to `/interviews`.

---

## Gemini Call Summary

| # | Model | Prompt | Always? | Purpose |
|---|---|---|---|---|
| 1 | `gemini-2.5-flash` | `rag_summarize.txt` | Only if KB has docs | Compress transcript to a focused query for vector search |
| 2 | `gemini-2.5-pro` | `synthesis.txt` + optional `rag_context_block.txt` | Always | Extract opportunities, quality score, metadata |
| 3 | `gemini-2.5-flash` | `dedupe.txt` | Only if existing opps | Resolve new vs. existing opportunities by root cause |
| 4 | `gemini-2.5-flash` | `coach.txt` | Always (non-fatal) | Score interviewer technique; produce keep/stop/start lists |

Minimum calls (empty workspace, no KB): **2** (extraction + coach).
Maximum calls (mature workspace + KB documents): **4**.
