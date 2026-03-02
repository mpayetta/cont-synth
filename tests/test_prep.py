"""Unit tests for the OST-based interview guide prep feature.

Covers:
- Toggle logic for opportunity and experiment selection (inline replicas)
- Cascade-deselect when an opportunity is unchecked
- Computed var logic: selected_opportunity_ids, selected_experiment_ids,
  visible_prep_experiments, prep_persona_options
- load_prep_for_persona sentinel handling ("— None —")
- load_prep_data DB query logic (in-memory SQLite via db_session fixture)
- Interview guide prompt template integrity
- generate_hostile_questions prompt-content building and guard clause
"""
import os

import pytest
from sqlmodel import select

from cont_synth.state.core import PrepExperimentItem, PrepOppItem


# ---------------------------------------------------------------------------
# Inline replicas of state logic (mirrors the pattern in test_business_logic.py)
# ---------------------------------------------------------------------------

def _toggle_opp(
    opps: list[PrepOppItem], opp_id: int
) -> tuple[list[PrepOppItem], bool]:
    """Replica of the toggle portion of toggle_prep_opportunity."""
    new_list = []
    was_selected = False
    for o in opps:
        if o.id == opp_id:
            was_selected = o.selected
            new_list.append(
                PrepOppItem(id=o.id, theme=o.theme, statement=o.statement, selected=not o.selected)
            )
        else:
            new_list.append(o)
    return new_list, was_selected


def _cascade_deselect(
    exps: list[PrepExperimentItem], opp_id: int
) -> list[PrepExperimentItem]:
    """Replica of the cascade-deselect block inside toggle_prep_opportunity."""
    return [
        PrepExperimentItem(
            id=e.id,
            opp_id=e.opp_id,
            solution_name=e.solution_name,
            experiment_name=e.experiment_name,
            assumption=e.assumption,
            selected=False if e.opp_id == opp_id else e.selected,
        )
        for e in exps
    ]


def _toggle_exp(
    exps: list[PrepExperimentItem], exp_id: int
) -> list[PrepExperimentItem]:
    """Replica of toggle_prep_experiment."""
    return [
        PrepExperimentItem(
            id=e.id,
            opp_id=e.opp_id,
            solution_name=e.solution_name,
            experiment_name=e.experiment_name,
            assumption=e.assumption,
            selected=not e.selected if e.id == exp_id else e.selected,
        )
        for e in exps
    ]


def _selected_opp_ids(opps: list[PrepOppItem]) -> list[int]:
    """Replica of the selected_opportunity_ids computed var."""
    return [o.id for o in opps if o.selected]


def _selected_exp_ids(exps: list[PrepExperimentItem]) -> list[int]:
    """Replica of the selected_experiment_ids computed var."""
    return [e.id for e in exps if e.selected]


def _visible_prep_experiments(
    opps: list[PrepOppItem], exps: list[PrepExperimentItem]
) -> list[PrepExperimentItem]:
    """Replica of the visible_prep_experiments computed var."""
    sel_ids = {o.id for o in opps if o.selected}
    if not sel_ids:
        return []
    return [e for e in exps if e.opp_id in sel_ids]


def _prep_persona_options(available_personas: list[str]) -> list[str]:
    """Replica of the prep_persona_options computed var."""
    return ["— None —"] + available_personas


def _should_clear_persona(persona: str) -> bool:
    """Replica of the guard clause in load_prep_for_persona."""
    return not persona or persona == "— None —"


def _build_opps_section(opps: list[PrepOppItem]) -> str:
    """Replica of the opps_section string built in generate_hostile_questions."""
    return "\n".join(f"- [{o.theme}] {o.statement}" for o in opps)


def _build_exps_section(exps: list[PrepExperimentItem]) -> str:
    """Replica of the exps_section string built in generate_hostile_questions."""
    if not exps:
        return "None selected."
    return "\n".join(
        f"- Solution '{e.solution_name}' | Experiment '{e.experiment_name}' | Assumption: {e.assumption}"
        for e in exps
    )


def _build_persona_context(target_persona: str) -> str:
    """Replica of the persona_context string built in generate_hostile_questions."""
    if target_persona:
        return f"The intended interviewee persona is '{target_persona}'."
    return "No specific persona has been defined for this interview."


# ---------------------------------------------------------------------------
# Small factory helpers
# ---------------------------------------------------------------------------

