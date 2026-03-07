import io
import json
import re
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
    InterviewFeedback,
    Opportunity,
    InterviewOpportunityLink,
    LlmUsageLog,
    Participant,
    InterviewParticipantLink,
)
from .core import (
    PendingOppItem,
    PendingLlmUsage,
    load_prompt,
    pro_model,
    flash_model,
)
from schema import InterviewSnapshot, DedupeResult

_TS_PATTERN = re.compile(r'\b\d+:\d{2}\b')
_TS_GROUP_PATTERN = re.compile(r'\s*\([^)]*\d+:\d{2}[^)]*\)')

_PHASE_MESSAGES = {
    "knowledge_base": [
        "Dusting off the knowledge base...",
        "Checking what we already know...",
        "Pulling up the opportunity map...",
    ],
    "workspace": [
        "Rummaging through your docs...",
        "Finding relevant context...",
        "Reading the room... and the files...",
    ],
    "extraction": [
        "Reading between the lines...",
        "Hunting for unmet needs...",
        "Listening carefully...",
        "Connecting the dots...",
        "What did they really mean?",
    ],
    "dedupe": [
        "Have we heard this before?",
        "Cross-referencing with the backlog...",
        "Checking for familiar complaints...",
        "Merging the déjà vu moments...",
    ],
    "coach": [
        "Reviewing your technique...",
        "Consulting the Mom Test...",
        "Grading your questions...",
    ],
}


def _load_existing_opps(product_id: int):
    """Blocking DB load of existing opportunities; safe to run in a thread."""
    with rx.session() as session:
        existing_opps = session.exec(
            select(Opportunity).where(Opportunity.product_id == product_id)
        ).all()
        return (
            {opp.id: opp.statement for opp in existing_opps},
            {opp.id: opp.theme for opp in existing_opps},
        )


def _parse_coach_items(raw: list[str]) -> list:
    """Split each raw coach string into clean text + scalar timestamp fields."""
    from .core import CoachDetailItem
    result = []
    for item in raw:
        timestamps = _TS_PATTERN.findall(item)
        clean = _TS_GROUP_PATTERN.sub('', item).strip()
        result.append(CoachDetailItem(
            text=clean,
            first_timestamp=timestamps[0] if timestamps else "",
            all_timestamps_str=", ".join(timestamps),
        ))
    return result


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


