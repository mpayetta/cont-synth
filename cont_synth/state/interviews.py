import io
import json
from datetime import datetime, timezone

import google.generativeai as genai
import PyPDF2
import docx
import reflex as rx
from sqlalchemy import func
from sqlmodel import select

from ..models import (
    Persona,
    Interview,
    Opportunity,
    InterviewOpportunityLink,
    LlmUsageLog,
    Participant,
    InterviewParticipantLink,
    Solution,
    Experiment,
)
from .core import (
    InterviewHistoryItem,
    QuoteItem,
    PersonaPrep,
    PendingOppItem,
    PendingLlmUsage,
    DetailParticipantItem,
    PrepOppItem,
    PrepExperimentItem,
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
                participants_str = ""
                if inv.participants:
                    try:
                        participants_str = ", ".join(json.loads(inv.participants))
                    except Exception:
                        participants_str = inv.participants
                history.append(
                    InterviewHistoryItem(
                        interview_id=inv.id,
                        persona=persona.name,
                        persona_color=self._persona_color(persona.name),
                        date_logged=date_str,
                        snippet=snippet,
                        interview_date=inv.interview_date or "",
                        duration_minutes=inv.duration_minutes or 0,
                        participants=participants_str,
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
        if not self.persona_input.strip() and not self.transcript_text.strip():
            self.synthesis_error = "Persona and transcript are required."
            return
        if not self.persona_input.strip():
            self.synthesis_error = "Persona is required."
            return
        if not self.transcript_text.strip():
            self.synthesis_error = "Transcript is required."
            return
        self.synthesis_error = ""

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

            # Extract optional metadata
            meta = result.get("metadata") or {}
            self.pending_synthesis_duration = meta.get("duration_minutes") or 0
            self.pending_synthesis_interview_date = meta.get("interview_date") or ""
            raw_names = meta.get("participant_names") or []
            raw_roles = meta.get("participant_roles") or []
            self.pending_synthesis_participants = raw_names
            self.pending_synthesis_participant_roles = [
                raw_roles[i] if i < len(raw_roles) else "interviewee"
                for i in range(len(raw_names))
            ]

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

    def set_participant_role(self, index: int, role: str):
        """Set a pending participant's role to 'interviewee' or 'interviewer'."""
        new_roles = list(self.pending_synthesis_participant_roles)
        while len(new_roles) <= index:
            new_roles.append("interviewee")
        new_roles[index] = role
        self.pending_synthesis_participant_roles = new_roles

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
        self.pending_synthesis_duration = 0
        self.pending_synthesis_interview_date = ""
        self.pending_synthesis_participants = []
        self.pending_synthesis_participant_roles = []
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
                duration_minutes=self.pending_synthesis_duration or None,
                interview_date=self.pending_synthesis_interview_date or None,
                participants=json.dumps(self.pending_synthesis_participants) if self.pending_synthesis_participants else None,
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

            # 3.5 Auto-create/link Participant records from LLM-extracted names
            roles = self.pending_synthesis_participant_roles
            for i, raw_name in enumerate(self.pending_synthesis_participants):
                name = raw_name.strip()
                if not name:
                    continue
                role = roles[i] if i < len(roles) else "interviewee"
                is_team = (role == "interviewer")

                existing_p = session.exec(
                    select(Participant).where(
                        func.lower(Participant.name) == name.lower()
                    )
                ).first()
                if existing_p:
                    participant = existing_p
                    # Only backfill persona_id for customers (not team members)
                    if not is_team and participant.persona_id is None:
                        participant.persona_id = persona.id
                        session.add(participant)
                        session.commit()
                    # If the participant was previously unknown, update their team status
                    if participant.is_team_member != is_team and not participant.is_team_member:
                        participant.is_team_member = is_team
                        session.add(participant)
                        session.commit()
                else:
                    # New participant — seed persona only for customers
                    participant = Participant(
                        name=name,
                        persona_id=persona.id if not is_team else None,
                        is_team_member=is_team,
                    )
                    session.add(participant)
                    session.commit()
                    session.refresh(participant)

                # Only link interviewees — team members are not the subjects of research
                if not is_team:
                    already_linked = session.exec(
                        select(InterviewParticipantLink).where(
                            InterviewParticipantLink.interview_id == interview.id,
                            InterviewParticipantLink.participant_id == participant.id,
                        )
                    ).first()
                    if not already_linked:
                        session.add(InterviewParticipantLink(
                            interview_id=interview.id,
                            participant_id=participant.id,
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
        self.pending_synthesis_duration = 0
        self.pending_synthesis_interview_date = ""
        self.pending_synthesis_participants = []
        self.pending_synthesis_participant_roles = []

        self.load_ledger()
        self.load_history()
        self.current_view = "logs"

    def load_prep_data(self):
        """Loads opportunities and running experiments for the prep page OST selectors."""
        with rx.session() as session:
            opps = session.exec(
                select(Opportunity).where(
                    Opportunity.product_id == int(self.active_product_id)
                )
            ).all()

            self.prep_opportunities = [
                PrepOppItem(id=o.id, theme=o.theme, statement=o.statement)
                for o in opps
            ]

            opp_ids = [o.id for o in opps]
            running_exps: list[PrepExperimentItem] = []

            if opp_ids:
                solutions = session.exec(
                    select(Solution).where(Solution.opportunity_id.in_(opp_ids))
                ).all()
                sol_by_id = {s.id: s for s in solutions}
                sol_to_opp = {s.id: s.opportunity_id for s in solutions}
                sol_ids = [s.id for s in solutions]

                if sol_ids:
                    experiments = session.exec(
                        select(Experiment).where(
                            Experiment.solution_id.in_(sol_ids),
                            Experiment.status == "Running",
                        )
                    ).all()
                    for exp in experiments:
                        sol = sol_by_id.get(exp.solution_id)
                        running_exps.append(
                            PrepExperimentItem(
                                id=exp.id,
                                opp_id=sol_to_opp.get(exp.solution_id, -1),
                                solution_name=sol.name if sol else "",
                                experiment_name=exp.name,
                                assumption=exp.assumption,
                            )
                        )

            self.prep_running_experiments = running_exps

    def toggle_prep_opportunity(self, opp_id: int):
        """Toggle selection of an opportunity in the prep page selector."""
        new_list = []
        was_selected = False
        for o in self.prep_opportunities:
            if o.id == opp_id:
                was_selected = o.selected
                new_list.append(
                    PrepOppItem(id=o.id, theme=o.theme, statement=o.statement, selected=not o.selected)
                )
            else:
                new_list.append(o)
        self.prep_opportunities = new_list
        # When deselecting an opportunity, also deselect its experiments
        if was_selected:
            self.prep_running_experiments = [
                PrepExperimentItem(
                    id=e.id,
                    opp_id=e.opp_id,
                    solution_name=e.solution_name,
                    experiment_name=e.experiment_name,
                    assumption=e.assumption,
                    selected=False if e.opp_id == opp_id else e.selected,
                )
                for e in self.prep_running_experiments
            ]

    def toggle_prep_experiment(self, exp_id: int):
        """Toggle selection of a running experiment in the prep page selector."""
        self.prep_running_experiments = [
            PrepExperimentItem(
                id=e.id,
                opp_id=e.opp_id,
                solution_name=e.solution_name,
                experiment_name=e.experiment_name,
                assumption=e.assumption,
                selected=not e.selected if e.id == exp_id else e.selected,
            )
            for e in self.prep_running_experiments
        ]

    def generate_hostile_questions(self):
        """Generates interview guide — OST-based if opportunities are selected, else persona battle plan."""
        has_persona = bool(getattr(self, "target_persona", ""))
        selected_opps = [o for o in self.prep_opportunities if o.selected]

        if not has_persona and not selected_opps:
            return rx.window_alert("Select at least one opportunity, or choose a persona to generate a guide.")

        self.is_prepping = True
        yield

        try:
            if selected_opps:
                # --- OST-based interview guide ---
                selected_exps = [e for e in self.prep_running_experiments if e.selected]

                opps_section = "\n".join(
                    f"- [{o.theme}] {o.statement}" for o in selected_opps
                )
                exps_section = (
                    "\n".join(
                        f"- Solution '{e.solution_name}' | Experiment '{e.experiment_name}' | Assumption: {e.assumption}"
                        for e in selected_exps
                    )
                    if selected_exps
                    else "None selected."
                )
                persona_context = (
                    f"The intended interviewee persona is '{self.target_persona}'."
                    if has_persona
                    else "No specific persona has been defined for this interview."
                )

                guide_template = load_prompt("interview_guide.txt")
                guide_prompt = guide_template.format(
                    persona_context=persona_context,
                    opportunities_section=opps_section,
                    assumptions_section=exps_section,
                )
                guide_response = flash_model.generate_content(guide_prompt)
                generated_text = guide_response.text

                with rx.session() as session:
                    session.add(LlmUsageLog(
                        model_name="gemini-2.5-flash",
                        operation="prep",
                        interview_id=None,
                        prompt_tokens=guide_response.usage_metadata.prompt_token_count,
                        output_tokens=guide_response.usage_metadata.candidates_token_count,
                        total_tokens=guide_response.usage_metadata.total_token_count,
                    ))
                    session.commit()

                self.prep_questions = generated_text
                self.prep_last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

            else:
                # --- Legacy persona-only battle plan ---
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

        participants_str = ""
        participant_items: list[DetailParticipantItem] = []
        if interview.participants:
            try:
                p_names = json.loads(interview.participants)
            except Exception:
                p_names = [interview.participants] if interview.participants else []
            participants_str = ", ".join(p_names)
            # Look up each name in the Participant table to get is_team_member status
            with rx.session() as p_session:
                for p_name in p_names:
                    p_rec = p_session.exec(
                        select(Participant).where(
                            func.lower(Participant.name) == p_name.lower()
                        )
                    ).first()
                    participant_items.append(DetailParticipantItem(
                        name=p_name,
                        is_team_member=p_rec.is_team_member if p_rec else False,
                    ))

        self.selected_interview_id = interview_id
        self.interview_detail_persona = persona.name
        self.interview_detail_persona_color = p_color
        self.interview_detail_date = date_str
        self.interview_detail_transcript = interview.transcript
        self.interview_detail_quotes = quotes
        self.active_quote_index = 0
        self.highlighted_quote_text = quotes[0].text if quotes else ""
        self.interview_detail_interview_date = interview.interview_date or ""
        self.interview_detail_duration = interview.duration_minutes or 0
        self.interview_detail_participants = participants_str
        self.interview_detail_participant_items = participant_items
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
        if not persona or persona == "— None —":
            self.target_persona = ""
            self.prep_questions = ""
            self.prep_last_updated = ""
            return

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