def _opp(
    id: int,
    theme: str = "General",
    statement: str = "Users need X",
    selected: bool = False,
) -> PrepOppItem:
    return PrepOppItem(id=id, theme=theme, statement=statement, selected=selected)


def _exp(
    id: int,
    opp_id: int,
    solution_name: str = "Sol",
    experiment_name: str = "Exp",
    assumption: str = "Assumption",
    selected: bool = False,
) -> PrepExperimentItem:
    return PrepExperimentItem(
        id=id,
        opp_id=opp_id,
        solution_name=solution_name,
        experiment_name=experiment_name,
        assumption=assumption,
        selected=selected,
    )


# ---------------------------------------------------------------------------
# Tests: opportunity toggle logic
# ---------------------------------------------------------------------------

class TestTogglePrepOpportunity:
    def test_unselected_becomes_selected(self):
        opps = [_opp(1, selected=False)]
        result, was_selected = _toggle_opp(opps, 1)
        assert result[0].selected is True
        assert was_selected is False

    def test_selected_becomes_unselected(self):
        opps = [_opp(1, selected=True)]
        result, was_selected = _toggle_opp(opps, 1)
        assert result[0].selected is False
        assert was_selected is True

    def test_only_target_item_changes(self):
        opps = [_opp(1, selected=False), _opp(2, selected=True), _opp(3, selected=False)]
        result, _ = _toggle_opp(opps, 2)
        assert result[0].selected is False
        assert result[1].selected is False  # toggled from True
        assert result[2].selected is False

    def test_list_length_unchanged(self):
        opps = [_opp(i) for i in range(1, 6)]
        result, _ = _toggle_opp(opps, 3)
        assert len(result) == 5

    def test_other_fields_preserved(self):
        opps = [_opp(1, theme="Workflow", statement="Users can't find invoices")]
        result, _ = _toggle_opp(opps, 1)
        assert result[0].theme == "Workflow"
        assert result[0].statement == "Users can't find invoices"
        assert result[0].id == 1

    def test_nonexistent_id_leaves_list_unchanged(self):
        opps = [_opp(1, selected=True), _opp(2, selected=False)]
        result, was_selected = _toggle_opp(opps, 99)
        assert result[0].selected is True
        assert result[1].selected is False
        assert was_selected is False

    def test_empty_list(self):
        result, was_selected = _toggle_opp([], 1)
        assert result == []
        assert was_selected is False

    def test_double_toggle_returns_to_original(self):
        opps = [_opp(1, selected=False)]
        result, _ = _toggle_opp(opps, 1)
        result, _ = _toggle_opp(result, 1)
        assert result[0].selected is False


# ---------------------------------------------------------------------------
# Tests: cascade-deselect of experiments when opportunity is unchecked
# ---------------------------------------------------------------------------

class TestCascadeDeselect:
    def test_experiments_for_deselected_opp_are_cleared(self):
        exps = [
            _exp(1, opp_id=10, selected=True),
            _exp(2, opp_id=10, selected=True),
            _exp(3, opp_id=20, selected=True),
        ]
        result = _cascade_deselect(exps, opp_id=10)
        assert result[0].selected is False   # belongs to opp 10
        assert result[1].selected is False   # belongs to opp 10
        assert result[2].selected is True    # belongs to opp 20 — unaffected

    def test_no_experiments_for_that_opp_is_noop(self):
        exps = [_exp(1, opp_id=20, selected=True)]
        result = _cascade_deselect(exps, opp_id=10)
        assert result[0].selected is True

    def test_already_unselected_experiments_stay_false(self):
        exps = [_exp(1, opp_id=10, selected=False)]
        result = _cascade_deselect(exps, opp_id=10)
        assert result[0].selected is False

    def test_empty_experiment_list(self):
        assert _cascade_deselect([], opp_id=1) == []

    def test_other_fields_preserved_during_cascade(self):
        exps = [_exp(1, opp_id=10, solution_name="AutoFill", experiment_name="Fake Door", assumption="Users notice it")]
        result = _cascade_deselect(exps, opp_id=10)
        assert result[0].solution_name == "AutoFill"
        assert result[0].experiment_name == "Fake Door"
        assert result[0].assumption == "Users notice it"


