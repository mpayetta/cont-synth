# The Catalyst: Continuous Discovery 🧬

An AI-powered Continuous Discovery dashboard built for Product Managers. Inspired by Teresa Torres' framework, this tool ingests raw user interview transcripts, acts as a ruthless gatekeeper to extract underlying psychological pain points, and mercilessly deduplicates them into a unified, cross-functional Product Roadmap.

## 🚀 Features

* **Dual-Engine Synthesis:** Uses `gemini-2.5-pro` to extract deep, emotional unmet needs from transcripts, strictly rejecting feature requests and solutions.
* **Global Deduplication (The Flash Engine):** Uses `gemini-2.5-flash` to aggressively merge new opportunities into existing ones based on root-cause friction, regardless of the user persona.
* **Decay Tracking:** A color-coded semaphore system (Green/Yellow/Red) that automatically tracks the "freshness" of assumptions, visually decaying over time if an opportunity hasn't been validated recently.
* **Evidence Drawer:** A single-click modal that pulls up the exact, verbatim quotes from users across multiple personas to defend the roadmap against stakeholder pushback.
* **Pre-Meeting Interrogator:** Select a persona before an interview to instantly generate a custom script of aggressive, highly-targeted questions designed to pressure-test your current assumptions.
* **Cascading Data Management:** Safely delete bad transcripts and automatically clean up orphaned opportunities and evidence links in the database.

## 🛠 Tech Stack

* **Frontend & Backend:** [Reflex](https://reflex.dev/) (Pure Python, compiling to React/Next.js)
* **Database:** SQLite (managed via SQLModel & Alembic migrations)
* **AI Engines:** Google Gemini (`gemini-2.5-pro` & `gemini-2.5-flash`)

## ⚙️ Local Setup

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd cont-synth

```

**2. Set up the virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

```

*(Note: Ensure you have `reflex` and `google-generativeai` in your requirements.txt)*

**3. Configure Environment Variables**
Create a `.env` file in the root directory and add your Google Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here

```

**4. Initialize the Database**
Because the `.gitignore` prevents pushing the actual `reflex.db` file, you need to generate a fresh local database using the included Alembic migrations:

```bash
reflex db init
reflex db migrate

```

**5. Run the Application**

```bash
reflex run

```

The application will be available at `http://localhost:3000`.

---

*Built for Product Managers who want to ship outcomes, not outputs.*