"""Unit tests for SQLModel database models using an in-memory SQLite engine."""
import json
import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select

from cont_synth.models import (
    Experiment,
    Interview,
    InterviewOpportunityLink,
    LlmUsageLog,
    Opportunity,
    Outcome,
    OutcomeOpportunityLink,
    Persona,
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