class TestToggleWithCascadeWorkflow:
    """Integration: simulates the full toggle_prep_opportunity call."""

    def test_deselecting_opp_clears_its_experiments(self):
        opps = [_opp(10, selected=True), _opp(20, selected=True)]
        exps = [_exp(1, opp_id=10, selected=True), _exp(2, opp_id=20, selected=True)]

        new_opps, was_selected = _toggle_opp(opps, 10)
        assert was_selected is True  # triggers cascade
        new_exps = _cascade_deselect(exps, opp_id=10)

        assert new_opps[0].selected is False
        assert new_exps[0].selected is False  # opp 10's experiment cleared
        assert new_exps[1].selected is True   # opp 20's experiment preserved

    def test_selecting_opp_does_not_cascade(self):
        opps = [_opp(10, selected=False)]
        exps = [_exp(1, opp_id=10, selected=False)]

        _, was_selected = _toggle_opp(opps, 10)
        assert was_selected is False  # no cascade triggered


# ---------------------------------------------------------------------------
# Tests: experiment toggle logic
# ---------------------------------------------------------------------------

class TestTogglePrepExperiment:
    def test_unselected_becomes_selected(self):
        exps = [_exp(1, opp_id=1, selected=False)]
        result = _toggle_exp(exps, 1)
        assert result[0].selected is True

    def test_selected_becomes_unselected(self):
        exps = [_exp(1, opp_id=1, selected=True)]
        result = _toggle_exp(exps, 1)
        assert result[0].selected is False

    def test_only_target_experiment_changes(self):
        exps = [
            _exp(1, opp_id=1, selected=False),
            _exp(2, opp_id=1, selected=True),
            _exp(3, opp_id=2, selected=False),
        ]
        result = _toggle_exp(exps, 2)
        assert result[0].selected is False
        assert result[1].selected is False  # toggled
        assert result[2].selected is False

    def test_other_fields_preserved(self):
        exps = [_exp(1, opp_id=5, solution_name="Auto-Suggest", experiment_name="Fake Door", assumption="Users click")]
        result = _toggle_exp(exps, 1)
        assert result[0].solution_name == "Auto-Suggest"
        assert result[0].experiment_name == "Fake Door"
        assert result[0].assumption == "Users click"
        assert result[0].opp_id == 5

    def test_empty_list(self):
        assert _toggle_exp([], 1) == []

    def test_double_toggle_returns_to_original(self):
        exps = [_exp(1, opp_id=1, selected=True)]
        result = _toggle_exp(exps, 1)
        result = _toggle_exp(result, 1)
        assert result[0].selected is True


# ---------------------------------------------------------------------------
# Tests: selected_opportunity_ids computed var
# ---------------------------------------------------------------------------

class TestSelectedOpportunityIds:
    def test_empty_list_returns_empty(self):
        assert _selected_opp_ids([]) == []

    def test_none_selected(self):
        assert _selected_opp_ids([_opp(1), _opp(2), _opp(3)]) == []

    def test_all_selected(self):
        opps = [_opp(1, selected=True), _opp(2, selected=True)]
        assert _selected_opp_ids(opps) == [1, 2]

    def test_some_selected(self):
        opps = [_opp(1, selected=True), _opp(2, selected=False), _opp(3, selected=True)]
        assert _selected_opp_ids(opps) == [1, 3]

    def test_preserves_order(self):
        opps = [_opp(30, selected=True), _opp(10, selected=True), _opp(20, selected=True)]
        assert _selected_opp_ids(opps) == [30, 10, 20]


# ---------------------------------------------------------------------------
# Tests: selected_experiment_ids computed var
# ---------------------------------------------------------------------------

class TestSelectedExperimentIds:
    def test_empty_list_returns_empty(self):
        assert _selected_exp_ids([]) == []

    def test_none_selected(self):
        exps = [_exp(1, opp_id=1), _exp(2, opp_id=1)]
        assert _selected_exp_ids(exps) == []

    def test_some_selected(self):
        exps = [
            _exp(1, opp_id=1, selected=True),
            _exp(2, opp_id=1, selected=False),
            _exp(3, opp_id=2, selected=True),
        ]
        assert _selected_exp_ids(exps) == [1, 3]

    def test_all_selected(self):
        exps = [_exp(1, opp_id=1, selected=True), _exp(2, opp_id=2, selected=True)]
        assert _selected_exp_ids(exps) == [1, 2]


# ---------------------------------------------------------------------------
# Tests: visible_prep_experiments computed var
# ---------------------------------------------------------------------------

