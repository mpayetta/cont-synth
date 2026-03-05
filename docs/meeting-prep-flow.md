# Meeting Prep Flow — "Generate Guide"

**Entry point:** `generate_hostile_questions()` in `cont_synth/state/interviews.py:902`

The Pre-Meeting Prep page (`/prep`) generates interview guides before a session. It has two distinct modes depending on whether the user has selected specific opportunities, and both modes run the same RAG retrieval step before hitting the LLM.

---

## Page Setup — What loads on `/prep`

`load_prep_page()` on the State triggers three loaders:

1. **`load_ledger()`** — populates `available_personas` for the persona selector dropdown.
2. **`load_prep_data()`** — queries all `Opportunity` rows for the product, annotates each with the persona names that surfaced it (via `InterviewOpportunityLink → Interview → Persona`), and loads all `Running` experiments. These feed the OST selector checkboxes.
3. **`load_coach_feedback_for_prep()`** — fetches the single most recent `InterviewFeedback` record. If found, populates `last_interview_score` and `last_stop_doing` for the optional coaching guardrails.

---

## User Inputs

| Input | State field | Used in |
|---|---|---|
| Target persona (autocomplete) | `target_persona` | Both modes |
| Selected opportunities (checkboxes) | `prep_opportunities[].selected` | Determines which mode runs |
| Selected running experiments | `prep_running_experiments[].selected` | OST guide only |
| Extra context (free text) | `prep_extra_context` | Both modes |
| Apply coach feedback toggle | `apply_coach_feedback` | Battle plan only |

The mode is determined purely by whether any opportunity is checked: **≥1 opp selected → OST interview guide; 0 opps → persona battle plan**.

---

## Step 1 — RAG Context Retrieval *(both modes; skipped if KB is empty)*

**File:** `cont_synth/kb_ingest.py:184` — `get_prep_rag_context()`

Unlike the synthesis RAG path, the prep page has **no transcript** to summarize. Instead, the query vector is built directly from the user's current selections.

### 1a. Query construction

```python
rag_query = " ".join(filter(None, [self.target_persona] + [o.statement for o in selected_opps]))
```

This concatenates the target persona name with all selected opportunity statements into a single query string. Examples:
- `"Enterprise CFO"` (no opps selected — battle plan mode)
- `"Enterprise CFO Users struggle to reconcile multi-currency invoices Approval workflow lacks audit trail"` (opps selected)

### 1b. Direct local embedding — `all-MiniLM-L6-v2`
**No Gemini call here.** The query string is passed directly through the locally-running `SentenceTransformer` model — no summarization step is needed because the query is already compact and domain-specific. Produces a 384-dimensional float vector.

### 1c. pgvector cosine similarity search
Identical SQL to the synthesis path:

```sql
SELECT chunk_text FROM documentchunk
WHERE document_id = ANY(:doc_ids)
ORDER BY embedding <=> CAST(:qv AS vector)
LIMIT 5
```

Returns the top 5 most semantically relevant chunks from the product documentation KB.

### 1d. Context block assembly
**Prompt file:** `prompts/rag_context_block.txt`

Retrieved chunks are wrapped in the same `<Workspace_Context>` block used during synthesis and stored in `workspace_context_block`. This variable is injected into whichever prompt template runs next (see both modes below).

Any exception in steps 1b–1d is silently swallowed — the guide generation continues without product context.

---

## Mode A — OST Interview Guide *(≥1 opportunity selected)*

**Prompt file:** `prompts/interview_guide.txt`

**Model:** `gemini-2.5-flash`

**File:** `cont_synth/state/interviews.py:929`

Triggered when the user has explicitly checked one or more opportunities. This mode generates a structured, OST-aligned interview guide focused on probing the selected opportunities and validating the assumptions behind any selected running experiments.

### Variables injected into the prompt

