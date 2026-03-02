# Opportunities — Full Lifecycle Guide

> This guide covers every stage of an Opportunity's life inside Catalyst: how it is discovered, structured, evidenced, explored with solutions, validated with experiments, and ultimately prioritized so your team focuses on the work that matters most.

---

## Table of Contents

1. [What is an Opportunity?](#1-what-is-an-opportunity)
2. [The Opportunity Tree](#2-the-opportunity-tree)
3. [Creating Opportunities](#3-creating-opportunities)
   - [AI Synthesis (recommended)](#31-ai-synthesis-recommended)
   - [Manual Creation](#32-manual-creation)
4. [Evidence — Grounding in Customer Reality](#4-evidence--grounding-in-customer-reality)
   - [Staleness Indicator](#41-staleness-indicator)
5. [Solutions — Brainstorming the "How"](#5-solutions--brainstorming-the-how)
   - [Solution Statuses](#51-solution-statuses)
6. [Experiments — Validating Assumptions](#6-experiments--validating-assumptions)
   - [Experiment Lifecycle](#61-experiment-lifecycle)
   - [Signal and Resolution](#62-signal-and-resolution)
7. [Prioritization — Deciding What to Work On](#7-prioritization--deciding-what-to-work-on)
   - [The Three Torres Criteria](#71-the-three-torres-criteria)
   - [Priority Score](#72-priority-score)
   - [Target Opportunity](#73-target-opportunity)
8. [Business Outcomes — Anchoring to Strategy](#8-business-outcomes--anchoring-to-strategy)
9. [Navigating the Opportunities List](#9-navigating-the-opportunities-list)
10. [Data Model Reference](#10-data-model-reference)

---

## 1. What is an Opportunity?

An **Opportunity** is an unmet customer need — not a feature request, not a solution, not a business goal.

It is written in the customer's voice using the standard frame:

> *"When [context], I need a way to [goal], because [underlying reason]."*

Examples of good Opportunities:
- *"I need a way to selectively collapse parts of an org chart to create a clean, readable visual for my presentation — because a rigid level-based export doesn't work for messy real-world structures."*
- *"I waste time on the manual multi-step process of creating pivot tables and then building summary charts in PowerPoint."*

Examples of things that are **NOT** Opportunities:
- *"Add a dark mode"* — this is a solution
- *"Increase Q3 retention by 5%"* — this is a business Outcome
- *"Users are frustrated with exports"* — too vague, not anchored to a specific unmet need

Teresa Torres' core principle: **fall in love with the problem, not the solution**. Opportunities are your problems.

---

## 2. The Opportunity Tree

Opportunities are organized into a hierarchy. A top-level opportunity can have child opportunities nested beneath it, allowing you to break a large, vague need into smaller, more specific ones.

```
[Outcome] Reduce chart creation time by 40%
│
├── Opportunity: I need a way to selectively collapse/expand org chart nodes
│   │
│   └── Opportunity: I need to apply collapse settings per export, not globally
│
└── Opportunity: I waste time building summary charts manually in PowerPoint
    │
    └── Opportunity: I can't reuse chart formatting across different data sources
```

This structure is sometimes called the **Opportunity Solution Tree** (OST) from Teresa Torres.

**Rules of the tree:**
- Any opportunity can be a parent of other opportunities.
- Opportunities inherit the **Business Outcome** link of their parent automatically on creation.
- The nesting depth is unlimited, but 2–3 levels is usually enough.

---

## 3. Creating Opportunities

### 3.1 AI Synthesis (recommended)

1. Navigate to **Synthesize** in the sidebar.
2. Paste a raw interview transcript (or upload a file).
3. Catalyst sends the transcript to **Gemini 2.5 Pro**, which extracts unmet needs as Opportunities, complete with verbatim source quotes.
4. The **Synthesis Review** page shows each extracted opportunity alongside its evidence quote and a highlighted transcript view.
5. For each opportunity, the AI also checks whether it matches an **existing** opportunity in your ledger (deduplication via Gemini 2.5 Flash). If a match is found, the quote is added to that existing opportunity rather than creating a duplicate.
6. You confirm or reject each item before anything is written to the database.

The prompts driving this are in [`prompts/synthesis.txt`](../prompts/synthesis.txt) and [`prompts/dedupe.txt`](../prompts/dedupe.txt).

### 3.2 Manual Creation

1. Open the **Opportunities** page.
2. Click **+ New Opportunity**.
3. Fill in:
   - **Theme / Category** — a short label (e.g., "Data Usability", "Visual Customization")
   - **Opportunity Statement** — write the unmet need in customer voice
   - **Parent Opportunity** *(optional)* — select from existing opportunities to nest this one
4. Click **Save Opportunity**.

To edit an existing opportunity, open its detail page (click the statement text) and click **Edit** in the top-right.

---

## 4. Evidence — Grounding in Customer Reality

Every opportunity should be grounded in at least one real verbatim quote from a customer interview. Evidence is what separates a validated opportunity from an assumption.

Each piece of evidence is a **link between an Opportunity and an Interview**, storing the exact verbatim quote the customer said.

**Adding evidence:**
- Automatically added during AI Synthesis (the source quote is captured for each extracted opportunity).
- Manually via the **"Map Missed Evidence"** section in the opportunity's Evidence tab: select the source interview, drag to select the verbatim text in the transcript, and click **Map as Evidence**.

**Viewing evidence:**
- Each evidence quote shows the persona badge and the verbatim text.
- Clicking a quote opens the full interview transcript in a side drawer, with the quote highlighted in yellow.

### 4.1 Staleness Indicator

Evidence decays over time. Customer needs evolve, and old evidence becomes less reliable.

Catalyst tracks `date_last_validated` per opportunity and shows a **freshness status** via a colored left border on each card:

| Border Color | Status | Age |
|---|---|---|
| Green | Fresh | 0–21 days |
| Amber | Decaying | 22–45 days |
| Red | Stale | 45+ days |

The number shown (e.g., `"14d"`) is the days since last validation. This creates urgency to keep re-validating important opportunities in ongoing customer conversations.

---

## 5. Solutions — Brainstorming the "How"

Once an Opportunity is well-evidenced, you can start brainstorming **Solutions** — competing ideas for how to address the unmet need.

Solutions are kept separate from Opportunities intentionally. The goal is to explore the problem space thoroughly before committing to any implementation direction.

**Adding a solution:**
1. Open an opportunity's detail page (click its statement in the list).
2. In the **Solutions & Experiments** column, type a solution name and description in the form at the bottom.
3. Click **Save Solution**.

Solutions can also be nested (sub-solutions), allowing you to represent variations of an approach. Use the branch icon (⎇) on a solution card to add a child solution beneath it.

### 5.1 Solution Statuses

| Status | Meaning |
|---|---|
| **Ideation** | Being considered; not yet being tested |
| **Testing** | An experiment is actively running against this solution |
| **Shipped** | Validated and built into the product |
| **Discarded** | Tested or reasoned out; not the right approach |

Status is updated automatically when you create an Experiment (bumps to *Testing*) and when you resolve an experiment's signal (bumps to *Shipped* or *Discarded*).

---

## 6. Experiments — Validating Assumptions

Before building a solution, you should test the key assumptions behind it. Experiments are lightweight tests designed to generate a signal quickly, without full implementation.

**Common experiment methods in Catalyst:**

| Method | Description |
|---|---|
| **Prototype Interview** | Show a low-fidelity mockup to customers and observe reactions |
| **Fake Door** | Add a button/link for the feature; measure click-through before building |
| **A/B Test** | Compare two variants with real users to measure behavior difference |
| **Usability Test** | Observe users attempting to complete a task with an existing or prototype UI |
| **Survey** | Ask targeted questions to a broad audience to quantify a hypothesis |

**Adding an experiment:**
1. From the detail page, click the flask icon (🧪) on a solution card, or click **Design Experiment** below the solution.
2. Fill in:
   - **Name** — a descriptive title (e.g., "Fake Door for Premium Export")
   - **Assumption** — the specific hypothesis being tested (e.g., "Users are willing to pay $10/month for faster exports")
   - **Method** — select the experiment type
3. Click **Save Experiment**.

Creating an experiment automatically moves the linked Solution to **Testing** status.

### 6.1 Experiment Lifecycle

```
Draft ──▶ Running ──▶ Concluded
  │
  └── (Edit or delete while in Draft)
```

- **Draft**: Designed but not yet started. Edit freely.
- **Running**: Actively collecting data. Click **▶ Start Running** to begin.
- **Concluded**: Data collected. Click **✓ Conclude** to end. You can then set the Signal and write Evidence / Learnings notes.

### 6.2 Signal and Resolution

Once Concluded, mark the experiment with a **Signal**:

| Signal | Meaning |
|---|---|
| **Validated** | The assumption held. Evidence supports building this solution. |
| **Invalidated** | The assumption failed. This direction should be reconsidered. |

After setting a signal, a **resolution button** appears:
- **→ Ship solution** (Validated): moves the linked Solution to **Shipped**.
- **→ Discard solution** (Invalidated): moves the linked Solution to **Discarded**.

The **Evidence / Learnings** textarea (visible once Concluded) is where you capture what you observed — what customers said, key metrics, behavioral patterns. These notes persist permanently as institutional memory.

---

## 7. Prioritization — Deciding What to Work On

The hardest question in Continuous Discovery is: *which opportunity should we focus on next?*

Catalyst uses the framework from **Teresa Torres' Continuous Discovery Habits** to score each opportunity across three independent criteria, then surfaces a composite **Priority Score** on each card in the list.

### 7.1 The Three Torres Criteria

#### Frequency
> *How often does this opportunity come up in customer interviews?*

In Catalyst, **Frequency is auto-derived** from the evidence count — the number of distinct interview quotes linked to the opportunity. It is normalized to a 0–5 scale (`min(evidence_count, 5)`). You do not set this manually; it grows as you add evidence through synthesis and manual mapping.

A high frequency means many different customers in many different interviews have expressed this need. That's a strong signal it's real and widespread.

#### Impact
> *If we solved this, how much would it matter to customers?*

**Impact is set manually** using the 5-dot rater on each opportunity card. Rate 1–5:

| Score | Meaning |
|---|---|
| 1 | Marginal — nice to have, low value |
| 2 | Minor — would help some customers in some cases |
| 3 | Moderate — meaningful improvement to a common workflow |
| 4 | Significant — addresses a major pain point |
| 5 | Critical — blocking or severely degrading customer success |

Consider both **depth** (how much does it hurt when it happens?) and **breadth** (how many customers are affected?).

#### Satisfaction Gap
> *How poorly is this need served today — by your product or any alternative?*

**Satisfaction Gap is set manually** using the 5-dot rater. Rate 1–5:

| Score | Meaning |
|---|---|
| 1 | Already well solved — customers have good workarounds |
| 2 | Partially solved — awkward but manageable |
| 3 | Poorly served — common workarounds are painful |
| 4 | Very poorly served — customers consistently fail or give up |
| 5 | Not served at all — no reasonable path forward exists today |

A high satisfaction gap means there is a real market gap you could uniquely fill. A low gap (even with high frequency and impact) means competitors or workarounds already address the need well — fixing it would give you less differentiation.

### 7.2 Priority Score

```
Priority Score = Impact + Satisfaction Gap + Frequency
                 (0–5)   (0–5)              (0–5)

Maximum = 15
```

This score appears as **P: N** in the top-right corner of each opportunity card. It is color-coded for at-a-glance scanning:

| Score Range | Badge Color | Interpretation |
|---|---|---|
| 0 | Gray (outline) | Not yet rated |
| 1–5 | Blue | Low priority |
| 6–10 | Amber | Medium priority |
| 11–15 | Green | High priority — strong candidate for target |

**Important:** unrated scores (0) do not contribute to the total, so an opportunity with no Impact or Sat. Gap scores set will only have Frequency contributing to its P score. Rate your opportunities as you go — even rough estimates are better than none.

### 7.3 Target Opportunity

Teresa Torres recommends that a team focuses on **exactly one opportunity at a time**. Spreading attention across five simultaneously is a recipe for shallow exploration and unfocused experiments.

Click the **crosshair button** (⊕) on any opportunity card to designate it as the **Target Opportunity**. This:

- Clears the target designation from any other opportunity
- Gives the card a green left border and subtle green background
- Shows a green **"Target"** badge in the card's tag row

Clicking the button again on the same opportunity removes its target designation.

The Target Opportunity should be the one your team is most actively exploring this sprint or discovery cycle — running experiments against it, synthesizing more evidence, and brainstorming new solutions.

---

## 8. Business Outcomes — Anchoring to Strategy

Each Opportunity can be linked to a **Business Outcome** — the measurable company goal it is meant to drive (e.g., "Reduce churn by 5%", "Increase Q3 Activation").

**Why this matters:** Continuous Discovery exists to move business needles, not just to understand customers. Linking opportunities to outcomes keeps your discovery work grounded in strategic intent and makes it easy to filter the Opportunities List to only the opportunities relevant to the current business priority.

**Assigning an outcome:**
- Open an opportunity's detail page.
- Use the **"Link to Outcome"** selector in the header to assign one primary outcome.

**Creating outcomes:**
- In the Opportunities List header, click **+ New Outcome**.
- Enter the outcome name (e.g., "Increase Q3 Retention").

**Filtering by outcome:**
- Use the **outcome dropdown** in the top-right of the Opportunities List to filter to only the opportunities relevant to a particular business goal.
- Select **"Unmapped Opportunities"** to find opportunities that haven't been connected to any outcome yet.

Child opportunities inherit their parent's outcome link automatically when created.

---

## 9. Navigating the Opportunities List

The **Opportunities List** (`/ledger`) is the main working surface. Each card shows:

```
┌────────────────────────────────────────────────────────┐
│ [Target] [Theme] [Cross-Persona]    [🧪 2 running] P:9 │  ← Tags + status
│                                                        │
│  Opportunity statement text — bold, easy to read       │  ← Hero text (click → detail)
│                                                        │
│  [Persona A] [Persona B]   ■ 3 quotes · ◆ 1 solution  │  ← Evidence & solutions count
│                                                        │
│  Impact ●●●○○  Sat.Gap ●●○○○  Frequency 3/5 mentions  │  ← Torres scoring
└────────────────────────────────────────────────────────┘
```

**Interacting with a card:**
- **Click the statement text** — opens the full detail page (Evidence column + Solutions & Experiments column).
- **Click dots (●)** — rates Impact or Satisfaction Gap inline; saves instantly.
- **Click the crosshair (⊕)** — toggles Target Opportunity designation.
- **Child opportunities** are indented beneath their parent.

**The detail page** gives you a 2-column layout:
- **Left column (Evidence):** verbatim quotes linked to this opportunity + the "Map Missed Evidence" form.
- **Right column (Solutions & Experiments):** solution cards (each with inline experiments), the brainstorm form, and experiment design forms.

---

## 10. Data Model Reference

```sql
Opportunity
├── id                   INTEGER PRIMARY KEY
├── product_id           INTEGER FK → Product
├── theme                TEXT            -- e.g. "Data Usability"
├── statement            TEXT            -- the customer need
├── parent_id            INTEGER FK → Opportunity  -- for nesting
├── date_last_validated  DATETIME        -- drives staleness
├── created_at           DATETIME
├── impact_score         INTEGER (0–5)   -- Torres: how much would solving it matter?
├── sat_gap_score        INTEGER (0–5)   -- Torres: how poorly is it served today?
└── is_target            BOOLEAN         -- team's current focus opportunity

InterviewOpportunityLink
├── interview_id         INTEGER FK → Interview  (PK)
├── opportunity_id       INTEGER FK → Opportunity  (PK)
└── source_quote         TEXT            -- verbatim evidence

Solution
├── id                   INTEGER PRIMARY KEY
├── opportunity_id       INTEGER FK → Opportunity
├── parent_id            INTEGER FK → Solution  -- for sub-solutions
├── name                 TEXT
├── description          TEXT
└── status               TEXT  -- Ideation | Testing | Shipped | Discarded

Experiment
├── id                   INTEGER PRIMARY KEY
├── solution_id          INTEGER FK → Solution
├── name                 TEXT
├── assumption           TEXT            -- the hypothesis being tested
├── method               TEXT  -- Prototype Interview | Fake Door | A/B Test | ...
├── status               TEXT  -- Draft | Running | Concluded
├── signal               TEXT  -- Pending | Validated | Invalidated
├── evidence_notes       TEXT            -- learnings recorded after concluding
└── created_at           DATETIME

OutcomeOpportunityLink
├── outcome_id           INTEGER FK → Outcome  (PK)
└── opportunity_id       INTEGER FK → Opportunity  (PK)
```

**Computed fields (not stored in DB):**

| Field | Computation |
|---|---|
| `priority_score` | `impact_score + sat_gap_score + min(evidence_count, 5)` |
| `running_experiments` | Count of linked experiments with `status = "Running"` |
| `days_old` | `(today - date_last_validated).days` |
| `status` / `status_color` | Based on `days_old`: 0–21 = Fresh/green, 22–45 = Decaying/amber, 45+ = Stale/red |
| `is_cross_functional` | `True` if linked to quotes from more than one persona |

---

*For the AI synthesis pipeline details, see [`prompts/synthesis.txt`](../prompts/synthesis.txt) and [`prompts/dedupe.txt`](../prompts/dedupe.txt). For the full application setup, see the [README](../README.md).*