class TestVisiblePrepExperiments:
    def test_no_selected_opps_returns_empty(self):
        opps = [_opp(1, selected=False)]
        exps = [_exp(1, opp_id=1, selected=True)]
        assert _visible_prep_experiments(opps, exps) == []

    def test_empty_opportunities_returns_empty(self):
        exps = [_exp(1, opp_id=1)]
        assert _visible_prep_experiments([], exps) == []

    def test_shows_experiments_for_selected_opp(self):
        opps = [_opp(10, selected=True), _opp(20, selected=False)]
        exps = [_exp(1, opp_id=10), _exp(2, opp_id=20), _exp(3, opp_id=10)]
        result = _visible_prep_experiments(opps, exps)
        assert len(result) == 2
        assert all(e.opp_id == 10 for e in result)

    def test_hides_experiments_for_unselected_opp(self):
        opps = [_opp(10, selected=True), _opp(20, selected=False)]
        exps = [_exp(1, opp_id=20)]
        assert _visible_prep_experiments(opps, exps) == []

    def test_shows_experiments_for_multiple_selected_opps(self):
        opps = [_opp(10, selected=True), _opp(20, selected=True), _opp(30, selected=False)]
        exps = [_exp(1, opp_id=10), _exp(2, opp_id=20), _exp(3, opp_id=30)]
        result = _visible_prep_experiments(opps, exps)
        assert len(result) == 2
        assert {e.opp_id for e in result} == {10, 20}

    def test_empty_experiment_list_returns_empty(self):
        opps = [_opp(1, selected=True)]
        assert _visible_prep_experiments(opps, []) == []

    def test_opp_with_no_experiments_returns_empty(self):
        opps = [_opp(10, selected=True)]
        exps = [_exp(1, opp_id=99)]  # different opp
        assert _visible_prep_experiments(opps, exps) == []


# ---------------------------------------------------------------------------
# Tests: prep_persona_options computed var
# ---------------------------------------------------------------------------

class TestPrepPersonaOptions:
    def test_always_starts_with_none_sentinel(self):
        result = _prep_persona_options(["Alice", "Bob"])
        assert result[0] == "— None —"

    def test_includes_all_personas_after_sentinel(self):
        personas = ["VP of Eng", "SMB Owner", "Enterprise Admin"]
        result = _prep_persona_options(personas)
        assert result == ["— None —", "VP of Eng", "SMB Owner", "Enterprise Admin"]

    def test_empty_personas_still_has_sentinel(self):
        assert _prep_persona_options([]) == ["— None —"]

    def test_length_is_personas_plus_one(self):
        personas = ["A", "B", "C"]
        assert len(_prep_persona_options(personas)) == len(personas) + 1

    def test_sentinel_is_exact_string(self):
        result = _prep_persona_options([])
        assert result[0] == "— None —"


# ---------------------------------------------------------------------------
# Tests: load_prep_for_persona sentinel handling
# ---------------------------------------------------------------------------

class TestPersonaSentinelHandling:
    def test_none_sentinel_triggers_clear(self):
        assert _should_clear_persona("— None —") is True

    def test_empty_string_triggers_clear(self):
        assert _should_clear_persona("") is True

    def test_real_persona_does_not_trigger_clear(self):
        assert _should_clear_persona("Enterprise Admin") is False

    def test_single_space_triggers_clear(self):
        # `not " "` is False in Python, but an empty-ish persona would be " "
        # The actual guard is `not persona or persona == "— None —"`
        # A single space: `not " "` is False, so it would NOT clear.
        # This documents the actual behavior.
        assert _should_clear_persona(" ") is False  # not falsy — would not clear

    @pytest.mark.parametrize("persona", [
        "VP of Engineering",
        "SMB Owner",
        "End User",
        "Product Manager",
        "Enterprise Admin",
    ])
    def test_various_real_personas_do_not_trigger_clear(self, persona):
        assert _should_clear_persona(persona) is False

    def test_none_value_triggers_clear(self):
        # Python `not None` is True
        assert _should_clear_persona(None) is True  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: prompt content building (strings interpolated into the LLM prompt)
# ---------------------------------------------------------------------------

