# PRISMA — Engineering Documentation

## Contents

| Document | What it covers |
|---|---|
| [synthesis-flow.md](synthesis-flow.md) | End-to-end flow when a user clicks "Run Synthesis" — RAG retrieval, all Gemini calls, deduplication, coach feedback, and the DB write on confirm |
| [meeting-prep-flow.md](meeting-prep-flow.md) | How the Pre-Meeting Prep page generates interview guides and battle plans, including its own RAG retrieval path |

## Quick Reference — AI Calls per Operation

| Trigger | Model | Prompt file | Conditional? |
|---|---|---|---|
| Synthesis: RAG summarization | `gemini-2.5-flash` | `rag_summarize.txt` | Only if KB has documents |
| Synthesis: opportunity extraction | `gemini-2.5-pro` | `synthesis.txt` + `rag_context_block.txt` | Always |
| Synthesis: deduplication | `gemini-2.5-flash` | `dedupe.txt` | Only if existing opps exist |
| Synthesis: interview coach | `gemini-2.5-flash` | `coach.txt` | Always (non-fatal) |
| Prep: OST interview guide | `gemini-2.5-flash` | `interview_guide.txt` + `rag_context_block.txt` | When opps are selected |
| Prep: persona battle plan | `gemini-2.5-flash` | `prep.txt` + `rag_context_block.txt` | When no opps selected |

## Tech Stack

- **Framework**: Reflex 0.8 (Python → React)
- **Database**: PostgreSQL + pgvector extension
- **Embeddings**: `all-MiniLM-L6-v2` via `sentence-transformers` (local, 384 dims)
- **LLM**: Google Gemini (`gemini-2.5-pro` for synthesis, `gemini-2.5-flash` for everything else)
- **State**: Mixin-based composition — behavior in mixins, field definitions on the concrete `State` class