class InterviewSynthesisStateMixin(rx.State, mixin=True):
    """Interview upload, synthesis, and synthesis-review logic mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

    _PERSONA_COLORS = [
        "red",
        "amber",
        "green",
        "blue",
        "violet",
        "crimson",
    ]

    def _persona_color(self, name: str) -> str:
        idx = sum(ord(c) for c in name) % len(self._PERSONA_COLORS)
        return self._PERSONA_COLORS[idx]

    def _get_coach_history_context(self, product_id: int) -> str:
        """Fetch the last 3 InterviewFeedback records for coaching history context."""
        with rx.session() as session:
            past_interviews = session.exec(
                select(Interview)
                .where(Interview.product_id == product_id)
                .order_by(Interview.date_logged.desc())
                .limit(3)
            ).all()
            history = []
            for inv in reversed(past_interviews):  # chronological order
                fb = session.exec(
                    select(InterviewFeedback).where(InterviewFeedback.interview_id == inv.id)
                ).first()
                if fb:
                    history.append({
                        "date": inv.date_logged.strftime("%Y-%m-%d"),
                        "score": fb.score,
                        "keep_doing": json.loads(fb.keep_doing) if fb.keep_doing else [],
                        "stop_doing": json.loads(fb.stop_doing) if fb.stop_doing else [],
                    })
        if not history:
            return "No previous coaching history available."
        return json.dumps(history, indent=2)

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

    @rx.event(background=True)
    async def run_synthesis(self):
        """Runs synthesis as a non-blocking background task so the UI stays responsive."""
        if self.is_viewer:
            return
        import asyncio

        # --- Validate & capture inputs atomically ---
        async with self:
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
            self.synthesis_phase = "knowledge_base"
            self.synthesis_status = _PHASE_MESSAGES["knowledge_base"][0]
            transcript_text = self.transcript_text
            persona_input = self.persona_input
            active_product_id = int(self.active_product_id)

        # --- Inline cycling: updates message every 2s until stop_cycling is set ---
        stop_cycling = asyncio.Event()

        async def _cycle():
            phase_idx: dict[str, int] = {}
            while not stop_cycling.is_set():
                await asyncio.sleep(2)
                if stop_cycling.is_set():
                    break
                async with self:
                    phase = self.synthesis_phase
                    if phase in _PHASE_MESSAGES:
                        msgs = _PHASE_MESSAGES[phase]
                        idx = phase_idx.get(phase, 0) % len(msgs)
                        self.synthesis_status = msgs[idx]
                        phase_idx[phase] = idx + 1

        cycling_task = asyncio.create_task(_cycle())
        error_msg = None

        try:
            # --- Phase: knowledge_base ---
            existing_opps_dict, existing_opps_themes = await asyncio.to_thread(
                _load_existing_opps, active_product_id
            )
            existing_themes = sorted(set(existing_opps_themes.values())) if existing_opps_themes else []
            existing_themes_str = (
                ", ".join(existing_themes) if existing_themes else "None yet — create new themes as needed."
            )

            # --- Phase: workspace ---
            async with self:
                self.synthesis_phase = "workspace"
                self.synthesis_status = _PHASE_MESSAGES["workspace"][0]
            workspace_context = ""
            try:
                from ..kb_ingest import get_rag_context as _get_rag_context
                workspace_context = await asyncio.to_thread(
                    _get_rag_context, transcript_text, active_product_id
                )
            except Exception as rag_err:
                print(f"RAG context retrieval failed (non-fatal): {rag_err}")

            synthesis_prompt = load_prompt("synthesis.txt").format(existing_themes=existing_themes_str)
            if workspace_context:
                synthesis_prompt += "\n\n" + load_prompt("rag_context_block.txt").format(
                    workspace_context=workspace_context
                )

            # --- Phase: extraction ---
            async with self:
                self.synthesis_phase = "extraction"
                self.synthesis_status = _PHASE_MESSAGES["extraction"][0]
            response = await asyncio.to_thread(
                lambda: pro_model.generate_content(
                    f"{synthesis_prompt}\n\nTranscript:\n{transcript_text}",
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=InterviewSnapshot,
                    ),
                )
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
                # --- Phase: dedupe ---
                async with self:
                    self.synthesis_phase = "dedupe"
                    self.synthesis_status = _PHASE_MESSAGES["dedupe"][0]
                dedupe_prompt = load_prompt("dedupe.txt").format(
                    existing_opps_dict=existing_opps_dict,
                    new_opps_list=[o["opportunity_statement"] for o in new_opps],
                )
                dedupe_response = await asyncio.to_thread(
                    lambda: flash_model.generate_content(
                        dedupe_prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=DedupeResult,
                        ),
                    )
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
                        (o for o in new_opps if o["opportunity_statement"] == match["new_opportunity_statement"]),
                        None,
                    )
                    quote = original_opp["source_quote"] if original_opp else "No quote found."
                    matched_id = match.get("matched_existing_id")
                    matched_statement = existing_opps_dict.get(matched_id, "") if matched_id else ""
                    theme = existing_opps_themes.get(matched_id) if matched_id else None
                    if not theme:
                        theme = original_opp["theme"] if original_opp else "General"
                    matched_results.append(
                        {
                            "theme": theme,
                            "new_opportunity_statement": match["new_opportunity_statement"],
                            "matched_existing_id": matched_id,
                            "matched_existing_statement": matched_statement,
                            "quote": quote,
                        }
                    )

            # Build pending opp list
            pending_opps: list[PendingOppItem] = [
                PendingOppItem(
                    index=i,
                    opportunity_statement=item["new_opportunity_statement"],
                    theme=item["theme"],
                    source_quote=item["quote"],
                    matched_existing_id=item["matched_existing_id"] if item["matched_existing_id"] is not None else -1,
                    matched_existing_statement=item.get("matched_existing_statement", ""),
                    selected=True,
                )
                for i, item in enumerate(matched_results)
            ]

            # --- Phase: coach ---
            async with self:
                self.synthesis_phase = "coach"
                self.synthesis_status = _PHASE_MESSAGES["coach"][0]

            pending_coach_score = 0
            pending_coach_keep: list[str] = []
            pending_coach_stop: list[str] = []
            pending_coach_start: list[str] = []
            pending_coach_trend = ""
            try:
                history_ctx = await asyncio.to_thread(
                    lambda: self._get_coach_history_context(active_product_id)
                )
                coach_prompt = load_prompt("coach.txt").format(
                    history_context=history_ctx,
                    transcript=transcript_text,
                )
                coach_resp = await asyncio.to_thread(
                    lambda: flash_model.generate_content(
                        coach_prompt,
                        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
                    )
                )
                coach = json.loads(coach_resp.text)
                pending_usages.append(
                    PendingLlmUsage(
                        model_name="gemini-2.5-flash",
                        operation="coach",
                        prompt_tokens=coach_resp.usage_metadata.prompt_token_count,
                        output_tokens=coach_resp.usage_metadata.candidates_token_count,
                        total_tokens=coach_resp.usage_metadata.total_token_count,
                    )
                )
                pending_coach_score = coach.get("score", 0)
                pending_coach_keep = coach.get("keep_doing", [])
                pending_coach_stop = coach.get("stop_doing", [])
                pending_coach_start = coach.get("start_doing", [])
                pending_coach_trend = coach.get("trend_analysis", "")
            except Exception as coach_err:
                print(f"Coach feedback generation failed (non-fatal): {coach_err}")

            # --- Store all results & decide navigation ---
            meta = result.get("metadata") or {}
            raw_names = meta.get("participant_names") or []
            raw_roles = meta.get("participant_roles") or []
            async with self:
                on_synthesize = self.router.page.path == "/synthesize"
                self.pending_synthesis_transcript = transcript_text
                self.pending_synthesis_persona = persona_input
                self.pending_synthesis_quality = result.get("quality_check", {}).get("score", 0)
                self.pending_synthesis_feedback = result.get("quality_check", {}).get("feedback", "")
                self.pending_synthesis_memorable_quote = result.get("memorable_quote", "")
                self.pending_synthesis_opps = pending_opps
                self.pending_llm_usages = pending_usages
                self.highlighted_quote_text = pending_opps[0].source_quote if pending_opps else ""
                self.pending_synthesis_duration = meta.get("duration_minutes") or 0
                self.pending_synthesis_interview_date = meta.get("interview_date") or ""
                self.pending_synthesis_participants = raw_names
                self.pending_synthesis_participant_roles = [
                    raw_roles[i] if i < len(raw_roles) else "interviewee"
                    for i in range(len(raw_names))
                ]
                self.pending_coach_score = pending_coach_score
                self.pending_coach_keep = pending_coach_keep
                self.pending_coach_stop = pending_coach_stop
                self.pending_coach_start = pending_coach_start
                self.pending_coach_trend = pending_coach_trend
                self.transcript_text = ""
                self.persona_input = ""
                if not on_synthesize:
                    self.synthesis_ready = True

            if on_synthesize:
                return rx.redirect("/review")

        except Exception as e:  # pragma: no cover
            print(f"Engine Failure: {str(e)}")
            error_msg = str(e)
        finally:
            stop_cycling.set()
            await cycling_task
            async with self:
                self.is_processing = False
                self.synthesis_phase = ""
                self.synthesis_status = ""

        if error_msg:
            return rx.window_alert(f"Engine Failure: {error_msg}")

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
        self.pending_coach_score = 0
        self.pending_coach_keep = []
        self.pending_coach_stop = []
        self.pending_coach_start = []
        self.pending_coach_trend = ""
        return rx.redirect("/synthesize")

    def confirm_synthesis(self):
        """Write the confirmed (selected) opportunities and interview to the database."""
        if self.is_viewer:
            return
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
                created_by_user_id=self.auth_user_id,
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

            # 3.5 Save coach feedback
            if self.pending_coach_score > 0:
                session.add(InterviewFeedback(
                    interview_id=interview.id,
                    score=self.pending_coach_score,
                    keep_doing=json.dumps(self.pending_coach_keep),
                    stop_doing=json.dumps(self.pending_coach_stop),
                    start_doing=json.dumps(self.pending_coach_start),
                    trend_analysis=self.pending_coach_trend,
                ))
                session.commit()

            # 4. Auto-create/link Participant records from LLM-extracted names
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

            # 5. Process selected opportunities
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
                            created_by_user_id=self.auth_user_id,
                        )
                        session.add(master_opp)
                        session.commit()
                        session.refresh(master_opp)
                else:
                    master_opp = Opportunity(
                        theme=opp_item.theme,
                        statement=opp_item.opportunity_statement,
                        product_id=int(self.active_product_id),
                        created_by_user_id=self.auth_user_id,
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
        return rx.redirect("/interviews")