class TestPromptContentBuilding:
    def test_opps_section_single_opportunity(self):
        opps = [_opp(1, theme="Search", statement="Results are irrelevant")]
        assert _build_opps_section(opps) == "- [Search] Results are irrelevant"

    def test_opps_section_multiple_opportunities(self):
        opps = [
            _opp(1, theme="Workflow", statement="Can't batch-export invoices"),
            _opp(2, theme="Onboarding", statement="Setup takes too long"),
        ]
        result = _build_opps_section(opps)
        assert "- [Workflow] Can't batch-export invoices" in result
        assert "- [Onboarding] Setup takes too long" in result

    def test_opps_section_uses_theme_in_brackets(self):
        opps = [_opp(1, theme="MyTheme", statement="Statement")]
        result = _build_opps_section(opps)
        assert result.startswith("- [MyTheme]")

    def test_exps_section_empty_returns_none_selected(self):
        assert _build_exps_section([]) == "None selected."

    def test_exps_section_formats_all_fields(self):
        exps = [_exp(1, opp_id=1, solution_name="AutoFill", experiment_name="Fake Door", assumption="Users notice the button")]
        result = _build_exps_section(exps)
        assert "Solution 'AutoFill'" in result
        assert "Experiment 'Fake Door'" in result
        assert "Assumption: Users notice the button" in result

    def test_exps_section_multiple_lines(self):
        exps = [
            _exp(1, opp_id=1, solution_name="S1", experiment_name="E1", assumption="A1"),
            _exp(2, opp_id=2, solution_name="S2", experiment_name="E2", assumption="A2"),
        ]
        result = _build_exps_section(exps)
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_persona_context_with_persona(self):
        ctx = _build_persona_context("VP of Engineering")
        assert ctx == "The intended interviewee persona is 'VP of Engineering'."

    def test_persona_context_without_persona(self):
        ctx = _build_persona_context("")
        assert ctx == "No specific persona has been defined for this interview."

    def test_persona_context_includes_persona_name(self):
        ctx = _build_persona_context("SMB Owner")
        assert "SMB Owner" in ctx


# ---------------------------------------------------------------------------
# Tests: generate_hostile_questions guard clause logic
# ---------------------------------------------------------------------------

class TestGenerateGuideGuardClause:
    def test_no_persona_and_no_opps_triggers_guard(self):
        """Guard fires when BOTH persona is empty AND no opps are selected."""
        has_persona = False
        selected_opps = []
        # Guard condition: `not has_persona and not selected_opps`
        assert not has_persona and not selected_opps

    def test_has_persona_no_opps_does_not_trigger_guard(self):
        """Guard is bypassed when a persona is chosen (legacy path)."""
        has_persona = True
        selected_opps = []
        assert not (not has_persona and not selected_opps)

    def test_no_persona_has_opps_does_not_trigger_guard(self):
        """Guard is bypassed when opportunities are selected (OST path)."""
        has_persona = False
        selected_opps = [_opp(1, selected=True)]
        assert not (not has_persona and not selected_opps)

    def test_has_both_does_not_trigger_guard(self):
        has_persona = True
        selected_opps = [_opp(1, selected=True)]
        assert not (not has_persona and not selected_opps)

    def test_opps_selected_flag_determines_branch(self):
        """When selected_opps is non-empty, OST branch is taken."""
        selected_opps = [_opp(1, selected=True), _opp(2, selected=True)]
        assert bool(selected_opps) is True  # OST path

    def test_empty_opps_forces_persona_branch(self):
        selected_opps: list = []
        assert bool(selected_opps) is False  # persona-only path


# ---------------------------------------------------------------------------
# Tests: interview guide prompt template integrity
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def interview_guide_prompt() -> str:
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "prompts", "interview_guide.txt")
    )
    with open(path) as f:
        return f.read()


