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
    InterviewOpportunityLink,
    LlmUsageLog,
)
from .core import (
    InterviewHistoryItem,
    QuoteItem,
    PersonaPrep,
    PendingOppItem,
    PendingLlmUsage,
    load_prompt,
    pro_model,
    flash_model,
)
from schema import InterviewSnapshot, DedupeResult

_SCROLL_TO_MARK = (
    "setTimeout(() => {"
    # Try scoped container search first (more reliable), then fall back globally
    " const ids = ['synthesis-transcript', 'interview-transcript', 'drawer-transcript'];"
    " let found = false;"
    " for (const id of ids) {"
    "   const c = document.getElementById(id);"
    "   if (c) { const m = c.querySelector('mark');"
    "     if (m) { m.scrollIntoView({behavior:'smooth', block:'center'}); found = true; break; } }"
    " }"
    " if (!found) { const m = document.querySelector('mark');"
    "   if (m) m.scrollIntoView({behavior:'smooth', block:'center'}); }"
    "}, 150)"
)


class InterviewStateMixin(rx.State, mixin=True):
    """Interview ingestion, synthesis, history, and prep logic mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

    _PERSONA_COLORS = [
        "blue", "purple", "orange", "green", "pink", "teal", "ruby", "iris", "indigo",
    ]

    def _persona_color(self, name: str) -> str:
        idx = sum(ord(c) for c in name) % len(self._PERSONA_COLORS)
        return self._PERSONA_COLORS[idx]

    def load_history(self):
        """Loads all past interviews for the management tab."""
        with rx.session() as session:
            interviews = session.exec(select(Interview).where(Interview.product_id == int(self.active_product_id))).all()
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
                        persona_color=self._persona_color(persona.name),
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
        """Runs Gemini-based synthesis and opportunity dedupe, then shows the review step."""
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

            pending_usages: list[PendingLlmUsage] = [
                PendingLlmUsage(
                    model_name="gemini-2.5-pro",
                    operation="synthesis",
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    output_tokens=response.usage_metadata.candidates_token_count,
                    total_tokens=response.usage_metadata.total_token_count,
                )
            ]

            # Load existing opps for deduplication (outside session to avoid holding it)
            with rx.session() as session:
                existing_opps = session.exec(
                    select(Opportunity).where(Opportunity.product_id == int(self.active_product_id))
                ).all()
                existing_opps_dict = {opp.id: opp.statement for opp in existing_opps}

            matched_results: list[dict] = []

            if not existing_opps_dict or not new_opps:
                for opp in new_opps:
                    matched_results.append(
                        {
                            "theme": opp.get("theme", "Uncategorized"),
                            "new_opportunity_statement": opp["opportunity_statement"],
                            "matched_existing_id": None,
                            "matched_existing_statement": "",
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
                pending_usages.append(
                    PendingLlmUsage(
                        model_name="gemini-2.5-flash",
                        operation="dedupe",
                        prompt_tokens=dedupe_response.usage_metadata.prompt_token_count,
                        output_tokens=dedupe_response.usage_metadata.candidates_token_count,
                        total_tokens=dedupe_response.usage_metadata.total_token_count,
                    )
                )

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
                    matched_id = match.get("matched_existing_id")
                    matched_statement = existing_opps_dict.get(matched_id, "") if matched_id else ""

                    matched_results.append(
                        {
                            "theme": theme,
                            "new_opportunity_statement": match["new_opportunity_statement"],
                            "matched_existing_id": matched_id,
                            "matched_existing_statement": matched_statement,
                            "quote": quote,
                        }
                    )

            # Build pending opp list for review step (no DB writes yet)
            pending_opps: list[PendingOppItem] = []
            for i, item in enumerate(matched_results):
                matched_id = item["matched_existing_id"]
                pending_opps.append(
                    PendingOppItem(
                        index=i,
                        opportunity_statement=item["new_opportunity_statement"],
                        theme=item["theme"],
                        source_quote=item["quote"],
                        matched_existing_id=matched_id if matched_id is not None else -1,
                        matched_existing_statement=item.get("matched_existing_statement", ""),
                        selected=True,
                    )
                )

            # Store pending synthesis state
            self.pending_synthesis_transcript = self.transcript_text
            self.pending_synthesis_persona = self.persona_input
            self.pending_synthesis_quality = result.get("quality_check", {}).get("score", 0)
            self.pending_synthesis_feedback = result.get("quality_check", {}).get("feedback", "")
            self.pending_synthesis_memorable_quote = result.get("memorable_quote", "")
            self.pending_synthesis_opps = pending_opps
            self.pending_llm_usages = pending_usages
            self.highlighted_quote_text = pending_opps[0].source_quote if pending_opps else ""

            # Clear the input form
            self.transcript_text = ""
            self.persona_input = ""

            # Navigate to review
            self.current_view = "synthesis_review"

        except Exception as e:  # pragma: no cover - UI alert path
            print(f"Engine Failure: {str(e)}")
            return rx.window_alert(f"Engine Failure: {str(e)}")
        finally:
            self.is_processing = False

    def toggle_pending_opp(self, index: int):
        """Toggle the selected state of a pending opportunity by its index."""
        new_list = []
        for opp in self.pending_synthesis_opps:
            if opp.index == index:
                new_list.append(
                    PendingOppItem(
                        index=opp.index,
                        opportunity_statement=opp.opportunity_statement,
                        theme=opp.theme,
                        source_quote=opp.source_quote,
                        matched_existing_id=opp.matched_existing_id,
                        matched_existing_statement=opp.matched_existing_statement,
                        selected=not opp.selected,
                    )
                )
            else:
                new_list.append(opp)
        self.pending_synthesis_opps = new_list

    async def set_highlighted_quote(self, quote: str):
        """Highlight the given quote text in the transcript panel and scroll to it."""
        self.highlighted_quote_text = quote
        self.scroll_trigger += 1  # Ensures a state delta even when the quote didn't change
        yield  # Flush state to frontend (re-renders transcript with <mark>) before scrolling
        yield rx.call_script(_SCROLL_TO_MARK)

    def _load_drawer_transcript(self, interview_id: int) -> bool:
        """Load an interview's transcript and persona into drawer state fields.
        Returns False if the interview doesn't exist."""
        with rx.session() as session:
            interview = session.get(Interview, interview_id)
            if not interview:
                return False
            persona = session.get(Persona, interview.persona_id)
            date_str = (
                interview.date_logged.strftime("%Y-%m-%d %H:%M")
                if interview.date_logged
                else "Unknown"
            )
        self.transcript_drawer_interview_id = interview_id
        self.transcript_drawer_transcript = interview.transcript
        self.transcript_drawer_persona = persona.name
        self.transcript_drawer_persona_color = self._persona_color(persona.name)
        self.transcript_drawer_date = date_str
        return True

    async def open_transcript_drawer(self, interview_id: int, quote_text: str):
        """Open the drawer in view mode with the given quote highlighted and scrolled to."""
        if not self._load_drawer_transcript(interview_id):
            return
        self.transcript_drawer_mode = "view"
        self.transcript_drawer_open = True
        self.highlighted_quote_text = quote_text
        self.scroll_trigger += 1
        yield
        yield rx.call_script(_SCROLL_TO_MARK)

    def open_transcript_for_selection(self, opportunity_id: int):
        """Open the drawer in select mode so the user can drag-select a quote."""
        if not self.selected_interview_choice:
            return rx.window_alert("Please select an interview first.")
        try:
            inv_id = int(self.selected_interview_choice.split(" - ")[0])
        except Exception:
            return rx.window_alert("Invalid interview selection.")
        if not self._load_drawer_transcript(inv_id):
            return
        self.transcript_drawer_mode = "select"
        self.transcript_drawer_opportunity_id = opportunity_id
        self.transcript_drawer_selection = ""
        self.highlighted_quote_text = ""
        self.transcript_drawer_open = True

    def set_drawer_selection(self, selection: str):
        """JS callback — stores captured selection and highlights it (select mode only)."""
        if self.transcript_drawer_mode != "select":
            return
        if selection.strip():
            self.transcript_drawer_selection = selection.strip()
            self.highlighted_quote_text = selection.strip()

    def clear_drawer_selection(self):
        """Clear the captured selection and its highlight."""
        self.transcript_drawer_selection = ""
        self.highlighted_quote_text = ""

    def confirm_drawer_evidence(self):
        """Map the selected transcript text as evidence using the existing save logic."""
        self.manual_quote_text = self.transcript_drawer_selection
        result = self.add_real_evidence(self.transcript_drawer_opportunity_id)
        if self.manual_quote_text == "":  # add_real_evidence clears it on success
            self.transcript_drawer_selection = ""
            self.transcript_drawer_open = False
            self.highlighted_quote_text = ""
        return result

    def close_transcript_drawer(self):
        """Close the transcript drawer."""
        self.transcript_drawer_open = False

    def cancel_synthesis_review(self):
        """Discard the pending synthesis results and return to the synthesize page."""
        self.pending_synthesis_transcript = ""
        self.pending_synthesis_persona = ""
        self.pending_synthesis_quality = 0
        self.pending_synthesis_feedback = ""
        self.pending_synthesis_memorable_quote = ""
        self.pending_synthesis_opps = []
        self.pending_llm_usages = []
        self.highlighted_quote_text = ""
        self.current_view = "synthesize"

    def confirm_synthesis(self):
        """Write the confirmed (selected) opportunities and interview to the database."""
        selected_opps = [opp for opp in self.pending_synthesis_opps if opp.selected]

        with rx.session() as session:
            # 1. Setup Persona
            persona = session.exec(
                select(Persona).where(Persona.name == self.pending_synthesis_persona)
            ).first()
            if not persona:
                persona = Persona(name=self.pending_synthesis_persona)
                session.add(persona)
                session.commit()
                session.refresh(persona)

            # 2. Create Interview (always stored, regardless of selected opps)
            interview = Interview(
                persona_id=persona.id,
                transcript=self.pending_synthesis_transcript,
                quality_score=self.pending_synthesis_quality,
                feedback=self.pending_synthesis_feedback,
                memorable_quote=self.pending_synthesis_memorable_quote,
                product_id=int(self.active_product_id),
            )
            session.add(interview)
            session.commit()
            session.refresh(interview)

            # 3. Persist LLM token usage now that we have an interview_id
            for usage in self.pending_llm_usages:
                session.add(LlmUsageLog(
                    model_name=usage.model_name,
                    operation=usage.operation,
                    interview_id=interview.id,
                    prompt_tokens=usage.prompt_tokens,
                    output_tokens=usage.output_tokens,
                    total_tokens=usage.total_tokens,
                ))
            session.commit()

            # 4. Process selected opportunities
            linked_master_opp_ids: set[int] = set()

            for opp_item in selected_opps:
                matched_id = opp_item.matched_existing_id

                if matched_id and matched_id > 0:
                    master_opp = session.get(Opportunity, matched_id)
                    if master_opp:
                        master_opp.date_last_validated = datetime.now(timezone.utc)
                        session.add(master_opp)
                        session.commit()
                    else:
                        # Existing opp was deleted in the meantime — create new
                        master_opp = Opportunity(
                            theme=opp_item.theme,
                            statement=opp_item.opportunity_statement,
                            product_id=int(self.active_product_id),
                        )
                        session.add(master_opp)
                        session.commit()
                        session.refresh(master_opp)
                else:
                    master_opp = Opportunity(
                        theme=opp_item.theme,
                        statement=opp_item.opportunity_statement,
                        product_id=int(self.active_product_id),
                    )
                    session.add(master_opp)
                    session.commit()
                    session.refresh(master_opp)

                if master_opp.id not in linked_master_opp_ids:
                    link = InterviewOpportunityLink(
                        interview_id=interview.id,
                        opportunity_id=master_opp.id,
                        source_quote=opp_item.source_quote,
                    )
                    session.add(link)
                    linked_master_opp_ids.add(master_opp.id)

            session.commit()

        # Clear pending state
        self.pending_synthesis_transcript = ""
        self.pending_synthesis_persona = ""
        self.pending_synthesis_quality = 0
        self.pending_synthesis_feedback = ""
        self.pending_synthesis_memorable_quote = ""
        self.pending_synthesis_opps = []
        self.pending_llm_usages = []
        self.highlighted_quote_text = ""

        self.load_ledger()
        self.load_history()
        self.current_view = "logs"

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
            prep_response = flash_model.generate_content(prep_prompt)
            generated_text = prep_response.text

            with rx.session() as session:
                session.add(LlmUsageLog(
                    model_name="gemini-2.5-flash",
                    operation="prep",
                    interview_id=None,
                    prompt_tokens=prep_response.usage_metadata.prompt_token_count,
                    output_tokens=prep_response.usage_metadata.candidates_token_count,
                    total_tokens=prep_response.usage_metadata.total_token_count,
                ))
                session.commit()
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

    def open_interview_detail(self, interview_id: int):
        """Loads the full interview transcript and its evidence snippets, then navigates to the detail view."""
        with rx.session() as session:
            interview = session.get(Interview, interview_id)
            if not interview:
                return
            persona = session.get(Persona, interview.persona_id)
            p_color = self._persona_color(persona.name)
            date_str = (
                interview.date_logged.strftime("%Y-%m-%d %H:%M")
                if interview.date_logged
                else "Unknown"
            )
            links = session.exec(
                select(InterviewOpportunityLink).where(
                    InterviewOpportunityLink.interview_id == interview_id
                )
            ).all()
            quotes: list[QuoteItem] = []
            for link in links:
                opp = session.get(Opportunity, link.opportunity_id)
                opp_statement = opp.statement if opp else ""
                quotes.append(
                    QuoteItem(
                        interview_id=interview_id,
                        persona_name=persona.name,
                        persona_color=p_color,
                        text=link.source_quote,
                        opportunity_statement=opp_statement,
                    )
                )

        self.selected_interview_id = interview_id
        self.interview_detail_persona = persona.name
        self.interview_detail_persona_color = p_color
        self.interview_detail_date = date_str
        self.interview_detail_transcript = interview.transcript
        self.interview_detail_quotes = quotes
        self.active_quote_index = 0
        self.highlighted_quote_text = quotes[0].text if quotes else ""
        self.current_view = "interview_detail"

    async def next_quote(self):
        if self.active_quote_index < len(self.interview_detail_quotes) - 1:
            self.active_quote_index += 1
            self.highlighted_quote_text = self.interview_detail_quotes[self.active_quote_index].text
            self.scroll_trigger += 1
            yield
            yield rx.call_script(_SCROLL_TO_MARK)

    async def prev_quote(self):
        if self.active_quote_index > 0:
            self.active_quote_index -= 1
            self.highlighted_quote_text = self.interview_detail_quotes[self.active_quote_index].text
            self.scroll_trigger += 1
            yield
            yield rx.call_script(_SCROLL_TO_MARK)

    def delete_current_interview(self):
        """Deletes the currently-viewed interview and navigates back to the list."""
        self.delete_interview(self.selected_interview_id)
        self.current_view = "logs"

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
