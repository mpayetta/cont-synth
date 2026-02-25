import reflex as rx
import google.generativeai as genai
import os
import json
import io
import PyPDF2
import docx
from datetime import datetime, timezone
from sqlmodel import select

from .models import Persona, Interview, Opportunity, InterviewOpportunityLink
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
    persona_name: str
    persona_color: str
    text: str

class LedgerItem(rx.Base):
    theme: str
    personas_affected: list[PersonaBadge] # <--- Changed from str to a list of Badges
    opportunity: str
    status: str
    status_color: str
    days_old: int
    is_cross_functional: bool
    evidence: list[QuoteItem]

class InterviewHistoryItem(rx.Base):
    interview_id: int
    persona: str
    date_logged: str
    snippet: str
    
# --- THE STATE (BACKEND LOGIC) ---
class State(rx.State):
    is_processing: bool = False
    is_prepping: bool = False
    ledger_data: list[LedgerItem] = []
    available_personas: list[str] = []
    interview_history: list[InterviewHistoryItem] = [] 
    target_persona: str = ""
    prep_questions: str = ""
    persona_input: str = ""
    transcript_text: str = ""
    current_view: str = "synthesize"

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
                    
                new_ledger.append(LedgerItem(
                    theme=opp.theme,
                    personas_affected=badge_list,
                    opportunity=opp.statement,
                    status=status,
                    status_color=status_color,
                    days_old=days_old,
                    is_cross_functional=len(affected_personas) > 1,
                    evidence=evidence_list # <--- Pass the quotes to the frontend
                ))
            
            # Sort the ledger alphabetically by Theme
            self.ledger_data = sorted(new_ledger, key=lambda x: x.theme)
            
            # Sync the history logs
            self.load_history()
            
            self.ledger_data = new_ledger
            self.available_personas = list(personas_set)
            if self.available_personas and not self.target_persona:
                self.target_persona = self.available_personas[0]
    
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
            self.interview_history = history[::-1] # Reverse list so newest is on top

    def delete_interview(self, interview_id: int):
        """Cascading delete: removes the interview, the links, and any orphaned opportunities."""
        with rx.session() as session:
            interview = session.get(Interview, interview_id)
            if not interview: return

            # 1. Find all Many-to-Many links connected to this transcript
            links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.interview_id == interview_id)).all()
            opportunity_ids = set([link.opportunity_id for link in links])
            
            # 2. Delete the links
            for link in links:
                session.delete(link)
            
            # 3. Delete the actual Interview record
            session.delete(interview)
            session.commit() # Commit here so the links are officially gone
            
            # 4. The Orphan Check: Did we leave any Master Opportunities with 0 evidence?
            for opp_id in opportunity_ids:
                remaining_links = session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.opportunity_id == opp_id)).all()
                if len(remaining_links) == 0:
                    opp = session.get(Opportunity, opp_id)
                    if opp: session.delete(opp)
                    
            session.commit()
            
        # Refresh the UI
        self.load_ledger()

    def generate_hostile_questions(self):
        if not self.target_persona:
            return rx.window_alert("No persona selected.")
        self.is_prepping = True
        yield
        try:
            # Safely extract all opportunities where this persona is affected
            target_opps = []
            for item in self.ledger_data:
                # Check if our target persona name matches any of the badges on this row
                if any(p.name == self.target_persona for p in item.personas_affected):
                    target_opps.append(item.opportunity)
                    
            if not target_opps:
                self.prep_questions = "No previously identified opportunities found for this persona. You are starting from a blank slate. Focus on broad, open-ended discovery!"
                return
                
            prep_template = load_prompt("prep.txt")
            prep_prompt = prep_template.format(
                target_persona=self.target_persona,
                target_opps=target_opps
            )
            
            self.prep_questions = flash_model.generate_content(prep_prompt).text
        except Exception as e:
            self.prep_questions = f"Failed to generate: {str(e)}"
        finally:
            self.is_prepping = False