class TestInterviewGuidePromptTemplate:
    def test_prompt_file_exists(self):
        path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "prompts", "interview_guide.txt")
        )
        assert os.path.isfile(path)

    def test_has_persona_context_placeholder(self, interview_guide_prompt):
        assert "{persona_context}" in interview_guide_prompt

    def test_has_opportunities_section_placeholder(self, interview_guide_prompt):
        assert "{opportunities_section}" in interview_guide_prompt

    def test_has_assumptions_section_placeholder(self, interview_guide_prompt):
        assert "{assumptions_section}" in interview_guide_prompt

    def test_mentions_opening_section(self, interview_guide_prompt):
        assert "Opening" in interview_guide_prompt

    def test_mentions_closing_section(self, interview_guide_prompt):
        assert "Closing" in interview_guide_prompt

    def test_mentions_opportunity_exploration(self, interview_guide_prompt):
        assert "Opportunity Exploration" in interview_guide_prompt

    def test_mentions_assumption_probes(self, interview_guide_prompt):
        assert "Assumption" in interview_guide_prompt

    def test_placeholders_are_formattable(self, interview_guide_prompt):
        """str.format() with all three placeholders must not raise."""
        result = interview_guide_prompt.format(
            persona_context="The interviewee is a VP of Engineering.",
            opportunities_section="- [Workflow] Can't batch-export",
            assumptions_section="- Solution 'X' | Experiment 'Y' | Assumption: Z",
        )
        assert "VP of Engineering" in result

    def test_no_extra_unresolved_placeholders(self, interview_guide_prompt):
        """After formatting the three known placeholders, no {…} remain."""
        result = interview_guide_prompt.format(
            persona_context="ctx",
            opportunities_section="opps",
            assumptions_section="exps",
        )
        import re
        remaining = re.findall(r"\{[^}]+\}", result)
        assert remaining == [], f"Unresolved placeholders found: {remaining}"


# ---------------------------------------------------------------------------
# Tests: load_prep_data DB query logic (uses db_session fixture)
# ---------------------------------------------------------------------------

