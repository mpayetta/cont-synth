import reflex as rx
import google.generativeai as genai
import os
import json
import io
import PyPDF2
import docx
from datetime import datetime, timezone
from sqlmodel import select, Field

from .models import Persona, Interview, Opportunity, InterviewOpportunityLink, Solution, Outcome, OutcomeOpportunityLink
from schema import InterviewSnapshot, DedupeResult
from dotenv import load_dotenv

# --- INITIALIZATION ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

pro_model = genai.GenerativeModel('gemini-2.5-pro')
flash_model = genai.GenerativeModel('gemini-2.5-flash')

def load_prompt(filename: str) -> str:
    """Reads prompt templates from the prompts directory."""
    filepath = os.path.join(os.getcwd(), "prompts", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# --- UI DATA MODELS ---
class PersonaBadge(rx.Base):
    name: str
    color: str

class QuoteItem(rx.Base): 
    interview_id: int
    persona_name: str
    persona_color: str
    text: str

class SolutionItem(rx.Base):
    id: int
    parent_id: int | None = None
    name: str
    description: str
    status: str
    indent_level: int = 0 # Tells the UI how far right to shift this card

class OutcomeItem(rx.Base):
    id: int
    name: str

class InterviewHistoryItem(rx.Base):
    interview_id: int
    persona: str
    date_logged: str
    snippet: str

class LedgerItem(rx.Base):
    opportunity_id: int 
    theme: str
    personas_affected: list[PersonaBadge]
    opportunity: str
    status: str
    status_color: str
    days_old: int
    is_cross_functional: bool
    evidence: list[QuoteItem]
    solutions: list[SolutionItem] = []
    linked_outcomes: list[OutcomeItem] = []

class PersonaPrep(rx.Model, table=True):
    """Stores the latest generated prep script for a specific persona."""
    persona: str = Field(primary_key=True) # The persona name acts as the ID
    content: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    
# --- THE STATE (BACKEND LOGIC) ---
class State(rx.State):
    is_processing: bool = False
    is_prepping: bool = False
    is_drawer_open: bool = False
    ledger_data: list[LedgerItem] = []
    available_personas: list[str] = []
    target_persona: str = ""
    prep_questions: str = ""
    prep_last_updated: str = ""
    persona_input: str = ""
    transcript_text: str = ""
    current_view: str = "synthesize"
    is_generating_solutions: bool = False
    new_solution_name: str = "" 
    new_solution_desc: str = "" 
    target_parent_name: str = ""
    is_drawer_open: bool = False
    editing_solution_id: int = -1   
    target_parent_id: int = -1 # Tracks if we are branching an existing solution
    outcomes: list[OutcomeItem] = []
    outcome_names: list[str] = ["All Outcomes"]
    active_outcome_name: str = "All Outcomes"
    new_outcome_name: str = ""
    selected_opp_outcome_name: str = ""    
    # --- OPPORTUNITY CRUD STATE ---
    editing_opp_id: int = -1
    manual_opp_theme: str = "Uncategorized"
    manual_opp_statement: str = ""
    is_opp_dialog_open: bool = False
    # --- EVIDENCE TRACKING ---
    interview_choices: list[str] = []
    selected_interview_choice: str = ""
    manual_quote_text: str = ""
    
    # Initialize with a blank dummy object so the React frontend never hits a "null" crash
    selected_opportunity: LedgerItem = LedgerItem(
        opportunity_id=0,
        theme="",
        personas_affected=[],
        opportunity="",
        status="",
        status_color="gray",
        days_old=0,
        is_cross_functional=False,
        evidence=[],
        solutions=[],
        linked_outcomes=[]
    )

    interview_history: list[InterviewHistoryItem] = []

    def handle_navigation(self, view_name: str):
        """Bulletproof router: Standard synchronous state updates."""
        self.current_view = view_name
        if view_name == "logs":
            self.load_history()
        elif view_name == "ledger":
            self.load_ledger()

    def load_history(self):
        """Loads all past interviews for the management tab."""
        with rx.session() as session:
            interviews = session.exec(select(Interview)).all()
            history = []
            for inv in interviews:
                persona = session.get(Persona, inv.persona_id)
                date_str = inv.date_logged.strftime("%Y-%m-%d %H:%M") if inv.date_logged else "Unknown"
                snippet = inv.transcript[:80] + "..." if inv.transcript else "No transcript."
                history.append(InterviewHistoryItem(
                    interview_id=inv.id,
                    persona=persona.name,
                    date_logged=date_str,
                    snippet=snippet
                ))
            self.interview_history = history[::-1]

    def delete_interview(self, interview_id: int):
        """Cascading delete."""
        with rx.session() as session:
            interview = session.get(Interview, interview_id)
            if not interview: return
            links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.interview_id == interview_id)).all()
            opportunity_ids = set([link.opportunity_id for link in links])
            for link in links:
                session.delete(link)
            session.delete(interview)
            session.commit()
            for opp_id in opportunity_ids:
                remaining_links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.opportunity_id == opp_id)).all()
                if len(remaining_links) == 0:
                    opp = session.get(Opportunity, opp_id)
                    if opp: session.delete(opp)
            session.commit()
            
        # Unified State allows safe, direct calls! No WebSockets needed.
        self.load_history()
        self.load_ledger()
    
    @rx.var
    def selectable_outcomes(self) -> list[str]:
        """A computed variable that strictly returns the names of the outcomes, plus a None option."""
        return ["None (Unmapped)"] + [o.name for o in self.outcomes]

    def handle_navigation(self, view_name: str):
        """Safely handles routing and triggers domain-specific data loads."""
        self.current_view = view_name
        
        # Tell each domain to load its fresh data ONLY when navigated to!
        if view_name == "logs":
            return State.load_history()
        elif view_name == "ledger":
            return State.load_ledger()

    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files: return
        file = files[0]
        upload_data = await file.read()
        filename = file.filename.lower()
        try:
            if filename.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(upload_data))
                self.transcript_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            elif filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(upload_data))
                self.transcript_text = "\n".join([para.text for para in doc.paragraphs])
            else:
                self.transcript_text = upload_data.decode("utf-8")
        except Exception as e:
            return rx.window_alert(f"Failed to parse file: {str(e)}")

    def run_synthesis(self):
        if not self.transcript_text.strip() or not self.persona_input.strip():
            return rx.window_alert("Error: Both Persona and Transcript are required.")
            
        self.is_processing = True
        yield
        
        try:
            synthesis_prompt = load_prompt("synthesis.txt")
            response = pro_model.generate_content(
                f"{synthesis_prompt}\n\nTranscript:\n{self.transcript_text}",
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=InterviewSnapshot,
                )
            )
            result = json.loads(response.text)
            new_opps = result.get("opportunities", [])
            
            with rx.session() as session:
                # 1. Setup Persona & Interview
                persona = session.exec(select(Persona).where(Persona.name == self.persona_input)).first()
                if not persona:
                    persona = Persona(name=self.persona_input)
                    session.add(persona)
                    session.commit()
                    session.refresh(persona)
                    
                interview = Interview(
                    persona_id=persona.id,
                    transcript=self.transcript_text[:500] + "...[TRUNCATED]",
                    quality_score=result.get("quality_check", {}).get("score", 0),
feedback=result.get("quality_check", {}).get("feedback", "No feedback generated."),
                    memorable_quote=result["memorable_quote"]
                )
                session.add(interview)
                session.commit()
                session.refresh(interview)
                
                # 2. Fetch all existing Master Opportunities
                existing_opps = session.exec(select(Opportunity)).all()
                existing_opps_dict = {opp.id: opp.statement for opp in existing_opps}
                
                matched_results = []
                
                if not existing_opps_dict or not new_opps:
                    for opp in new_opps:
                        matched_results.append({"new_opportunity_statement": opp["opportunity_statement"], "matched_existing_id": None, "quote": opp["source_quote"]})
                else:
                    dedupe_template = load_prompt("dedupe.txt")
                    new_opps_list = [o["opportunity_statement"] for o in new_opps]
                    
                    # Inject variables into the template
                    dedupe_prompt = dedupe_template.format(
                        existing_opps_dict=existing_opps_dict,
                        new_opps_list=new_opps_list
                    )
                    
                    dedupe_response = flash_model.generate_content(
                        dedupe_prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=DedupeResult,
                        )
                    )
                    dedupe_json = json.loads(dedupe_response.text)
                    
                    for match in dedupe_json.get("matches", []):
                        # Find the original extraction to get the quote AND the theme
                        original_opp = next((o for o in new_opps if o["opportunity_statement"] == match["new_opportunity_statement"]), None)
                        quote = original_opp["source_quote"] if original_opp else "No quote found."
                        theme = original_opp["theme"] if original_opp else "General" # Grab the theme
                        
                        matched_results.append({
                            "theme": theme,
                            "new_opportunity_statement": match["new_opportunity_statement"],
                            "matched_existing_id": match["matched_existing_id"],
                            "quote": quote
                        })

                # 3. Database Injection
                linked_master_opp_ids = set()
                
                for item in matched_results:
                    matched_id = item["matched_existing_id"]
                    if matched_id and matched_id in existing_opps_dict:
                        master_opp = session.get(Opportunity, matched_id)
                        master_opp.date_last_validated = datetime.now(timezone.utc)
                        session.add(master_opp)
                    else:
                        # BRAND NEW OPPORTUNITY
                        master_opp = Opportunity(
                            theme=item["theme"], # Save the theme to SQLite
                            statement=item["new_opportunity_statement"]
                        )
                        session.add(master_opp)
                        session.commit()
                        session.refresh(master_opp)
                        existing_opps_dict[master_opp.id] = master_opp.statement
                        
                    if master_opp.id not in linked_master_opp_ids:
                        link = InterviewOpportunityLink(
                            interview_id=interview.id,
                            opportunity_id=master_opp.id,
                            source_quote=item["quote"]
                        )
                        session.add(link)
                        linked_master_opp_ids.add(master_opp.id)
                
                session.commit()
            
            self.load_ledger()
            self.transcript_text = ""
            return rx.window_alert(f"Success! Score: {result['quality_check']['score']}/10. Deduplication Complete.")
            
        except Exception as e:
            return rx.window_alert(f"Engine Failure: {str(e)}")
        finally:
            self.is_processing = False

    def load_ledger(self):
        self.load_outcomes()
        with rx.session() as session:
            opportunities = session.exec(select(Opportunity)).all()
            new_ledger = []
            personas_set = set()
            now = datetime.now(timezone.utc)
            
            for opp in opportunities:
                links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.opportunity_id == opp.id)).all()
                affected_personas = set()
                evidence_list = [] # <--- Track the quotes for this row
                safe_colors = ["blue", "purple", "orange", "green", "pink", "teal", "ruby", "iris", "indigo"]

                for link in links:
                    interview = session.get(Interview, link.interview_id)
                    persona = session.get(Persona, interview.persona_id)
                    affected_personas.add(persona.name)
                    personas_set.add(persona.name)

                    # Calculate the same stable color for the evidence card
                    color_index = sum(ord(c) for c in persona.name) % len(safe_colors)
                    p_color = safe_colors[color_index]

                    # Add the raw quote to the evidence list
                    evidence_list.append(QuoteItem(
                        interview_id=interview.id,
                        persona_name=persona.name,
                        persona_color=p_color,
                        text=link.source_quote
                    ))
                
                db_date = opp.date_last_validated.replace(tzinfo=timezone.utc) if opp.date_last_validated.tzinfo is None else opp.date_last_validated
                days_old = (now - db_date).days
                
                if days_old > 45: 
                    status = "STALE (>45 Days)"
                    status_color = "red"
                elif days_old > 21: 
                    status = "DECAYING (>21 Days)"
                    status_color = "yellow"
                else: 
                    status = "FRESH"
                    status_color = "green"

                # Calculate the badges
                badge_list = []
                for p in sorted(list(affected_personas)):
                    color_index = sum(ord(c) for c in p) % len(safe_colors)
                    badge_list.append(PersonaBadge(name=p, color=safe_colors[color_index]))
                    
                # --- NEW: Fetch existing solutions for this opportunity ---
                db_solutions = session.exec(select(Solution).where(Solution.opportunity_id == opp.id)).all()
                
                # Flatten hierarchical solutions into a logically sorted list with indent levels
                children_map = {}
                top_level = []
                for s in db_solutions:
                    if s.parent_id:
                        if s.parent_id not in children_map:
                            children_map[s.parent_id] = []
                        children_map[s.parent_id].append(s)
                    else:
                        top_level.append(s)
                        
                flat_sols = []
                def append_children(parent_id, current_level):
                    if parent_id in children_map:
                        for child in children_map[parent_id]:
                            flat_sols.append(SolutionItem(
                                id=child.id, 
                                parent_id=child.parent_id,
                                name=child.name, 
                                description=child.description, 
                                status=child.status,
                                indent_level=current_level
                            ))
                            append_children(child.id, current_level + 1)

                for s in top_level:
                    flat_sols.append(SolutionItem(
                        id=s.id, 
                        parent_id=s.parent_id,
                        name=s.name, 
                        description=s.description, 
                        status=s.status,
                        indent_level=0
                    ))
                    append_children(s.id, 1)

                sol_items = flat_sols

                # --- NEW: Fetch and Map Outcomes ---
                outcome_links = session.exec(select(OutcomeOpportunityLink).where(OutcomeOpportunityLink.opportunity_id == opp.id)).all()
                linked_out_ids = [link.outcome_id for link in outcome_links]
                
                # FILTER THE BOARD: If we are focused on a specific outcome, skip rows that don't match
                # FILTER THE BOARD: Handle "All", "Unmapped", or "Specific Outcome"
                if self.active_outcome_name == "Unmapped Opportunities":
                    if len(linked_out_ids) > 0:
                        continue # Skip mapped rows
                elif self.active_outcome_name != "All Outcomes":
                    active_out = next((o for o in self.outcomes if o.name == self.active_outcome_name), None)
                    if active_out and active_out.id not in linked_out_ids:
                        continue # Skip rows that don't match the specific outcome

                linked_out_items = [out for out in self.outcomes if out.id in linked_out_ids]
                
                new_ledger.append(LedgerItem(
                    opportunity_id=opp.id, # <--- NEW: Tells the UI which DB row this is
                    theme=opp.theme,
                    personas_affected=badge_list,
                    opportunity=opp.statement,
                    status=status,
                    status_color=status_color,
                    days_old=days_old,
                    is_cross_functional=len(affected_personas) > 1,
                    evidence=evidence_list,
                    solutions=sol_items,
                    linked_outcomes=linked_out_items
                ))
            
            # Sort the ledger alphabetically by Theme
            self.ledger_data = sorted(new_ledger, key=lambda x: x.theme)
            
            self.available_personas = list(personas_set)
            if self.available_personas and not self.target_persona:
                self.target_persona = self.available_personas[0]

            # --- POPULATE REAL INTERVIEW CHOICES ---
            all_interviews = session.exec(select(Interview)).all()
            choices = []
            for inv in all_interviews:
                p = session.get(Persona, inv.persona_id)
                date_str = inv.date_logged.strftime("%Y-%m-%d") if inv.date_logged else "Unknown"
                # Format: "ID - Persona (Date)" so we can parse the ID later
                choices.append(f"{inv.id} - {p.name} ({date_str})")
            self.interview_choices = choices[::-1] # Reverse to show newest first
    
    def open_drawer(self, item: LedgerItem):
        """Opens the workspace and perfectly syncs the state."""
        self.selected_opportunity = item
        
        # Sync the outcome dropdown, defaulting to Unmapped if empty
        if len(item.linked_outcomes) > 0:
            self.selected_opp_outcome_name = item.linked_outcomes[0].name
        else:
            self.selected_opp_outcome_name = "None (Unmapped)"
            
        self.cancel_edit() 
        self.is_drawer_open = True

    def close_drawer(self):
        self.is_drawer_open = False

    def handle_drawer_change(self, is_open: bool):
        """Catches when the drawer is opened/closed via clicking outside or hitting Escape."""
        self.is_drawer_open = is_open


    def set_target_parent(self, sol_id: int, sol_name: str):
        """Activates 'Branching' mode and remembers the parent's name."""
        self.target_parent_id = sol_id
        self.target_parent_name = sol_name
        self.editing_solution_id = -1
        self.new_solution_name = ""
        self.new_solution_desc = ""

    def cancel_edit(self):
        """Clears the input form and exits edit/branch mode."""
        self.editing_solution_id = -1
        self.target_parent_id = -1
        self.target_parent_name = ""
        self.new_solution_name = ""
        self.new_solution_desc = ""

    def delete_solution(self, solution_id: int):
        """Permanently removes a solution AND recursively deletes all its nested children."""
        with rx.session() as session:
            def delete_recursive(sol_id):
                children = session.exec(select(Solution).where(Solution.parent_id == sol_id)).all()
                for c in children:
                    delete_recursive(c.id)
                sol = session.get(Solution, sol_id)
                if sol:
                    session.delete(sol)
            
            delete_recursive(solution_id)
            session.commit()
        
        self.load_ledger()
        self._sync_drawer()    

    def delete_solution(self, solution_id: int):
        """Permanently removes a solution from the database."""
        with rx.session() as session:
            sol = session.get(Solution, solution_id)
            if sol:
                session.delete(sol)
                session.commit()
        
        self.load_ledger()
        self._sync_drawer()

    def start_edit_solution(self, sol: SolutionItem):
        """Populates the input form with the existing solution's data."""
        self.editing_solution_id = sol.id
        self.new_solution_name = sol.name
        self.new_solution_desc = sol.description
        
    def _sync_drawer(self):
        """Helper: Refreshes the drawer UI after database changes."""
        if self.selected_opportunity and self.selected_opportunity.opportunity_id != 0:
            for item in self.ledger_data:
                if item.opportunity_id == self.selected_opportunity.opportunity_id:
                    self.selected_opportunity = item
                    # Grab the name of the first (and only) linked outcome, or "" if none
                    self.selected_opp_outcome_name = item.linked_outcomes[0].name if len(item.linked_outcomes) > 0 else ""
                    break

    def generate_hostile_questions(self):
        if not self.target_persona:
            return rx.window_alert("No persona selected.")
            
        self.is_prepping = True
        yield
        
        try:
            # 1. Gather opportunities (same logic as before)
            target_opps = []
            for item in self.ledger_data:
                if any(p.name == self.target_persona for p in item.personas_affected):
                    target_opps.append(item.opportunity)
                    
            if not target_opps:
                self.prep_questions = "No identified opportunities. Start fresh!"
                self.prep_last_updated = ""
                return
                
            # 2. Generate the content
            prep_template = load_prompt("prep.txt")
            prep_prompt = prep_template.format(
                target_persona=self.target_persona,
                target_opps=target_opps
            )
            generated_text = flash_model.generate_content(prep_prompt).text
            
            # 3. SAVE TO DATABASE
            with rx.session() as session:
                # specific logic: insert or update if exists
                existing_entry = session.get(PersonaPrep, self.target_persona)
                
                if existing_entry:
                    existing_entry.content = generated_text
                    existing_entry.updated_at = datetime.utcnow()
                    session.add(existing_entry)
                else:
                    new_entry = PersonaPrep(
                        persona=self.target_persona, 
                        content=generated_text,
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_entry)
                session.commit()

            # 4. Update UI
            self.prep_questions = generated_text
            self.prep_last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
            
        except Exception as e:
            self.prep_questions = f"Failed to generate: {str(e)}"
        finally:
            self.is_prepping = False

    # --- NEW: LOAD SCRIPT ON SELECTION ---
    def load_prep_for_persona(self, persona: str):
        """Sets the target persona and tries to load an existing script from DB."""
        self.target_persona = persona
        
        with rx.session() as session:
            # Try to find a saved script for this persona
            saved_prep = session.get(PersonaPrep, persona)
            
            if saved_prep:
                self.prep_questions = saved_prep.content
                # Format the date nicely
                self.prep_last_updated = saved_prep.updated_at.strftime("%Y-%m-%d %H:%M")
            else:
                self.prep_questions = ""
                self.prep_last_updated = ""

    def add_manual_solution(self, opportunity_id: int):
        """Saves a human-brainstormed solution or updates an existing one."""
        if not self.new_solution_name.strip():
            return rx.window_alert("Solution name cannot be empty.")
            
        with rx.session() as session:
            if self.editing_solution_id != -1:
                sol = session.get(Solution, self.editing_solution_id)
                if sol:
                    sol.name = self.new_solution_name.strip()
                    sol.description = self.new_solution_desc.strip()
                    session.add(sol)
            else:
                new_sol = Solution(
                    opportunity_id=opportunity_id,
                    parent_id=self.target_parent_id if self.target_parent_id != -1 else None,
                    name=self.new_solution_name.strip(),
                    description=self.new_solution_desc.strip()
                )
                session.add(new_sol)
            session.commit()
            
        # --- EXPLICIT FORCE RESET ---
        self.editing_solution_id = -1
        self.target_parent_id = -1
        self.target_parent_name = ""
        self.new_solution_name = ""
        self.new_solution_desc = ""
        
        self.load_ledger()
        self._sync_drawer()

    def generate_competing_solutions(self, opportunity_id: int):
        """Uses Gemini to read the evidence and propose distinct solutions via prompt file."""
        self.is_generating_solutions = True
        yield
        try:
            import json
            with rx.session() as session:
                opp = session.get(Opportunity, opportunity_id)
                if not opp: return

                links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.opportunity_id == opportunity_id)).all()
                evidence_texts = [link.source_quote for link in links]
                context = "\n".join(evidence_texts)

                # --- NEW: Load from external file ---
                prompt_template = load_prompt("solutions.txt")
                prompt = prompt_template.format(
                    opportunity_statement=opp.statement,
                    context=context
                )
                
                response = flash_model.generate_content(prompt).text
                cleaned_response = response.strip().strip("```json").strip("```")
                solutions_data = json.loads(cleaned_response)

                for s_data in solutions_data:
                    new_sol = Solution(
                        opportunity_id=opportunity_id,
                        name=s_data.get("name", "Untitled"),
                        description=s_data.get("description", "No description")
                    )
                    session.add(new_sol)
                session.commit()
                
            self.load_ledger()
            self._sync_drawer()

            # Sync the open drawer with the fresh data
            if self.selected_opportunity:
                for item in self.ledger_data:
                    if item.opportunity_id == self.selected_opportunity.opportunity_id:
                        self.selected_opportunity = item
                        break
        except Exception as e:
            print(f"Failed to generate solutions: {e}")
        finally:
            self.is_generating_solutions = False

    def load_outcomes(self):
        """Loads all business outcomes for the global dropdowns."""
        with rx.session() as session:
            db_outcomes = session.exec(select(Outcome)).all()
            self.outcomes = [OutcomeItem(id=o.id, name=o.name) for o in db_outcomes]
            # Add explicit filters for All and Unmapped
            self.outcome_names = ["All Outcomes", "Unmapped Opportunities"] + [o.name for o in self.outcomes]

    def create_outcome(self):
        """Creates a new top-level business outcome."""
        if not self.new_outcome_name.strip(): return
        with rx.session() as session:
            new_out = Outcome(name=self.new_outcome_name.strip(), description="")
            session.add(new_out)
            session.commit()
            
        self.active_outcome_name = self.new_outcome_name.strip()
        self.new_outcome_name = ""
        self.load_outcomes()
        self.load_ledger()

    def change_outcome_filter(self, name: str):
        """Changes the global board filter and reloads."""
        self.active_outcome_name = name
        self.load_ledger()

    def set_primary_outcome(self, outcome_name: str):
        """Forces an opportunity to have only ONE primary outcome, or none."""
        if not self.selected_opportunity: return
        
        # Optimistic UI update
        self.selected_opp_outcome_name = outcome_name 
        opp_id = self.selected_opportunity.opportunity_id
        
        # Will be None if they selected "None (Unmapped)"
        selected_out = next((o for o in self.outcomes if o.name == outcome_name), None) 
        
        with rx.session() as session:
            # Wipe ANY existing outcome links for this opportunity
            existing_links = session.exec(select(OutcomeOpportunityLink).where(
                OutcomeOpportunityLink.opportunity_id == opp_id
            )).all()
            for link in existing_links:
                session.delete(link)
                
            # Add the new link ONLY if they selected a real outcome
            if selected_out:
                session.add(OutcomeOpportunityLink(opportunity_id=opp_id, outcome_id=selected_out.id))
                
            session.commit()
            
        self.load_ledger()
        self._sync_drawer()

    def handle_opp_dialog_change(self, is_open: bool):
        """Catches when the dialog opens/closes and safely resets state."""
        self.is_opp_dialog_open = is_open
        if not is_open:
            # Wipe the form when they close it without saving
            self.editing_opp_id = -1
            self.manual_opp_theme = "Uncategorized"
            self.manual_opp_statement = ""

    def open_opp_dialog(self):
        """Opens the dialog for a BRAND NEW Opportunity."""
        self.editing_opp_id = -1
        self.manual_opp_theme = "Uncategorized"
        self.manual_opp_statement = ""
        self.is_opp_dialog_open = True

    def close_opp_dialog(self):
        self.is_opp_dialog_open = False

    def start_edit_opportunity(self, opp_id: int, theme: str, statement: str):
        """Opens the dialog to EDIT an existing Opportunity."""
        self.editing_opp_id = opp_id
        self.manual_opp_theme = theme
        self.manual_opp_statement = statement
        self.is_opp_dialog_open = True

    def save_manual_opportunity(self):
        """Handles both creating a new opportunity and updating an existing one."""
        if not self.manual_opp_statement.strip():
            return rx.window_alert("Opportunity statement cannot be empty.")
            
        with rx.session() as session:
            if self.editing_opp_id != -1:
                # UPDATE EXISTING
                opp = session.get(Opportunity, self.editing_opp_id)
                if opp:
                    opp.theme = self.manual_opp_theme.strip()
                    opp.statement = self.manual_opp_statement.strip()
                    session.add(opp)
            else:
                # CREATE NEW
                new_opp = Opportunity(
                    theme=self.manual_opp_theme.strip() or "Uncategorized",
                    statement=self.manual_opp_statement.strip()
                )
                session.add(new_opp)
            session.commit()
            
        self.close_opp_dialog()
        self.load_ledger()
        self._sync_drawer()

    def delete_opportunity(self, opp_id: int):
        """Safely deletes an opportunity and ALL its nested relationships."""
        with rx.session() as session:
            opp = session.get(Opportunity, opp_id)
            if not opp: return
            
            # 1. Delete Interview Links
            int_links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.opportunity_id == opp_id)).all()
            for link in int_links: session.delete(link)
            
            # 2. Delete Outcome Links
            out_links = session.exec(select(OutcomeOpportunityLink).where(OutcomeOpportunityLink.opportunity_id == opp_id)).all()
            for link in out_links: session.delete(link)
            
            # 3. Delete Solutions (and their sub-solutions recursively)
            def delete_sol_recursive(sol_id):
                children = session.exec(select(Solution).where(Solution.parent_id == sol_id)).all()
                for c in children: delete_sol_recursive(c.id)
                sol_to_del = session.get(Solution, sol_id)
                if sol_to_del: session.delete(sol_to_del)

            sols = session.exec(select(Solution).where(Solution.opportunity_id == opp_id)).all()
            for s in sols: delete_sol_recursive(s.id)

            # 4. Finally, delete the Opportunity itself
            session.delete(opp)
            session.commit()
        
        # If they deleted the opportunity while it was open in the drawer, close it!
        if self.selected_opportunity and self.selected_opportunity.opportunity_id == opp_id:
            self.close_drawer()
            
        self.load_ledger()

    def add_real_evidence(self, opportunity_id: int):
        """Links a missed quote from a real interview to this opportunity."""
        if not self.selected_interview_choice or not self.manual_quote_text.strip():
            return rx.window_alert("Please select an interview and enter a quote.")

        # Extract the ID from the string (e.g., "12 - Sales (2024-02-26)" -> 12)
        try:
            inv_id = int(self.selected_interview_choice.split(" - ")[0])
        except:
            return rx.window_alert("Invalid interview selection.")

        with rx.session() as session:
            # Check if this interview is already linked to this opportunity
            existing = session.get(InterviewOpportunityLink, (inv_id, opportunity_id))
            if existing:
                return rx.window_alert("This interview is already linked here. Edit the transcript instead.")

            new_link = InterviewOpportunityLink(
                interview_id=inv_id,
                opportunity_id=opportunity_id,
                source_quote=self.manual_quote_text.strip()
            )
            session.add(new_link)
            session.commit()

        self.manual_quote_text = ""
        self.selected_interview_choice = ""
        self.load_ledger()
        self._sync_drawer()

    def delete_evidence(self, opportunity_id: int, interview_id: int):
        """Unlinks an interview quote from an opportunity."""
        with rx.session() as session:
            link = session.get(InterviewOpportunityLink, (interview_id, opportunity_id))
            if link:
                session.delete(link)
                session.commit()
                
        self.load_ledger()
        self._sync_drawer()