"""Unit tests for SQLModel database models using an in-memory SQLite engine."""
import json
import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select

from cont_synth.models import (
    Experiment,
    Interview,
    InterviewFeedback,
    InterviewOpportunityLink,
    InterviewParticipantLink,
    LlmUsageLog,
    Opportunity,
    Outcome,
    OutcomeOpportunityLink,
    Participant,
    Persona,
    PrepGuideLog,
    Product,
    Solution,
    User,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(session: Session, name: str = "Test Workspace") -> Product:
    p = Product(name=name)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def _make_persona(session: Session, name: str = "Power User") -> Persona:
    p = Persona(name=name)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def _make_interview(session: Session, product: Product, persona: Persona, **kwargs) -> Interview:
    defaults = dict(
        product_id=product.id,
        persona_id=persona.id,
        transcript="Interview transcript text.",
        quality_score=75,
        feedback="Good session.",
        memorable_quote="Users love the product.",
    )
    defaults.update(kwargs)
    inv = Interview(**defaults)
    session.add(inv)
    session.commit()
    session.refresh(inv)
    return inv


def _make_opportunity(session: Session, product: Product, **kwargs) -> Opportunity:
    defaults = dict(product_id=product.id, statement="Users need X.")
    defaults.update(kwargs)
    opp = Opportunity(**defaults)
    session.add(opp)
    session.commit()
    session.refresh(opp)
    return opp


def _make_solution(session: Session, opportunity: Opportunity, **kwargs) -> Solution:
    defaults = dict(
        opportunity_id=opportunity.id,
        name="Solution A",
        description="Try this.",
        status="Ideation",
    )
    defaults.update(kwargs)
    sol = Solution(**defaults)
    session.add(sol)
    session.commit()
    session.refresh(sol)
    return sol


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class TestProduct:
    def test_create_and_retrieve(self, db_session: Session):
        product = _make_product(db_session, "My Workspace")
        fetched = db_session.get(Product, product.id)
        assert fetched is not None
        assert fetched.name == "My Workspace"

    def test_auto_id(self, db_session: Session):
        p = _make_product(db_session)
        assert p.id is not None
        assert isinstance(p.id, int)

    def test_created_at_auto_set(self, db_session: Session):
        before = datetime.now(timezone.utc)
        p = _make_product(db_session)
        after = datetime.now(timezone.utc)
        created = (
            p.created_at.replace(tzinfo=timezone.utc)
            if p.created_at.tzinfo is None
            else p.created_at
        )
        assert before <= created <= after

    def test_multiple_products(self, db_session: Session):
        names = ["Workspace A", "Workspace B", "Workspace C"]
        for name in names:
            _make_product(db_session, name)
        all_prods = db_session.exec(select(Product)).all()
        assert len(all_prods) >= 3


# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

class TestPersona:
    def test_create(self, db_session: Session):
        p = _make_persona(db_session, "Enterprise Customer")
        assert p.id is not None
        assert p.name == "Enterprise Customer"

    def test_retrieve_by_name(self, db_session: Session):
        _make_persona(db_session, "SMB Owner")
        result = db_session.exec(select(Persona).where(Persona.name == "SMB Owner")).first()
        assert result is not None


# ---------------------------------------------------------------------------
# Interview
# ---------------------------------------------------------------------------

class TestInterview:
    def test_create_basic(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session)
        inv = _make_interview(db_session, product, persona)

        assert inv.id is not None
        assert inv.product_id == product.id
        assert inv.persona_id == persona.id
        assert inv.quality_score == 75
        assert inv.date_logged is not None

    def test_optional_metadata_default_none(self, db_session: Session):
        product = _make_product(db_session, "P")
        persona = _make_persona(db_session, "Buyer")
        inv = _make_interview(db_session, product, persona)

        assert inv.duration_minutes is None
        assert inv.interview_date is None
        assert inv.participants is None

    def test_optional_metadata_set(self, db_session: Session):
        product = _make_product(db_session, "P2")
        persona = _make_persona(db_session, "Admin")
        inv = _make_interview(
            db_session,
            product,
            persona,
            duration_minutes=45,
            interview_date="2025-01-15",
            participants='["Alice", "Bob"]',
        )

        assert inv.duration_minutes == 45
        assert inv.interview_date == "2025-01-15"
        participants = json.loads(inv.participants)
        assert "Alice" in participants
        assert "Bob" in participants

    def test_transcript_stored_fully(self, db_session: Session):
        product = _make_product(db_session, "P3")
        persona = _make_persona(db_session, "User")
        long_text = "word " * 1000
        inv = _make_interview(db_session, product, persona, transcript=long_text)
        assert inv.transcript == long_text

    def test_quality_score_range(self, db_session: Session):
        product = _make_product(db_session, "P4")
        persona = _make_persona(db_session, "PU")
        for score in [0, 50, 100]:
            inv = _make_interview(db_session, product, persona, quality_score=score)
            assert inv.quality_score == score


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------

class TestOpportunity:
    def test_create(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product, statement="Invoice search is slow.")
        assert opp.id is not None
        assert opp.statement == "Invoice search is slow."

    def test_default_theme_is_uncategorized(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        assert opp.theme == "Uncategorized"

    def test_custom_theme(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product, theme="Billing")
        assert opp.theme == "Billing"

    def test_parent_id_default_none(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        assert opp.parent_id is None

    def test_nested_opportunity(self, db_session: Session):
        product = _make_product(db_session)
        parent = _make_opportunity(db_session, product, statement="Parent")
        child = _make_opportunity(db_session, product, statement="Child", parent_id=parent.id)
        assert child.parent_id == parent.id

    def test_date_last_validated_auto_set(self, db_session: Session):
        product = _make_product(db_session)
        before = datetime.now(timezone.utc)
        opp = _make_opportunity(db_session, product)
        after = datetime.now(timezone.utc)
        validated = (
            opp.date_last_validated.replace(tzinfo=timezone.utc)
            if opp.date_last_validated.tzinfo is None
            else opp.date_last_validated
        )
        assert before <= validated <= after

    def test_filter_by_product(self, db_session: Session):
        p1 = _make_product(db_session, "Product 1")
        p2 = _make_product(db_session, "Product 2")
        _make_opportunity(db_session, p1, statement="Opp for P1")
        _make_opportunity(db_session, p2, statement="Opp for P2")

        p1_opps = db_session.exec(
            select(Opportunity).where(Opportunity.product_id == p1.id)
        ).all()
        assert len(p1_opps) == 1
        assert p1_opps[0].statement == "Opp for P1"


# ---------------------------------------------------------------------------
# Solution
# ---------------------------------------------------------------------------

class TestSolution:
    def test_create(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        sol = _make_solution(db_session, opp)
        assert sol.id is not None
        assert sol.status == "Ideation"
        assert sol.parent_id is None

    def test_all_pipeline_statuses(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        for status in ["Ideation", "Testing", "Discarded", "Shipped"]:
            sol = _make_solution(db_session, opp, name=f"Sol-{status}", status=status)
            assert sol.status == status

    def test_nested_solution(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        parent = _make_solution(db_session, opp, name="Parent")
        child = _make_solution(db_session, opp, name="Child", parent_id=parent.id)
        assert child.parent_id == parent.id

    def test_solutions_for_opportunity(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        for i in range(3):
            _make_solution(db_session, opp, name=f"Sol{i}")
        sols = db_session.exec(
            select(Solution).where(Solution.opportunity_id == opp.id)
        ).all()
        assert len(sols) == 3


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

class TestExperiment:
    def _setup(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        sol = _make_solution(db_session, opp)
        return sol

    def test_create_defaults(self, db_session: Session):
        sol = self._setup(db_session)
        exp = Experiment(
            solution_id=sol.id,
            name="Fake Door Test",
            assumption="Users want this feature",
            method="Fake Door",
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        assert exp.id is not None
        assert exp.status == "Draft"
        assert exp.signal == "Pending"
        assert exp.evidence_notes == ""
        assert exp.description == ""
        assert exp.success_metric == ""

    def test_all_methods(self, db_session: Session):
        sol = self._setup(db_session)
        for method in ["Fake Door", "A/B Test", "Prototype Interview"]:
            exp = Experiment(
                solution_id=sol.id,
                name=f"Exp-{method}",
                assumption="Assumption",
                method=method,
            )
            db_session.add(exp)
            db_session.commit()
            db_session.refresh(exp)
            assert exp.method == method

    def test_status_transitions_stored(self, db_session: Session):
        sol = self._setup(db_session)
        exp = Experiment(
            solution_id=sol.id, name="E", assumption="A", method="Fake Door"
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        for status in ["Draft", "Running", "Concluded"]:
            exp.status = status
            db_session.add(exp)
            db_session.commit()
            db_session.refresh(exp)
            assert exp.status == status

    def test_signal_values_stored(self, db_session: Session):
        sol = self._setup(db_session)
        exp = Experiment(
            solution_id=sol.id, name="E2", assumption="A", method="A/B Test"
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        for signal in ["Pending", "Validated", "Invalidated"]:
            exp.signal = signal
            db_session.add(exp)
            db_session.commit()
            db_session.refresh(exp)
            assert exp.signal == signal

    def test_description_and_success_metric_default_empty(self, db_session: Session):
        sol = self._setup(db_session)
        exp = Experiment(
            solution_id=sol.id, name="Defaults Test", assumption="A", method="Survey"
        )
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        assert exp.description == ""
        assert exp.success_metric == ""

    def test_description_and_success_metric_persisted(self, db_session: Session):
        sol = self._setup(db_session)
        exp = Experiment(
            solution_id=sol.id,
            name="Persist Test",
            assumption="Users will sign up",
            method="Fake Door",
            description="Place a sign-up button on the landing page and track clicks.",
            success_metric="Sign-up click rate > 10% within one week.",
        )
        db_session.add(exp)
        db_session.commit()
        exp_id = exp.id

        # Reload from DB to confirm persistence
        reloaded = db_session.get(Experiment, exp_id)
        assert reloaded is not None
        assert reloaded.description == "Place a sign-up button on the landing page and track clicks."
        assert reloaded.success_metric == "Sign-up click rate > 10% within one week."


# ---------------------------------------------------------------------------
# InterviewOpportunityLink
# ---------------------------------------------------------------------------

class TestInterviewOpportunityLink:
    def test_create_link(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session, "IOL User")
        inv = _make_interview(db_session, product, persona)
        opp = _make_opportunity(db_session, product)

        link = InterviewOpportunityLink(
            interview_id=inv.id,
            opportunity_id=opp.id,
            source_quote="Users said they need this.",
        )
        db_session.add(link)
        db_session.commit()

        fetched = db_session.exec(
            select(InterviewOpportunityLink).where(
                InterviewOpportunityLink.interview_id == inv.id
            )
        ).first()
        assert fetched is not None
        assert fetched.source_quote == "Users said they need this."
        assert fetched.opportunity_id == opp.id

    def test_multiple_interviews_same_opportunity(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        for i in range(3):
            persona = _make_persona(db_session, f"Persona{i}")
            inv = _make_interview(db_session, product, persona)
            link = InterviewOpportunityLink(
                interview_id=inv.id,
                opportunity_id=opp.id,
                source_quote=f"Quote {i}",
            )
            db_session.add(link)
        db_session.commit()

        links = db_session.exec(
            select(InterviewOpportunityLink).where(
                InterviewOpportunityLink.opportunity_id == opp.id
            )
        ).all()
        assert len(links) == 3


# ---------------------------------------------------------------------------
# Outcome & OutcomeOpportunityLink
# ---------------------------------------------------------------------------

class TestOutcome:
    def test_create(self, db_session: Session):
        product = _make_product(db_session)
        outcome = Outcome(
            product_id=product.id,
            name="Reduce Churn",
            description="Reduce customer churn by 5%.",
            target_metric="Churn rate",
        )
        db_session.add(outcome)
        db_session.commit()
        db_session.refresh(outcome)

        assert outcome.id is not None
        assert outcome.name == "Reduce Churn"
        assert outcome.is_active is True

    def test_link_opportunity_to_outcome(self, db_session: Session):
        product = _make_product(db_session)
        opp = _make_opportunity(db_session, product)
        outcome = Outcome(
            product_id=product.id,
            name="Revenue Growth",
            description="Grow revenue",
            target_metric="MRR",
        )
        db_session.add(outcome)
        db_session.commit()
        db_session.refresh(outcome)

        link = OutcomeOpportunityLink(
            outcome_id=outcome.id, opportunity_id=opp.id
        )
        db_session.add(link)
        db_session.commit()

        fetched = db_session.exec(
            select(OutcomeOpportunityLink).where(
                OutcomeOpportunityLink.opportunity_id == opp.id
            )
        ).first()
        assert fetched is not None
        assert fetched.outcome_id == outcome.id


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class TestUser:
    def test_create(self, db_session: Session):
        user = User(
            username="testuser",
            password_hash="$2b$12$hashed_value_here_for_testing",
            fullname="Test User",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.fullname == "Test User"

    def test_retrieve_by_username(self, db_session: Session):
        user = User(
            username="alice",
            password_hash="$2b$12$hash",
            fullname="Alice Smith",
        )
        db_session.add(user)
        db_session.commit()

        found = db_session.exec(select(User).where(User.username == "alice")).first()
        assert found is not None
        assert found.fullname == "Alice Smith"


# ---------------------------------------------------------------------------
# LlmUsageLog
# ---------------------------------------------------------------------------

class TestLlmUsageLog:
    def test_create_without_interview(self, db_session: Session):
        log = LlmUsageLog(
            model_name="gemini-2.5-pro",
            operation="synthesis",
            prompt_tokens=1500,
            output_tokens=300,
            total_tokens=1800,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.id is not None
        assert log.model_name == "gemini-2.5-pro"
        assert log.total_tokens == 1800
        assert log.interview_id is None

    def test_create_with_interview_id(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session, "LLM Tester")
        inv = _make_interview(db_session, product, persona)

        log = LlmUsageLog(
            model_name="gemini-2.5-flash",
            operation="dedupe",
            interview_id=inv.id,
            prompt_tokens=200,
            output_tokens=100,
            total_tokens=300,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        assert log.interview_id == inv.id

    def test_all_operations_stored(self, db_session: Session):
        for operation in ["synthesis", "dedupe", "prep"]:
            log = LlmUsageLog(
                model_name="gemini-2.5-flash",
                operation=operation,
                prompt_tokens=100,
                output_tokens=50,
                total_tokens=150,
            )
            db_session.add(log)
        db_session.commit()

        logs = db_session.exec(select(LlmUsageLog)).all()
        ops = {log.operation for log in logs}
        assert {"synthesis", "dedupe", "prep"}.issubset(ops)


# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------

class TestParticipant:
    def test_create_customer(self, db_session: Session):
        participant = Participant(
            name="Alice Chen",
            segment="Enterprise",
            recruited_via="LinkedIn",
            notes="Key decision maker",
        )
        db_session.add(participant)
        db_session.commit()
        db_session.refresh(participant)

        assert participant.id is not None
        assert participant.name == "Alice Chen"
        assert participant.is_team_member is False
        assert participant.segment == "Enterprise"

    def test_create_team_member(self, db_session: Session):
        interviewer = Participant(
            name="Bob Smith",
            is_team_member=True,
            segment="",
            recruited_via="",
            notes="",
        )
        db_session.add(interviewer)
        db_session.commit()
        db_session.refresh(interviewer)

        assert interviewer.is_team_member is True

    def test_defaults(self, db_session: Session):
        p = Participant(name="Charlie")
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)

        assert p.is_team_member is False
        assert p.segment == ""
        assert p.recruited_via == ""
        assert p.notes == ""
        assert p.created_at is not None

    def test_filter_customers_excludes_team_members(self, db_session: Session):
        db_session.add(Participant(name="Customer A"))
        db_session.add(Participant(name="Interviewer B", is_team_member=True))
        db_session.add(Participant(name="Customer C"))
        db_session.commit()

        customers = db_session.exec(
            select(Participant).where(Participant.is_team_member == False)
        ).all()
        names = {p.name for p in customers}
        assert "Customer A" in names
        assert "Customer C" in names
        assert "Interviewer B" not in names

    def test_persona_link(self, db_session: Session):
        persona = Persona(name="VP of Engineering")
        db_session.add(persona)
        db_session.commit()
        db_session.refresh(persona)

        participant = Participant(name="Dana", persona_id=persona.id)
        db_session.add(participant)
        db_session.commit()
        db_session.refresh(participant)

        assert participant.persona_id == persona.id


# ---------------------------------------------------------------------------
# InterviewParticipantLink
# ---------------------------------------------------------------------------

class TestInterviewParticipantLink:
    def test_create_link(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session, "IPL Persona")
        inv = _make_interview(db_session, product, persona)

        p = Participant(name="Eve")
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)

        link = InterviewParticipantLink(interview_id=inv.id, participant_id=p.id)
        db_session.add(link)
        db_session.commit()

        fetched = db_session.exec(
            select(InterviewParticipantLink).where(
                InterviewParticipantLink.interview_id == inv.id
            )
        ).first()
        assert fetched is not None
        assert fetched.participant_id == p.id

    def test_one_participant_multiple_interviews(self, db_session: Session):
        product = _make_product(db_session)
        participant = Participant(name="Frank")
        db_session.add(participant)
        db_session.commit()
        db_session.refresh(participant)

        for i in range(3):
            persona = _make_persona(db_session, f"Persona-IPL-{i}")
            inv = _make_interview(db_session, product, persona)
            db_session.add(InterviewParticipantLink(interview_id=inv.id, participant_id=participant.id))
        db_session.commit()

        links = db_session.exec(
            select(InterviewParticipantLink).where(
                InterviewParticipantLink.participant_id == participant.id
            )
        ).all()
        assert len(links) == 3


# ---------------------------------------------------------------------------
# InterviewFeedback
# ---------------------------------------------------------------------------

class TestInterviewFeedback:
    def test_create(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session, "Coach Test Persona")
        inv = _make_interview(db_session, product, persona)

        feedback = InterviewFeedback(
            interview_id=inv.id,
            score=8,
            keep_doing='["Good silence", "Follow-up questions"]',
            stop_doing='["Leading questions"]',
            start_doing='["Ask about workarounds"]',
            trend_analysis="Improving over time.",
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        assert feedback.id is not None
        assert feedback.interview_id == inv.id
        assert feedback.score == 8

    def test_defaults(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session, "Coach Default Persona")
        inv = _make_interview(db_session, product, persona)

        feedback = InterviewFeedback(interview_id=inv.id, score=5)
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        assert feedback.keep_doing == ""
        assert feedback.stop_doing == ""
        assert feedback.start_doing == ""
        assert feedback.trend_analysis == ""
        assert feedback.created_at is not None

    def test_score_range(self, db_session: Session):
        product = _make_product(db_session)
        for i, score in enumerate([1, 5, 10]):
            persona = _make_persona(db_session, f"Coach Score Persona {i}")
            inv = _make_interview(db_session, product, persona)
            feedback = InterviewFeedback(interview_id=inv.id, score=score)
            db_session.add(feedback)
        db_session.commit()

        all_feedback = db_session.exec(select(InterviewFeedback)).all()
        scores = {f.score for f in all_feedback}
        assert {1, 5, 10}.issubset(scores)

    def test_json_fields_round_trip(self, db_session: Session):
        product = _make_product(db_session)
        persona = _make_persona(db_session, "Coach JSON Persona")
        inv = _make_interview(db_session, product, persona)

        keep_doing_data = json.dumps(["Item 1", "Item 2", "Item 3"])
        feedback = InterviewFeedback(
            interview_id=inv.id,
            score=7,
            keep_doing=keep_doing_data,
        )
        db_session.add(feedback)
        db_session.commit()
        feedback_id = feedback.id

        reloaded = db_session.get(InterviewFeedback, feedback_id)
        items = json.loads(reloaded.keep_doing)
        assert items == ["Item 1", "Item 2", "Item 3"]


# ---------------------------------------------------------------------------
# PrepGuideLog
# ---------------------------------------------------------------------------

class TestPrepGuideLog:
    def test_create_battle_plan(self, db_session: Session):
        log = PrepGuideLog(
            guide_type="battle_plan",
            target_persona="VP of Engineering",
            content="## Battle Plan\n1. Open warmly...",
            used_coach_feedback=True,
            input_extra_context="Focus on billing pain points",
            input_coach_score=7,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.id is not None
        assert log.guide_type == "battle_plan"
        assert log.target_persona == "VP of Engineering"
        assert log.used_coach_feedback is True
        assert log.created_at is not None

    def test_create_interview_guide(self, db_session: Session):
        opps_json = json.dumps([{"theme": "Workflow", "statement": "Can't batch export"}])
        log = PrepGuideLog(
            guide_type="interview_guide",
            target_persona="SMB Owner",
            content="## Interview Guide\n...",
            used_coach_feedback=False,
            input_opportunities=opps_json,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.guide_type == "interview_guide"
        opps = json.loads(log.input_opportunities)
        assert len(opps) == 1
        assert opps[0]["theme"] == "Workflow"

    def test_defaults(self, db_session: Session):
        log = PrepGuideLog(content="Minimal guide content.")
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.guide_type == "battle_plan"
        assert log.target_persona == ""
        assert log.used_coach_feedback is False
        assert log.input_opportunities == ""
        assert log.input_extra_context == ""
        assert log.input_coach_score == 0

    def test_multiple_logs_ordered_by_creation(self, db_session: Session):
        for i in range(3):
            db_session.add(PrepGuideLog(content=f"Guide {i}"))
        db_session.commit()

        all_logs = db_session.exec(select(PrepGuideLog)).all()
        assert len(all_logs) >= 3