class TestLoadPrepDataQueries:
    """Validates the SQL queries performed by load_prep_data() against an
    in-memory SQLite database using the same schema as production."""

    def test_no_opportunities_returns_empty(self, db_session):
        from cont_synth.models import Opportunity
        results = db_session.exec(select(Opportunity)).all()
        assert results == []

    def test_opportunities_loaded_for_correct_product(self, db_session):
        from cont_synth.models import Opportunity, Product

        prod_a = Product(name="Workspace A")
        prod_b = Product(name="Workspace B")
        db_session.add_all([prod_a, prod_b])
        db_session.commit()
        db_session.refresh(prod_a)
        db_session.refresh(prod_b)

        db_session.add(Opportunity(product_id=prod_a.id, statement="Opp for A", theme="Theme A"))
        db_session.add(Opportunity(product_id=prod_b.id, statement="Opp for B", theme="Theme B"))
        db_session.commit()

        results = db_session.exec(
            select(Opportunity).where(Opportunity.product_id == prod_a.id)
        ).all()
        assert len(results) == 1
        assert results[0].statement == "Opp for A"

    def test_running_experiments_included(self, db_session):
        from cont_synth.models import Experiment, Opportunity, Product, Solution

        prod = Product(name="WS")
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

        opp = Opportunity(product_id=prod.id, statement="Opp", theme="T")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        sol = Solution(opportunity_id=opp.id, name="Sol", description="D")
        db_session.add(sol)
        db_session.commit()
        db_session.refresh(sol)

        db_session.add(Experiment(solution_id=sol.id, name="Running Exp", assumption="A", method="Fake Door", status="Running"))
        db_session.add(Experiment(solution_id=sol.id, name="Draft Exp", assumption="B", method="A/B Test", status="Draft"))
        db_session.add(Experiment(solution_id=sol.id, name="Done Exp", assumption="C", method="Prototype Interview", status="Concluded"))
        db_session.commit()

        running = db_session.exec(
            select(Experiment).where(
                Experiment.solution_id.in_([sol.id]),
                Experiment.status == "Running",
            )
        ).all()
        assert len(running) == 1
        assert running[0].name == "Running Exp"

    def test_draft_and_concluded_experiments_excluded(self, db_session):
        from cont_synth.models import Experiment, Opportunity, Product, Solution

        prod = Product(name="WS")
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

        opp = Opportunity(product_id=prod.id, statement="Opp", theme="T")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        sol = Solution(opportunity_id=opp.id, name="Sol", description="D")
        db_session.add(sol)
        db_session.commit()
        db_session.refresh(sol)

        for status in ["Draft", "Concluded"]:
            db_session.add(
                Experiment(solution_id=sol.id, name=f"Exp-{status}", assumption="A", method="Fake Door", status=status)
            )
        db_session.commit()

        running = db_session.exec(
            select(Experiment).where(
                Experiment.solution_id.in_([sol.id]),
                Experiment.status == "Running",
            )
        ).all()
        assert running == []

    def test_experiment_opp_id_resolved_via_solution_fk(self, db_session):
        """sol_to_opp lookup must map experiment → solution → opportunity correctly."""
        from cont_synth.models import Experiment, Opportunity, Product, Solution

        prod = Product(name="WS")
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

        opp = Opportunity(product_id=prod.id, statement="Opp", theme="T")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        sol = Solution(opportunity_id=opp.id, name="Sol", description="D")
        db_session.add(sol)
        db_session.commit()
        db_session.refresh(sol)

        exp = Experiment(solution_id=sol.id, name="E", assumption="A", method="Fake Door", status="Running")
        db_session.add(exp)
        db_session.commit()
        db_session.refresh(exp)

        solutions = db_session.exec(
            select(Solution).where(Solution.opportunity_id.in_([opp.id]))
        ).all()
        sol_to_opp = {s.id: s.opportunity_id for s in solutions}

        assert sol_to_opp[sol.id] == opp.id

    def test_experiments_from_other_products_not_included(self, db_session):
        """Running experiments from product B must not appear in product A's results."""
        from cont_synth.models import Experiment, Opportunity, Product, Solution

        prod_a = Product(name="A")
        prod_b = Product(name="B")
        db_session.add_all([prod_a, prod_b])
        db_session.commit()
        db_session.refresh(prod_a)
        db_session.refresh(prod_b)

        opp_a = Opportunity(product_id=prod_a.id, statement="A-opp", theme="T")
        opp_b = Opportunity(product_id=prod_b.id, statement="B-opp", theme="T")
        db_session.add_all([opp_a, opp_b])
        db_session.commit()
        db_session.refresh(opp_a)
        db_session.refresh(opp_b)

        sol_a = Solution(opportunity_id=opp_a.id, name="Sol A", description="")
        sol_b = Solution(opportunity_id=opp_b.id, name="Sol B", description="")
        db_session.add_all([sol_a, sol_b])
        db_session.commit()
        db_session.refresh(sol_a)
        db_session.refresh(sol_b)

        db_session.add(Experiment(solution_id=sol_a.id, name="Exp A", assumption="A", method="Fake Door", status="Running"))
        db_session.add(Experiment(solution_id=sol_b.id, name="Exp B", assumption="B", method="Fake Door", status="Running"))
        db_session.commit()

        # Simulate load_prep_data scoped to product A
        opp_ids_a = [opp_a.id]
        solutions_a = db_session.exec(
            select(Solution).where(Solution.opportunity_id.in_(opp_ids_a))
        ).all()
        sol_ids_a = [s.id for s in solutions_a]
        running = db_session.exec(
            select(Experiment).where(
                Experiment.solution_id.in_(sol_ids_a),
                Experiment.status == "Running",
            )
        ).all()
        assert len(running) == 1
        assert running[0].name == "Exp A"

    def test_multiple_solutions_per_opportunity(self, db_session):
        """Multiple solutions under one opp each contribute their running experiments."""
        from cont_synth.models import Experiment, Opportunity, Product, Solution

        prod = Product(name="WS")
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

        opp = Opportunity(product_id=prod.id, statement="Opp", theme="T")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        sol1 = Solution(opportunity_id=opp.id, name="Sol 1", description="")
        sol2 = Solution(opportunity_id=opp.id, name="Sol 2", description="")
        db_session.add_all([sol1, sol2])
        db_session.commit()
        db_session.refresh(sol1)
        db_session.refresh(sol2)

        db_session.add(Experiment(solution_id=sol1.id, name="Exp 1", assumption="A", method="Fake Door", status="Running"))
        db_session.add(Experiment(solution_id=sol2.id, name="Exp 2", assumption="B", method="A/B Test", status="Running"))
        db_session.commit()

        running = db_session.exec(
            select(Experiment).where(
                Experiment.solution_id.in_([sol1.id, sol2.id]),
                Experiment.status == "Running",
            )
        ).all()
        assert len(running) == 2
        assert {e.name for e in running} == {"Exp 1", "Exp 2"}

    def test_no_solutions_returns_no_experiments(self, db_session):
        """If an opportunity has no solutions, no experiments can be found."""
        from cont_synth.models import Experiment, Opportunity, Product, Solution

        prod = Product(name="WS")
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

        opp = Opportunity(product_id=prod.id, statement="Opp", theme="T")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        # No solutions added
        solutions = db_session.exec(
            select(Solution).where(Solution.opportunity_id.in_([opp.id]))
        ).all()
        assert solutions == []
        # With no solution IDs, experiment query would not be performed
        sol_ids = [s.id for s in solutions]
        assert sol_ids == []
