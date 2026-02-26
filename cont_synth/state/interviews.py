import io
import json
from datetime import datetime, timezone

import google.generativeai as genai
import PyPDF2
import docx
import reflex as rx
from sqlmodel import select

from ..models import (
    Persona,
    Interview,
    Opportunity,
)
from .core import (
    InterviewHistoryItem,
    PersonaPrep,
    load_prompt,
    pro_model,
    flash_model,
)
from schema import InterviewSnapshot, DedupeResult


class InterviewStateMixin(rx.State, mixin=True):
    """Interview ingestion, synthesis, history, and prep logic mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

    def load_history(self):
        """Loads all past interviews for the management tab."""
        with rx.session() as session:
            interviews = session.exec(select(Interview)).all()
            history: list[InterviewHistoryItem] = []
            for inv in interviews:
                persona = session.get(Persona, inv.persona_id)
                date_str = (
                    inv.date_logged.strftime("%Y-%m-%d %H:%M")
                    if inv.date_logged
                    else "Unknown"
                )
                snippet = (
                    inv.transcript[:80] + "..." if inv.transcript else "No transcript."
                )
                history.append(
                    InterviewHistoryItem(
                        interview_id=inv.id,
                        persona=persona.name,
                        date_logged=date_str,
                        snippet=snippet,
                    )
                )
            self.interview_history = history[::-1]

    def delete_interview(self, interview_id: int):
        """Cascading delete for interviews and orphaned opportunities."""
        from ..models import InterviewOpportunityLink as IOL  # local alias

        with rx.session() as session:
            interview = session.get(Interview, interview_id)
            if not interview:
                return

            links = session.exec(
                select(IOL).where(IOL.interview_id == interview_id)
            ).all()
            opportunity_ids = {link.opportunity_id for link in links}

            for link in links:
                session.delete(link)
            session.delete(interview)
            session.commit()

            for opp_id in opportunity_ids:
                remaining_links = session.exec(
                    select(IOL).where(IOL.opportunity_id == opp_id)
                ).all()
                if len(remaining_links) == 0:
                    opp = session.get(Opportunity, opp_id)
                    if opp:
                        session.delete(opp)
            session.commit()

        self.load_history()
        # Ledger depends on interviews, so refresh it too.
        self.load_ledger()

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Parses uploaded transcript files into raw text."""
        if not files:
            return
        file = files[0]
        upload_data = await file.read()
        filename = file.filename.lower()
        try:
            if filename.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(upload_data))
                self.transcript_text = "\n".join(
                    [
                        page.extract_text()
                        for page in pdf_reader.pages
                        if page.extract_text()
                    ]
                )
            elif filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(upload_data))
                self.transcript_text = "\n".join(para.text for para in doc.paragraphs)
            else:
                self.transcript_text = upload_data.decode("utf-8")
        except Exception as e:  # pragma: no cover - UI alert path
            return rx.window_alert(f"Failed to parse file: {str(e)}")

    def run_synthesis(self):
        """Runs Gemini-based synthesis and opportunity dedupe."""
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
                ),
            )
            result = json.loads(response.text)
            new_opps = result.get("opportunities", [])

            from ..models import InterviewOpportunityLink as IOL

            with rx.session() as session:
                # 1. Setup Persona & Interview
                persona = session.exec(
                    select(Persona).where(Persona.name == self.persona_input)
                ).first()
                if not persona:
                    persona = Persona(name=self.persona_input)
                    session.add(persona)
                    session.commit()
                    session.refresh(persona)

                interview = Interview(
                    persona_id=persona.id,
                    transcript=self.transcript_text[:500] + "...[TRUNCATED]",
                    quality_score=result.get("quality_check", {}).get("score", 0),
                    feedback=result.get("quality_check", {}).get(
                        "feedback", "No feedback generated."
                    ),
                    memorable_quote=result["memorable_quote"],
                )
                session.add(interview)
                session.commit()
                session.refresh(interview)

                # 2. Fetch all existing Master Opportunities
                existing_opps = session.exec(select(Opportunity)).all()
                existing_opps_dict = {opp.id: opp.statement for opp in existing_opps}

                matched_results: list[dict] = []

                if not existing_opps_dict or not new_opps:
                    for opp in new_opps:
                        matched_results.append(
                            {
                                "new_opportunity_statement": opp[
                                    "opportunity_statement"
                                ],
                                "matched_existing_id": None,
                                "quote": opp["source_quote"],
                            }
                        )
                else:
                    dedupe_template = load_prompt("dedupe.txt")
                    new_opps_list = [o["opportunity_statement"] for o in new_opps]

                    dedupe_prompt = dedupe_template.format(
                        existing_opps_dict=existing_opps_dict,
                        new_opps_list=new_opps_list,
                    )

                    dedupe_response = flash_model.generate_content(
                        dedupe_prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=DedupeResult,
                        ),
                    )
                    dedupe_json = json.loads(dedupe_response.text)

                    for match in dedupe_json.get("matches", []):
                        original_opp = next(
                            (
                                o
                                for o in new_opps
                                if o["opportunity_statement"]
                                == match["new_opportunity_statement"]
                            ),
                            None,
                        )
                        quote = (
                            original_opp["source_quote"]
                            if original_opp
                            else "No quote found."
                        )
                        theme = original_opp["theme"] if original_opp else "General"

                        matched_results.append(
                            {
                                "theme": theme,
                                "new_opportunity_statement": match[
                                    "new_opportunity_statement"
                                ],
                                "matched_existing_id": match["matched_existing_id"],
                                "quote": quote,
                            }
                        )

                # 3. Database Injection
                linked_master_opp_ids: set[int] = set()

                for item in matched_results:
                    matched_id = item["matched_existing_id"]
                    if matched_id and matched_id in existing_opps_dict:
                        master_opp = session.get(Opportunity, matched_id)
                        master_opp.date_last_validated = datetime.now(timezone.utc)
                        session.add(master_opp)
                    else:
                        master_opp = Opportunity(
                            theme=item["theme"],
                            statement=item["new_opportunity_statement"],
                        )
                        session.add(master_opp)
                        session.commit()
                        session.refresh(master_opp)
                        existing_opps_dict[master_opp.id] = master_opp.statement

                    if master_opp.id not in linked_master_opp_ids:
                        link = IOL(
                            interview_id=interview.id,
                            opportunity_id=master_opp.id,
                            source_quote=item["quote"],
                        )
                        session.add(link)
                        linked_master_opp_ids.add(master_opp.id)

                session.commit()

            self.load_ledger()
            self.transcript_text = ""
            return rx.window_alert(
                f"Success! Score: {result['quality_check']['score']}/10. Deduplication Complete."
            )

        except Exception as e:  # pragma: no cover - UI alert path
            return rx.window_alert(f"Engine Failure: {str(e)}")
        finally:
            self.is_processing = False

    def generate_hostile_questions(self):
        """Generates prep script for the currently selected persona."""
        if not getattr(self, "target_persona", ""):
            return rx.window_alert("No persona selected.")

        self.is_prepping = True
        yield

        try:
            target_opps: list[str] = []
            for item in getattr(self, "ledger_data", []):
                if any(p.name == self.target_persona for p in item.personas_affected):
                    target_opps.append(item.opportunity)

            if not target_opps:
                self.prep_questions = "No identified opportunities. Start fresh!"
                self.prep_last_updated = ""
                return

            prep_template = load_prompt("prep.txt")
            prep_prompt = prep_template.format(
                target_persona=self.target_persona,
                target_opps=target_opps,
            )
            generated_text = flash_model.generate_content(prep_prompt).text

            with rx.session() as session:
                existing_entry = session.get(PersonaPrep, self.target_persona)

                if existing_entry:
                    existing_entry.content = generated_text
                    existing_entry.updated_at = datetime.utcnow()
                    session.add(existing_entry)
                else:
                    new_entry = PersonaPrep(
                        persona=self.target_persona,
                        content=generated_text,
                        updated_at=datetime.utcnow(),
                    )
                    session.add(new_entry)
                session.commit()

            self.prep_questions = generated_text
            self.prep_last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

        except Exception as e:  # pragma: no cover - UI alert path
            self.prep_questions = f"Failed to generate: {str(e)}"
        finally:
            self.is_prepping = False

    def load_prep_for_persona(self, persona: str):
        """Sets the target persona and tries to load an existing script from DB."""
        self.target_persona = persona

        with rx.session() as session:
            saved_prep = session.get(PersonaPrep, persona)

            if saved_prep:
                self.prep_questions = saved_prep.content
                self.prep_last_updated = saved_prep.updated_at.strftime(
                    "%Y-%m-%d %H:%M"
                )
            else:
                self.prep_questions = ""
                self.prep_last_updated = ""