| Template variable | Source |
|---|---|
| `{workspace_context}` | The `<Workspace_Context>` block from Step 1 (empty string if KB has no docs) |
| `{persona_context}` | Sentence describing the target persona, or a fallback if none selected |
| `{opportunities_section}` | Bulleted list: `- [Theme] Opportunity statement` for each selected opp |
| `{assumptions_section}` | Bulleted list of selected running experiments: solution name, experiment name, assumption text |
| `{extra_context}` | Free-text additional context from the user, prefixed with `"ADDITIONAL CONTEXT FROM THE INTERVIEWER:"` |

### Output & persistence

The generated markdown is:
- Displayed immediately in the `prep_questions` textarea.
- Written to `PrepGuideLog` with `guide_type = "interview_guide"`, the full input snapshot, and token counts.
- Written to `LlmUsageLog` with `operation = "prep"`.

---

## Mode B — Persona Battle Plan *(0 opportunities selected)*

**Prompt file:** `prompts/prep.txt`

**Model:** `gemini-2.5-flash`

**File:** `cont_synth/state/interviews.py:992`

Triggered when no opportunities are checked. This mode generates a broader "battle plan" for interviewing a persona, drawing on all previously discovered opportunities for that persona and optionally applying coaching guardrails.

### Persona opportunity lookup

Scans `self.ledger_data` (already loaded) to find every opportunity where `target_persona` appears in `personas_affected`. These become the focus areas for the interview. If no prior opportunities exist AND no extra context was provided, the function exits early with an informational message.

### Coaching guardrails

If `apply_coach_feedback = True` and `last_stop_doing` is non-empty (loaded at page mount):

```
### 🛑 Coach's Guardrails:

Based on your last interview (score: {score}/10), you must actively avoid
these habits during this conversation:
- {stop_doing_item_1}
- {stop_doing_item_2}
...
```

If no coaching data is available, a generic Mom Test reminder is injected instead.

### Variables injected into the prompt

| Template variable | Source |
|---|---|
| `{workspace_context}` | The `<Workspace_Context>` block from Step 1 |
| `{target_persona}` | `self.target_persona` |
| `{target_opps}` | Python list of opportunity statements for this persona |
| `{coaching_guardrails}` | Coach feedback block or generic fallback |
| `{extra_direction}` | Free-text from `prep_extra_context`, or empty string |

### Output & persistence

The generated markdown is:
- Displayed in `prep_questions`.
- Written to `PrepGuideLog` with `guide_type = "battle_plan"`, coaching metadata, and the full input snapshot.
- Written to `LlmUsageLog` with `operation = "prep"`.
- **Also upserted into `PersonaPrep`** (keyed on persona name) — this is the "saved script" that the prep page pre-fills the next time the same persona is selected.

---

## Gemini Call Summary

| Mode | # of Gemini calls | Model | Prompt |
|---|---|---|---|
| Either (KB has docs) | 1 (RAG summarization) | *none* — embedding is local | — |
| OST guide | 1 | `gemini-2.5-flash` | `interview_guide.txt` |
| Battle plan | 1 | `gemini-2.5-flash` | `prep.txt` |

The prep page always makes **exactly 1 Gemini call** for the actual guide generation. The RAG retrieval step on the prep page makes **0 Gemini calls** — the query is embedded locally without a summarization round-trip, which is faster and sufficient because the query is already compact.

Compare to synthesis, where RAG uses a Flash call to first compress the long transcript before embedding it.

---

## Key Difference: Prep RAG vs. Synthesis RAG

| | Synthesis | Prep |
|---|---|---|
| RAG function | `get_rag_context()` | `get_prep_rag_context()` |
| Query source | LLM-generated summary of the transcript | Concatenated persona name + selected opportunity statements |
| Gemini call before embedding? | Yes — `gemini-2.5-flash` summarizes the transcript | No — query is embedded directly |
| Why? | Transcript is long and noisy; summary distills signal | Prep query is already short and domain-specific |
