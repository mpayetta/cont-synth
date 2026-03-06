import json
from datetime import datetime

import google.generativeai as genai
import reflex as rx
from sqlalchemy import func
from sqlmodel import select

from ..models import (
    Persona,
    Interview,
    InterviewFeedback,
    PrepGuideLog,
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
    DetailParticipantItem,
    PrepOppItem,
    PrepExperimentItem,
    PrepGuideItem,
    CoachDetailItem,
    load_prompt,
    flash_model,
)
from .synthesis import _SCROLL_TO_MARK, _parse_coach_items


class InterviewPrepStateMixin(rx.State, mixin=True):
    """Interview history, prep guide generation, and interview detail logic mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

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

            # Phase 1: delete all rows that FK-reference this interview.
            # Committed before touching the interview row so the DB never sees
            # a state where the parent is gone but children still reference it.
            for link in links:
                session.delete(link)
            for fb in session.exec(
                select(InterviewFeedback).where(InterviewFeedback.interview_id == interview_id)
            ).all():
                session.delete(fb)
            for log in session.exec(
                select(LlmUsageLog).where(LlmUsageLog.interview_id == interview_id)
            ).all():
                session.delete(log)
            for ipl in session.exec(
                select(InterviewParticipantLink).where(InterviewParticipantLink.interview_id == interview_id)
            ).all():
                session.delete(ipl)
            session.commit()

            # Phase 2: delete the interview row itself.
            interview = session.get(Interview, interview_id)
            if interview:
                session.delete(interview)
            session.commit()

            # Phase 3: clean up opportunities that are now evidence-less.
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

    def load_prep_data(self):
        """Loads opportunities and running experiments for the prep page OST selectors."""
        with rx.session() as session:
            opps = session.exec(
                select(Opportunity).where(
                    Opportunity.product_id == int(self.active_product_id)
                )
            ).all()

            # Build opp_id → persona names mapping via InterviewOpportunityLink → Interview → Persona
            opp_ids = [o.id for o in opps]
            opp_personas: dict[int, list[str]] = {o.id: [] for o in opps}
            if opp_ids:
                links = session.exec(
                    select(InterviewOpportunityLink).where(
                        InterviewOpportunityLink.opportunity_id.in_(opp_ids)
                    )
                ).all()
                interview_ids = list({lnk.interview_id for lnk in links})
                if interview_ids:
                    interviews = session.exec(
                        select(Interview).where(Interview.id.in_(interview_ids))
                    ).all()
                    persona_ids = list({iv.persona_id for iv in interviews})
                    personas = session.exec(
                        select(Persona).where(Persona.id.in_(persona_ids))
                    ).all()
                    persona_map = {p.id: p.name for p in personas}
                    interview_map = {iv.id: iv.persona_id for iv in interviews}
                    for lnk in links:
                        p_id = interview_map.get(lnk.interview_id)
                        p_name = persona_map.get(p_id, "") if p_id else ""
                        if p_name and p_name not in opp_personas[lnk.opportunity_id]:
                            opp_personas[lnk.opportunity_id].append(p_name)

            self.prep_opportunities = [
                PrepOppItem(id=o.id, theme=o.theme, statement=o.statement, personas=opp_personas[o.id])
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

    def load_coach_feedback_for_prep(self):
        """Fetches the most recent InterviewFeedback to surface in the pre-game brief."""
        with rx.session() as session:
            latest_fb = session.exec(
                select(InterviewFeedback)
                .order_by(InterviewFeedback.created_at.desc())
                .limit(1)
            ).first()
        if latest_fb:
            self.last_interview_score = latest_fb.score
            self.last_stop_doing = json.loads(latest_fb.stop_doing) if latest_fb.stop_doing else []
        else:
            self.last_interview_score = 0
            self.last_stop_doing = []

    def load_guide_history(self):
        """Fetches all PrepGuideLog records ordered newest-first."""
        with rx.session() as session:
            rows = session.exec(
                select(PrepGuideLog).order_by(PrepGuideLog.created_at.desc())
            ).all()
        self.guide_history = [
            PrepGuideItem(
                id=r.id,
                created_at=r.created_at.strftime("%Y-%m-%d %H:%M"),
                guide_type=r.guide_type,
                target_persona=r.target_persona,
                content=r.content,
                used_coach_feedback=r.used_coach_feedback,
                input_opportunities=json.loads(r.input_opportunities) if r.input_opportunities else [],
                input_extra_context=r.input_extra_context,
                input_coach_score=r.input_coach_score,
                input_stop_doing=json.loads(r.input_stop_doing) if r.input_stop_doing else [],
            )
            for r in rows
        ]

    def toggle_prep_opportunity(self, opp_id: int):
        """Toggle selection of an opportunity in the prep page selector."""
        new_list = []
        was_selected = False
        for o in self.prep_opportunities:
            if o.id == opp_id:
                was_selected = o.selected
                new_list.append(
                    PrepOppItem(id=o.id, theme=o.theme, statement=o.statement, selected=not o.selected, personas=o.personas)
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
        has_extra_context = bool(self.prep_extra_context.strip())

        if not has_persona and not selected_opps and not has_extra_context:
            return rx.window_alert("Select at least one opportunity, add extra context, or choose a persona to generate a guide.")

        self.is_prepping = True
        yield

        try:
            # --- RAG: retrieve workspace context keyed on persona + selected opportunities ---
            workspace_context_block = ""
            try:
                from ..kb_ingest import get_prep_rag_context
                opp_texts = [o.statement for o in selected_opps]
                rag_query = " ".join(filter(None, [self.target_persona] + opp_texts))
                raw_context = get_prep_rag_context(rag_query, int(self.active_product_id))
                if raw_context:
                    workspace_context_block = load_prompt("rag_context_block.txt").format(
                        workspace_context=raw_context
                    ) + "\n"
            except Exception as rag_err:
                print(f"Prep RAG context retrieval failed (non-fatal): {rag_err}")

            if selected_opps:
                # --- OST-based interview guide: only when opportunities are explicitly selected ---
                selected_exps = [e for e in self.prep_running_experiments if e.selected]

                opps_section = "\n".join(f"- [{o.theme}] {o.statement}" for o in selected_opps)
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
                extra_context = (
                    f"ADDITIONAL CONTEXT FROM THE INTERVIEWER:\n{self.prep_extra_context.strip()}\n"
                    if has_extra_context
                    else ""
                )

                guide_template = load_prompt("interview_guide.txt")
                guide_prompt = guide_template.format(
                    workspace_context=workspace_context_block,
                    persona_context=persona_context,
                    extra_context=extra_context,
                    opportunities_section=opps_section,
                    assumptions_section=exps_section,
                )
                print(workspace_context_block)
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
                    session.add(PrepGuideLog(
                        guide_type="interview_guide",
                        target_persona=self.target_persona,
                        content=generated_text,
                        used_coach_feedback=False,
                        input_opportunities=json.dumps([
                            {"theme": o.theme, "statement": o.statement} for o in selected_opps
                        ]),
                        input_extra_context=self.prep_extra_context.strip(),
                        input_coach_score=0,
                        input_stop_doing="[]",
                    ))
                    session.commit()

                self.prep_questions = generated_text
                self.prep_last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.load_guide_history()

            else:
                # --- Persona battle plan: no opportunities selected; extra context is passed as additional direction ---
                target_opps: list[str] = []
                for item in getattr(self, "ledger_data", []):
                    if any(p.name == self.target_persona for p in item.personas_affected):
                        target_opps.append(item.opportunity)

                # If no prior opps exist for this persona, use extra context as the only direction
                if not target_opps and not has_extra_context:
                    self.prep_questions = "No identified opportunities for this persona. Add some via synthesis first, or provide additional context."
                    self.prep_last_updated = ""
                    return

                use_coaching = self.apply_coach_feedback and bool(self.last_stop_doing)
                if use_coaching:
                    stop_list = "\n".join(f"- {item}" for item in self.last_stop_doing)
                    coaching_guardrails = (
                        f"### 🛑 Coach's Guardrails:\n\n"
                        f"Based on your last interview (score: {self.last_interview_score}/10), "
                        f"you must actively avoid these habits during this conversation:\n{stop_list}"
                    )
                else:
                    coaching_guardrails = (
                        "### 🛑 Coach's Guardrails:\n\n"
                        "No prior coaching data available. General reminder: do not lead the witness, "
                        "avoid hypotheticals, and let silence do the work — resist filling pauses."
                    )

                extra_direction = (
                    f"\nADDITIONAL DIRECTION FROM INTERVIEWER:\n{self.prep_extra_context.strip()}"
                    if has_extra_context
                    else ""
                )

                prep_template = load_prompt("prep.txt")
                prep_prompt = prep_template.format(
                    workspace_context=workspace_context_block,
                    target_persona=self.target_persona,
                    target_opps=target_opps if target_opps else ["(No prior opportunities — use the additional direction below as the focus)"],
                    coaching_guardrails=coaching_guardrails,
                    extra_direction=extra_direction,
                )
                print(workspace_context_block)
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
                    session.add(PrepGuideLog(
                        guide_type="battle_plan",
                        target_persona=self.target_persona,
                        content=generated_text,
                        used_coach_feedback=use_coaching,
                        input_opportunities=json.dumps([
                            {"theme": "", "statement": o} for o in target_opps
                        ]),
                        input_extra_context=self.prep_extra_context.strip(),
                        input_coach_score=self.last_interview_score if use_coaching else 0,
                        input_stop_doing=json.dumps(self.last_stop_doing) if use_coaching else "[]",
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
                self.load_guide_history()

        except Exception as e:  # pragma: no cover - UI alert path
            self.prep_questions = f"Failed to generate: {str(e)}"
        finally:
            self.is_prepping = False

    def open_interview_detail(self, interview_id: int):
        """Navigate to the interview detail page via URL routing."""
        self.selected_interview_id = interview_id
        return rx.redirect(f"/interviews/{interview_id}")

    def load_interview_detail_data(self):
        """Loads the full interview transcript and evidence snippets from self.selected_interview_id."""
        interview_id = self.selected_interview_id
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
        self.interview_detail_quality = interview.quality_score

        # Load coach feedback
        with rx.session() as fb_session:
            fb = fb_session.exec(
                select(InterviewFeedback).where(InterviewFeedback.interview_id == interview_id)
            ).first()
        if fb:
            self.interview_detail_coach_score = fb.score
            self.interview_detail_coach_keep = _parse_coach_items(json.loads(fb.keep_doing) if fb.keep_doing else [])
            self.interview_detail_coach_stop = _parse_coach_items(json.loads(fb.stop_doing) if fb.stop_doing else [])
            self.interview_detail_coach_start = _parse_coach_items(json.loads(fb.start_doing) if fb.start_doing else [])
            self.interview_detail_coach_trend = fb.trend_analysis or ""
        else:
            self.interview_detail_coach_score = 0
            self.interview_detail_coach_keep = []
            self.interview_detail_coach_stop = []
            self.interview_detail_coach_start = []
            self.interview_detail_coach_trend = ""

    async def generate_coach_feedback(self):
        """Generate (or regenerate) coach feedback for the currently viewed interview."""
        interview_id = self.selected_interview_id
        transcript = self.interview_detail_transcript
        if not transcript or not interview_id:
            return

        self.is_generating_coach = True
        yield

        try:
            history_ctx = self._get_coach_history_context(int(self.active_product_id))
            coach_prompt = load_prompt("coach.txt").format(
                history_context=history_ctx,
                transcript=transcript,
            )
            coach_resp = flash_model.generate_content(
                coach_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )
            coach = json.loads(coach_resp.text)

            with rx.session() as session:
                # Upsert: update existing record if it exists
                existing = session.exec(
                    select(InterviewFeedback).where(InterviewFeedback.interview_id == interview_id)
                ).first()
                if existing:
                    existing.score = coach.get("score", 0)
                    existing.keep_doing = json.dumps(coach.get("keep_doing", []))
                    existing.stop_doing = json.dumps(coach.get("stop_doing", []))
                    existing.start_doing = json.dumps(coach.get("start_doing", []))
                    existing.trend_analysis = coach.get("trend_analysis", "")
                    session.add(existing)
                else:
                    session.add(InterviewFeedback(
                        interview_id=interview_id,
                        score=coach.get("score", 0),
                        keep_doing=json.dumps(coach.get("keep_doing", [])),
                        stop_doing=json.dumps(coach.get("stop_doing", [])),
                        start_doing=json.dumps(coach.get("start_doing", [])),
                        trend_analysis=coach.get("trend_analysis", ""),
                    ))
                session.add(LlmUsageLog(
                    model_name="gemini-2.5-flash",
                    operation="coach",
                    interview_id=interview_id,
                    prompt_tokens=coach_resp.usage_metadata.prompt_token_count,
                    output_tokens=coach_resp.usage_metadata.candidates_token_count,
                    total_tokens=coach_resp.usage_metadata.total_token_count,
                ))
                session.commit()

            # Reload coach fields into detail state
            self.interview_detail_coach_score = coach.get("score", 0)
            self.interview_detail_coach_keep = _parse_coach_items(coach.get("keep_doing", []))
            self.interview_detail_coach_stop = _parse_coach_items(coach.get("stop_doing", []))
            self.interview_detail_coach_start = _parse_coach_items(coach.get("start_doing", []))
            self.interview_detail_coach_trend = coach.get("trend_analysis", "")

        except Exception as e:
            print(f"generate_coach_feedback failed: {e}")
            yield rx.window_alert(f"Coach feedback generation failed: {e}")
        finally:
            self.is_generating_coach = False

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
        return rx.redirect("/interviews")

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
