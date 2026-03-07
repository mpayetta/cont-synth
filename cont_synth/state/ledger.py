from datetime import datetime, timezone
from typing import Dict, List, Set

import json
import reflex as rx
from sqlmodel import select

from ..models import (
    Persona,
    Interview,
    Opportunity,
    InterviewOpportunityLink,
    Solution,
    Outcome,
    OutcomeOpportunityLink,
    Experiment,
    AuditLog,
)
from .core import (
    ExperimentItem,
    OppDetailSolution,
    PersonaBadge,
    QuoteItem,
    SolutionItem,
    OutcomeItem,
    LedgerItem,
    ThemeGroup,
    BoardColumn,
    MatrixCell,
)


class LedgerStateMixin(rx.State, mixin=True):
    """Global ledger, drawer workspace, outcomes, solutions, and evidence state mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

    # ── Filter computed vars ──────────────────────────────────────────────────

    @rx.var
    def available_personas_in_ledger(self) -> list[str]:
        """Unique persona names across all opportunities (for filter dropdown)."""
        seen = []
        for item in self.ledger_data:
            for badge in item.personas_affected:
                if badge.name and badge.name not in seen:
                    seen.append(badge.name)
        return sorted(seen)

    @rx.var
    def opp_filters_active(self) -> bool:
        """True when at least one filter is applied."""
        return bool(
            self.opp_filter_themes
            or self.opp_filter_personas
            or self.opp_filter_priority
            or self.opp_filter_search
        )

    @rx.var
    def filtered_ledger_data(self) -> list[LedgerItem]:
        """ledger_data with active filters applied."""
        items = self.ledger_data
        if self.opp_filter_themes:
            items = [i for i in items if i.theme in self.opp_filter_themes]
        if self.opp_filter_personas:
            items = [
                i for i in items
                if any(b.name in self.opp_filter_personas for b in i.personas_affected)
            ]
        if self.opp_filter_priority:
            if self.opp_filter_priority == "high":
                items = [i for i in items if i.priority_score >= 11]
            elif self.opp_filter_priority == "medium":
                items = [i for i in items if 6 <= i.priority_score <= 10]
            elif self.opp_filter_priority == "low":
                items = [i for i in items if 1 <= i.priority_score <= 5]
            elif self.opp_filter_priority == "unrated":
                items = [i for i in items if i.priority_score == 0]
        if self.opp_filter_search:
            q = self.opp_filter_search.lower()
            items = [i for i in items if q in i.opportunity.lower()]
        return items

    # ── View-mode computed vars ───────────────────────────────────────────────

    @rx.var
    def ledger_data_by_theme(self) -> list[ThemeGroup]:
        """Groups filtered_ledger_data by theme for the collapsible list view."""
        groups: dict[str, list[LedgerItem]] = {}
        for item in self.filtered_ledger_data:
            theme = item.theme if item.theme else "Uncategorized"
            groups.setdefault(theme, []).append(item)

        result: list[ThemeGroup] = []
        for theme, items in groups.items():
            avg_p = sum(i.priority_score for i in items) // max(len(items), 1)
            result.append(ThemeGroup(
                theme=theme,
                count=len(items),
                avg_priority=avg_p,
                collapsed=theme in self.collapsed_themes,
                opps=items,
            ))

        result.sort(key=lambda g: -g.avg_priority)
        return result

    @rx.var
    def ledger_board_columns(self) -> list[BoardColumn]:
        """Splits filtered_ledger_data into 4 priority tiers for the Kanban board view."""
        high = [i for i in self.filtered_ledger_data if i.priority_score >= 8]
        medium = [i for i in self.filtered_ledger_data if 4 <= i.priority_score < 8]
        low = [i for i in self.filtered_ledger_data if 1 <= i.priority_score < 4]
        unscored = [i for i in self.filtered_ledger_data if i.priority_score == 0]
        return [
            BoardColumn(label="High  P≥8", color="amber", opps=high),
            BoardColumn(label="Medium  P≥4", color="blue", opps=medium),
            BoardColumn(label="Low  P<4", color="gray", opps=low),
            BoardColumn(label="Unscored", color="gray", opps=unscored),
        ]

    @rx.var
    def matrix_cells(self) -> list[MatrixCell]:
        """Returns 25 cells (sat_gap 5→1 × impact 1→5) for the priority matrix."""
        cells: list[MatrixCell] = []
        for sat in range(5, 0, -1):
            for imp in range(1, 6):
                cell_items = [
                    i for i in self.filtered_ledger_data
                    if i.sat_gap_score == sat and i.impact_score == imp
                ]
                cells.append(MatrixCell(
                    sat_gap=sat,
                    impact=imp,
                    opps=cell_items,
                    is_sweet_spot=(sat >= 3 and imp >= 3),
                ))
        return cells

    @rx.var
    def matrix_unscored(self) -> list[LedgerItem]:
        """Opportunities missing at least one score (cannot appear in matrix)."""
        return [
            i for i in self.filtered_ledger_data
            if i.impact_score == 0 or i.sat_gap_score == 0
        ]

    def toggle_theme_collapse(self, theme: str):
        """Collapses or expands a theme group in the list view."""
        if theme in self.collapsed_themes:
            self.collapsed_themes = [t for t in self.collapsed_themes if t != theme]
        else:
            self.collapsed_themes = self.collapsed_themes + [theme]

    # ─────────────────────────────────────────────────────────────────────────

    @rx.var
    def selectable_outcomes(self) -> list[str]:
        """Names of outcomes plus a None/unmapped option."""
        return ["None (Unmapped)"] + [o.name for o in self.outcomes]

    @rx.var
    def solution_choices_for_experiment(self) -> list[str]:
        """Solutions of the selected opportunity formatted for the experiment form select."""
        return [
            f"{s.id} - {s.name}"
            for s in self.selected_opportunity.solutions
        ]

    @rx.var
    def detail_solutions_with_experiments(self) -> list[OppDetailSolution]:
        """Combines solutions with their experiments for the full-page detail view."""
        result = []
        for sol in self.selected_opportunity.solutions:
            sol_exps = [
                e for e in self.selected_opportunity.experiments
                if e.solution_id == sol.id
            ]
            result.append(OppDetailSolution(
                id=sol.id,
                parent_id=sol.parent_id,
                name=sol.name,
                description=sol.description,
                status=sol.status,
                indent_level=sol.indent_level,
                experiments=sol_exps,
            ))
        return result

    def load_outcomes(self):
        """Loads all business outcomes for the global dropdowns."""
        with rx.session() as session:
            db_outcomes = session.exec(
                select(Outcome).where(Outcome.product_id == int(self.active_product_id))
            ).all()
            self.outcomes = [OutcomeItem(id=o.id, name=o.name) for o in db_outcomes]
            self.outcome_names = ["All Outcomes", "Unmapped Opportunities"] + [
                o.name for o in self.outcomes
            ]

    def load_ledger(self):
        """Loads the global opportunity ledger with evidence, solutions, and outcomes."""
        self.load_outcomes()
        with rx.session() as session:
            opportunities = session.exec(
                select(Opportunity).where(
                    Opportunity.product_id == int(self.active_product_id)
                )
            ).all()
            opp_dict = {opp.id: opp for opp in opportunities}
            now = datetime.now(timezone.utc)

            # Pre-compute evidence counts for priority sort (single bulk query)
            opp_ids = [o.id for o in opportunities]
            _sort_links = (
                session.exec(
                    select(InterviewOpportunityLink).where(
                        InterviewOpportunityLink.opportunity_id.in_(opp_ids)
                    )
                ).all()
                if opp_ids else []
            )
            _evidence_counts: dict[int, int] = {}
            for _lnk in _sort_links:
                _evidence_counts[_lnk.opportunity_id] = _evidence_counts.get(_lnk.opportunity_id, 0) + 1

            def _opp_sort_key(o: Opportunity) -> tuple:
                freq = min(_evidence_counts.get(o.id, 0), 5)
                priority = o.impact_score + o.sat_gap_score + freq
                db_date = (
                    o.date_last_validated.replace(tzinfo=timezone.utc)
                    if o.date_last_validated.tzinfo is None
                    else o.date_last_validated
                )
                return (-priority, (now - db_date).days)

            # 1. BULLETPROOF FLATTENING (Handles Cycles & Orphans)
            opp_children_map = {}
            opp_top_level = []

            for opp in opportunities:
                # Only treat as a child if the parent actually exists in the DB
                if opp.parent_id and opp.parent_id in opp_dict:
                    opp_children_map.setdefault(opp.parent_id, []).append(opp)
                else:
                    opp_top_level.append(opp)

            # Sort roots and each sibling group: highest priority first, then fewest days_old
            opp_top_level.sort(key=_opp_sort_key)
            for _sibs in opp_children_map.values():
                _sibs.sort(key=_opp_sort_key)

            flat_opps: list[tuple[Opportunity, int]] = []
            visited_nodes = set()

            def append_opp_children(opp_id: int, current_level: int) -> None:
                if opp_id in visited_nodes:
                    return  # Break infinite loops
                visited_nodes.add(opp_id)

                if opp_id in opp_children_map:
                    for child in opp_children_map[opp_id]:
                        if child.id not in visited_nodes:
                            flat_opps.append((child, current_level))
                            append_opp_children(child.id, current_level + 1)

            # Process all valid top-level roots
            for opp in opp_top_level:
                if opp.id not in visited_nodes:
                    flat_opps.append((opp, 0))
                    append_opp_children(opp.id, 1)

            # RECOVERY: If any nodes are left over (they are trapped in a cycle A->B->A),
            # force them to render at the top level so they don't disappear from the UI!
            for opp in opportunities:
                if opp.id not in visited_nodes:
                    flat_opps.append((opp, 0))
                    append_opp_children(opp.id, 1)

            new_ledger: list[LedgerItem] = []
            personas_set: set[str] = set()

            # 2. ITERATE OVER FLATTENED OPPORTUNITIES
            for opp, opp_indent in flat_opps:
                links = session.exec(
                    select(InterviewOpportunityLink).where(
                        InterviewOpportunityLink.opportunity_id == opp.id
                    )
                ).all()
                affected_personas: Set[str] = set()
                evidence_list: List[QuoteItem] = []
                safe_colors = [
                    "blue",
                    "purple",
                    "orange",
                    "green",
                    "pink",
                    "teal",
                    "ruby",
                    "iris",
                    "indigo",
                ]

                for link in links:
                    interview = session.get(Interview, link.interview_id)
                    persona = session.get(Persona, interview.persona_id)
                    affected_personas.add(persona.name)
                    personas_set.add(persona.name)

                    color_index = sum(ord(c) for c in persona.name) % len(safe_colors)
                    p_color = safe_colors[color_index]

                    evidence_list.append(
                        QuoteItem(
                            interview_id=interview.id,
                            persona_name=persona.name,
                            persona_color=p_color,
                            text=link.source_quote,
                        )
                    )

                db_date = (
                    opp.date_last_validated.replace(tzinfo=timezone.utc)
                    if opp.date_last_validated.tzinfo is None
                    else opp.date_last_validated
                )
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

                badge_list: List[PersonaBadge] = []
                for p in sorted(list(affected_personas)):
                    color_index = sum(ord(c) for c in p) % len(safe_colors)
                    badge_list.append(
                        PersonaBadge(
                            name=p,
                            color=safe_colors[color_index],
                        )
                    )

                db_solutions = session.exec(
                    select(Solution).where(Solution.opportunity_id == opp.id)
                ).all()

                children_map: Dict[int, list[Solution]] = {}
                top_level: list[Solution] = []
                for s in db_solutions:
                    if s.parent_id:
                        children_map.setdefault(s.parent_id, []).append(s)
                    else:
                        top_level.append(s)

                flat_sols: list[SolutionItem] = []

                def append_children(parent_id: int, current_level: int) -> None:
                    if parent_id in children_map:
                        for child in children_map[parent_id]:
                            flat_sols.append(
                                SolutionItem(
                                    id=child.id,
                                    parent_id=child.parent_id,
                                    name=child.name,
                                    description=child.description,
                                    status=child.status,
                                    indent_level=current_level,
                                )
                            )
                            append_children(child.id, current_level + 1)

                for s in top_level:
                    flat_sols.append(
                        SolutionItem(
                            id=s.id,
                            parent_id=s.parent_id,
                            name=s.name,
                            description=s.description,
                            status=s.status,
                            indent_level=0,
                        )
                    )
                    append_children(s.id, 1)

                sol_items = flat_sols

                # Inside the per-opportunity loop, after sol_items is built:
                exp_items: list[ExperimentItem] = []
                for sol in db_solutions:
                    db_exps = session.exec(
                        select(Experiment).where(Experiment.solution_id == sol.id)
                    ).all()
                    for exp in db_exps:
                        exp_items.append(ExperimentItem(
                            id=exp.id,
                            solution_id=sol.id,
                            solution_name=sol.name,
                            name=exp.name,
                            assumption=exp.assumption,
                            description=exp.description,
                            success_metric=exp.success_metric,
                            method=exp.method,
                            status=exp.status,
                            signal=exp.signal,
                            evidence_notes=exp.evidence_notes,
                        ))

                outcome_links = session.exec(
                    select(OutcomeOpportunityLink).where(
                        OutcomeOpportunityLink.opportunity_id == opp.id
                    )
                ).all()
                linked_out_ids = [link.outcome_id for link in outcome_links]

                # Filter board by current outcome filter
                if self.active_outcome_name == "Unmapped Opportunities":
                    if len(linked_out_ids) > 0:
                        continue
                elif self.active_outcome_name != "All Outcomes":
                    active_out = next(
                        (
                            o
                            for o in self.outcomes
                            if o.name == self.active_outcome_name
                        ),
                        None,
                    )
                    if active_out and active_out.id not in linked_out_ids:
                        continue

                linked_out_items = [
                    out for out in self.outcomes if out.id in linked_out_ids
                ]

                running_exp_count = sum(1 for e in exp_items if e.status == "Running")
                frequency_score = min(len(evidence_list), 5)
                priority_score = opp.impact_score + opp.sat_gap_score + frequency_score

                new_ledger.append(
                    LedgerItem(
                        opportunity_id=opp.id,
                        parent_id=opp.parent_id if opp.parent_id is not None else -1,
                        indent_level=opp_indent,
                        theme=opp.theme,
                        personas_affected=badge_list,
                        opportunity=opp.statement,
                        status=status,
                        status_color=status_color,
                        days_old=days_old,
                        is_cross_functional=len(affected_personas) > 1,
                        evidence=evidence_list,
                        solutions=sol_items,
                        linked_outcomes=linked_out_items,
                        experiments=exp_items,
                        impact_score=opp.impact_score,
                        sat_gap_score=opp.sat_gap_score,
                        priority_score=priority_score,
                        running_experiments=running_exp_count,
                    )
                )

            # Remove the alphabetical sort to preserve tree order!
            self.ledger_data = new_ledger

            # Generate choices for the Parent Select dropdown
            self.parent_opp_choices = ["None"] + [
                f"{item.opportunity_id} - {item.opportunity}"
                for item in new_ledger
            ]

            self.available_personas = list(personas_set)
            if self.available_personas and not self.target_persona:
                self.target_persona = self.available_personas[0]

            all_interviews = (
                session.exec(
                    select(Interview).where(
                        Interview.product_id == int(self.active_product_id)
                    )
                ).all()
                if self.active_product_id
                else []
            )
            choices: list[str] = []
            for inv in all_interviews:
                p = session.get(Persona, inv.persona_id)
                date_str = (
                    inv.date_logged.strftime("%Y-%m-%d")
                    if inv.date_logged
                    else "Unknown"
                )
                choices.append(f"{inv.id} - {p.name} ({date_str})")
            self.interview_choices = choices[::-1]

    def _load_and_sync(self):
        """Reloads ledger data and refreshes selected_opportunity when on the detail page."""
        self.load_ledger()
        if self.current_view == "opportunity":
            for item in self.ledger_data:
                if item.opportunity_id == self.selected_opportunity_id:
                    self.selected_opportunity = item
                    break

    # Solutions tree
    def set_target_parent(self, sol_id: int, sol_name: str):
        """Activates branching mode and remembers the parent's name."""
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
        if self.is_viewer:
            return

        def delete_recursive(session, sol_id):
            # Delete experiments first
            experiments = session.exec(
                select(Experiment).where(Experiment.solution_id == sol_id)
            ).all()
            for exp in experiments:
                session.delete(exp)
            # Then recurse into children
            children = session.exec(
                select(Solution).where(Solution.parent_id == sol_id)
            ).all()
            for c in children:
                delete_recursive(session, c.id)
            sol = session.get(Solution, sol_id)
            if sol:
                session.delete(sol)


        with rx.session() as session:
            sol = session.get(Solution, solution_id)
            if sol:
                opp = session.get(Opportunity, sol.opportunity_id) if sol.opportunity_id else None
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=opp.product_id if opp else None,
                    entity_type="solution",
                    entity_id=solution_id,
                    action="delete",
                    detail=f'{{"name": "{sol.name[:120].replace(chr(34), chr(39))}"}}',
                ))
            delete_recursive(session, solution_id)
            session.commit()

        self._load_and_sync()

    def start_edit_solution(self, sol: SolutionItem):
        """Populates the input form with an existing solution's data."""
        self.editing_solution_id = sol.id
        self.new_solution_name = sol.name
        self.new_solution_desc = sol.description
        self.new_solution_status = sol.status

    def add_manual_solution(self, opportunity_id: int):
        """Saves a human-brainstormed solution or updates an existing one."""
        if self.is_viewer:
            return
        if not self.new_solution_name.strip():
            return rx.window_alert("Solution name cannot be empty.")

        with rx.session() as session:
            if self.editing_solution_id != -1:
                sol = session.get(Solution, self.editing_solution_id)
                if sol:
                    old_name = sol.name
                    old_status = sol.status
                    sol.name = self.new_solution_name.strip()
                    sol.description = self.new_solution_desc.strip()
                    sol.status = self.new_solution_status
                    sol.updated_by_user_id = self.auth_user_id
                    sol.updated_at = datetime.now(timezone.utc)
                    session.add(sol)
                    opp = session.get(Opportunity, sol.opportunity_id) if sol.opportunity_id else None
                    changes: dict = {}
                    if old_name != sol.name:
                        changes["name"] = {"from": old_name[:80], "to": sol.name[:80]}
                    if old_status != sol.status:
                        changes["status"] = {"from": old_status, "to": sol.status}
                    session.add(AuditLog(
                        user_id=self.auth_user_id,
                        product_id=opp.product_id if opp else None,
                        entity_type="solution",
                        entity_id=sol.id,
                        action="update",
                        detail=json.dumps({"opportunity_id": sol.opportunity_id, "changes": changes}),
                    ))
            else:
                parent_id_val = self.target_parent_id if self.target_parent_id != -1 else None
                new_sol = Solution(
                    opportunity_id=opportunity_id,
                    parent_id=parent_id_val,
                    name=self.new_solution_name.strip(),
                    description=self.new_solution_desc.strip(),
                    created_by_user_id=self.auth_user_id,
                )
                session.add(new_sol)
                session.commit()
                session.refresh(new_sol)
                opp = session.get(Opportunity, opportunity_id)
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=opp.product_id if opp else None,
                    entity_type="solution",
                    entity_id=new_sol.id,
                    action="create",
                    detail=json.dumps({
                        "name": new_sol.name[:80],
                        "opportunity_id": opportunity_id,
                        "parent_id": parent_id_val,
                    }),
                ))
            session.commit()

        self.editing_solution_id = -1
        self.target_parent_id = -1
        self.target_parent_name = ""
        self.new_solution_name = ""
        self.new_solution_desc = ""

        self._load_and_sync()

    # Outcomes
    def create_outcome(self):
        """Creates a new top-level business outcome."""
        if self.is_viewer:
            return
        if not self.new_outcome_name.strip():
            return
        with rx.session() as session:
            new_out = Outcome(
                name=self.new_outcome_name.strip(),
                description="",
                product_id=int(self.active_product_id),
                created_by_user_id=self.auth_user_id,
            )
            session.add(new_out)
            session.commit()

        self.active_outcome_name = self.new_outcome_name.strip()
        self.new_outcome_name = ""
        self.load_outcomes()
        self._load_and_sync()

    def change_outcome_filter(self, name: str):
        """Changes the global board filter and reloads."""
        self.active_outcome_name = name
        self._load_and_sync()

    def set_primary_outcome(self, outcome_name: str):
        """Forces an opportunity to have only ONE primary outcome, or none."""
        if self.is_viewer:
            return
        if not self.selected_opportunity:
            return

        self.selected_opp_outcome_name = outcome_name
        opp_id = self.selected_opportunity.opportunity_id

        selected_out = next((o for o in self.outcomes if o.name == outcome_name), None)

        with rx.session() as session:
            existing_links = session.exec(
                select(OutcomeOpportunityLink).where(
                    OutcomeOpportunityLink.opportunity_id == opp_id
                )
            ).all()
            for link in existing_links:
                session.delete(link)

            if selected_out:
                session.add(
                    OutcomeOpportunityLink(
                        opportunity_id=opp_id, outcome_id=selected_out.id
                    )
                )
            session.commit()

        self._load_and_sync()

    # Opportunity CRUD
    def handle_opp_dialog_change(self, is_open: bool):
        self.is_opp_dialog_open = is_open
        if not is_open:
            self.editing_opp_id = -1
            self.manual_opp_theme = "Uncategorized"
            self.manual_opp_statement = ""
            self.manual_opp_parent_id = "None"
            self.manual_opp_outcome_name = "None"

    def open_opp_dialog(self):
        self.editing_opp_id = -1
        self.manual_opp_theme = "Uncategorized"
        self.manual_opp_statement = ""
        self.manual_opp_parent_id = "None"
        self.manual_opp_outcome_name = "None"
        self.is_opp_dialog_open = True

    def close_opp_dialog(self):
        self.is_opp_dialog_open = False

    def open_delete_confirm(self, opp_id: int):
        self.pending_delete_opp_id = opp_id
        self.is_delete_confirm_open = True

    def close_delete_confirm(self, _open: bool = False):
        self.is_delete_confirm_open = False
        self.pending_delete_opp_id = -1

    def confirm_delete_opportunity(self):
        if self.pending_delete_opp_id != -1:
            self.delete_opportunity(self.pending_delete_opp_id)
        self.is_delete_confirm_open = False
        self.pending_delete_opp_id = -1

    def start_edit_opportunity(
        self, opp_id: int, theme: str, statement: str, parent_id: int
    ):
        self.editing_opp_id = opp_id
        self.manual_opp_theme = theme
        self.manual_opp_statement = statement

        # Match the parent ID to the string choice
        self.manual_opp_parent_id = "None"
        if parent_id != -1:
            for choice in self.parent_opp_choices:
                if choice.startswith(f"{parent_id} -"):
                    self.manual_opp_parent_id = choice
                    break

        # Prefill linked outcome (first one if any)
        self.manual_opp_outcome_name = "None"
        for item in self.ledger_data:
            if item.opportunity_id == opp_id and item.linked_outcomes:
                self.manual_opp_outcome_name = item.linked_outcomes[0].name
                break

        self.is_opp_dialog_open = True

    def save_manual_opportunity(self):
        """Handles both creating a new opportunity and updating an existing one."""
        if self.is_viewer:
            return
        if not self.manual_opp_statement.strip():
            return rx.window_alert("Opportunity statement cannot be empty.")

        parent_id_val = None
        if self.manual_opp_parent_id and self.manual_opp_parent_id != "None":
            try:
                parent_id_val = int(self.manual_opp_parent_id.split(" - ")[0])
            except Exception:
                pass

        if self.editing_opp_id != -1 and parent_id_val == self.editing_opp_id:
            return rx.window_alert("An opportunity cannot be its own parent.")

        with rx.session() as session:
            # Check if we are setting a new parent to inherit outcomes
            parent_outcome_ids = []
            if parent_id_val:
                parent_links = session.exec(
                    select(OutcomeOpportunityLink).where(
                        OutcomeOpportunityLink.opportunity_id == parent_id_val
                    )
                ).all()
                parent_outcome_ids = [link.outcome_id for link in parent_links]

            chosen_outcome = next(
                (o for o in self.outcomes if o.name == self.manual_opp_outcome_name), None
            )

            if self.editing_opp_id != -1:
                opp = session.get(Opportunity, self.editing_opp_id)
                if opp:
                    # Capture old values before overwriting
                    old_statement = opp.statement
                    old_theme = opp.theme
                    old_parent_id = opp.parent_id
                    opp.theme = self.manual_opp_theme.strip()
                    opp.statement = self.manual_opp_statement.strip()
                    opp.parent_id = parent_id_val
                    session.add(opp)

                    # Build diff detail
                    changes: dict = {}
                    new_stmt = self.manual_opp_statement.strip()
                    new_theme = self.manual_opp_theme.strip()
                    if old_statement != new_stmt:
                        changes["statement"] = {"from": old_statement[:80].replace('"', "'"), "to": new_stmt[:80].replace('"', "'")}
                    if old_theme != new_theme:
                        changes["theme"] = {"from": old_theme, "to": new_theme}
                    if old_parent_id != parent_id_val:
                        changes["parent_id"] = {"from": old_parent_id, "to": parent_id_val}
                    session.add(AuditLog(
                        user_id=self.auth_user_id,
                        product_id=opp.product_id,
                        entity_type="opportunity",
                        entity_id=opp.id,
                        action="update",
                        detail=json.dumps(changes),
                    ))

                    # Apply dialog outcome selection (clears and re-sets)
                    existing_outcomes = session.exec(
                        select(OutcomeOpportunityLink).where(
                            OutcomeOpportunityLink.opportunity_id == opp.id
                        )
                    ).all()
                    for link in existing_outcomes:
                        session.delete(link)
                    if chosen_outcome:
                        session.add(
                            OutcomeOpportunityLink(
                                opportunity_id=opp.id, outcome_id=chosen_outcome.id
                            )
                        )
                    elif not chosen_outcome and not existing_outcomes and parent_outcome_ids:
                        # Fall back to parent inheritance only if no explicit selection and none existed
                        for out_id in parent_outcome_ids:
                            session.add(
                                OutcomeOpportunityLink(
                                    opportunity_id=opp.id, outcome_id=out_id
                                )
                            )
            else:
                new_opp = Opportunity(
                    theme=self.manual_opp_theme.strip() or "Uncategorized",
                    statement=self.manual_opp_statement.strip(),
                    parent_id=parent_id_val,
                    created_by_user_id=self.auth_user_id,
                )
                session.add(new_opp)
                session.commit()
                session.refresh(new_opp)
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=new_opp.product_id,
                    entity_type="opportunity",
                    entity_id=new_opp.id,
                    action="create",
                    detail=f'{{"statement": "{new_opp.statement[:80].replace(chr(34), chr(39))}", "theme": "{new_opp.theme}"}}',
                ))

                if chosen_outcome:
                    session.add(
                        OutcomeOpportunityLink(
                            opportunity_id=new_opp.id, outcome_id=chosen_outcome.id
                        )
                    )
                else:
                    # Inherit from parent if no explicit selection
                    for out_id in parent_outcome_ids:
                        session.add(
                            OutcomeOpportunityLink(
                                opportunity_id=new_opp.id, outcome_id=out_id
                            )
                        )

            session.commit()

        self.close_opp_dialog()
        self._load_and_sync()

    def delete_opportunity(self, opp_id: int):
        """Safely deletes an opportunity and all nested relationships."""
        if self.is_viewer:
            return
        with rx.session() as session:
            opp = session.get(Opportunity, opp_id)
            if not opp:
                return

            # Audit log before deletion
            session.add(AuditLog(
                user_id=self.auth_user_id,
                product_id=opp.product_id,
                entity_type="opportunity",
                entity_id=opp_id,
                action="delete",
                detail=f'{{"statement": "{opp.statement[:120].replace(chr(34), chr(39))}", "theme": "{opp.theme}"}}',
            ))

            int_links = session.exec(
                select(InterviewOpportunityLink).where(
                    InterviewOpportunityLink.opportunity_id == opp_id
                )
            ).all()
            for link in int_links:
                session.delete(link)

            out_links = session.exec(
                select(OutcomeOpportunityLink).where(
                    OutcomeOpportunityLink.opportunity_id == opp_id
                )
            ).all()
            for link in out_links:
                session.delete(link)

            def delete_sol_recursive(sol_id: int):
                # Delete experiments first
                experiments = session.exec(
                    select(Experiment).where(Experiment.solution_id == sol_id)
                ).all()
                for exp in experiments:
                    session.delete(exp)
                    
                children = session.exec(
                    select(Solution).where(Solution.parent_id == sol_id)
                ).all()
                for c in children:
                    delete_sol_recursive(c.id)
                sol_to_del = session.get(Solution, sol_id)
                if sol_to_del:
                    session.delete(sol_to_del)

            sols = session.exec(
                select(Solution).where(Solution.opportunity_id == opp_id)
            ).all()
            for s in sols:
                delete_sol_recursive(s.id)

            session.delete(opp)
            session.commit()

        self._load_and_sync()

    # Evidence mapping
    def add_real_evidence(self, opportunity_id: int):
        """Links a missed quote from a real interview to this opportunity."""
        if self.is_viewer:
            return
        if not self.selected_interview_choice or not self.manual_quote_text.strip():
            return rx.window_alert("Please select an interview and enter a quote.")

        try:
            inv_id = int(self.selected_interview_choice.split(" - ")[0])
        except Exception:  # pragma: no cover - UI alert path
            return rx.window_alert("Invalid interview selection.")

        with rx.session() as session:
            existing = session.get(InterviewOpportunityLink, (inv_id, opportunity_id))
            if existing:
                return rx.window_alert(
                    "This interview is already linked here. Edit the transcript instead."
                )

            new_link = InterviewOpportunityLink(
                interview_id=inv_id,
                opportunity_id=opportunity_id,
                source_quote=self.manual_quote_text.strip(),
            )
            session.add(new_link)
            opp = session.get(Opportunity, opportunity_id)
            session.add(AuditLog(
                user_id=self.auth_user_id,
                product_id=opp.product_id if opp else None,
                entity_type="evidence",
                entity_id=opportunity_id,
                action="create",
                detail=json.dumps({"opportunity_id": opportunity_id, "interview_id": inv_id, "quote": self.manual_quote_text.strip()[:120]}),
            ))
            session.commit()

        self.manual_quote_text = ""
        self.selected_interview_choice = ""
        self._load_and_sync()

    def delete_evidence(self, opportunity_id: int, interview_id: int):
        """Unlinks an interview quote from an opportunity."""
        if self.is_viewer:
            return
        with rx.session() as session:
            link = session.get(InterviewOpportunityLink, (interview_id, opportunity_id))
            if link:
                opp = session.get(Opportunity, opportunity_id)
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=opp.product_id if opp else None,
                    entity_type="evidence",
                    entity_id=opportunity_id,
                    action="delete",
                    detail=json.dumps({"opportunity_id": opportunity_id, "interview_id": interview_id}),
                ))
                session.delete(link)
                session.commit()

        self._load_and_sync()
        
    def navigate_to_opportunity(self, opp_id: int):
        """Navigate to the opportunity detail page via URL routing."""
        self.current_view = "opportunity"
        self.selected_opportunity_id = opp_id
        self.load_data_for_current_view()
        return rx.redirect(f"/opportunities/{opp_id}")

    def enter_opp_detail_edit(self):
        """Enters inline edit mode on the opportunity detail page."""
        opp = self.selected_opportunity
        self.editing_opp_id = opp.opportunity_id
        self.manual_opp_theme = opp.theme
        self.manual_opp_statement = opp.opportunity
        self.manual_opp_parent_id = "None"
        if opp.parent_id != -1:
            for choice in self.parent_opp_choices:
                if choice.startswith(f"{opp.parent_id} -"):
                    self.manual_opp_parent_id = choice
                    break
        self.is_editing_opp_detail = True

    def exit_opp_detail_edit(self):
        """Cancels inline edit without saving."""
        self.is_editing_opp_detail = False
        self.editing_opp_id = -1
        self.manual_opp_theme = "Uncategorized"
        self.manual_opp_statement = ""
        self.manual_opp_parent_id = "None"

    def save_opp_detail_edit(self):
        """Saves the opportunity from the inline detail editor."""
        self.save_manual_opportunity()
        self.is_editing_opp_detail = False

    def delete_current_opportunity(self):
        """Deletes the currently viewed opportunity and navigates back to the ledger."""
        self.delete_opportunity(self.selected_opportunity.opportunity_id)
        return rx.redirect("/opportunities")

    def start_edit_solution_from_detail(
        self, sol_id: int, name: str, desc: str, status: str
    ):
        """Enters edit mode for a solution from the detail page."""
        self.editing_solution_id = sol_id
        self.new_solution_name = name
        self.new_solution_desc = desc
        self.new_solution_status = status

    def cancel_experiment_form(self):
        """Clears the inline experiment form without leaving the experiments area."""
        self.editing_experiment_id = -1
        self.experiment_target_solution_id = -1
        self.experiment_target_solution_name = ""
        self.selected_solution_for_experiment = ""
        self.new_experiment_name = ""
        self.new_experiment_assumption = ""
        self.new_experiment_description = ""
        self.new_experiment_success_metric = ""
        self.new_experiment_method = "Prototype Interview"
        self.new_experiment_method_other = ""

    def set_selected_solution_for_experiment(self, choice: str):
        """Parses the select string and sets the target solution fields."""
        try:
            sol_id = int(choice.split(" - ")[0])
            sol_name = " - ".join(choice.split(" - ")[1:])
            self.experiment_target_solution_id = sol_id
            self.experiment_target_solution_name = sol_name
            self.selected_solution_for_experiment = choice
        except Exception:
            pass

    def open_add_experiment(self, sol_id: int, sol_name: str):
        """Sets the target solution for a new experiment (called from a solution card)."""
        self.experiment_target_solution_id = sol_id
        self.experiment_target_solution_name = sol_name
        self.selected_solution_for_experiment = f"{sol_id} - {sol_name}"
        self.editing_experiment_id = -1
        self.new_experiment_name = ""
        self.new_experiment_assumption = ""
        self.new_experiment_description = ""
        self.new_experiment_success_metric = ""
        self.new_experiment_method = "Prototype Interview"
        self.new_experiment_method_other = ""

    def add_experiment(self, opportunity_id: int):
        """Creates a new experiment (or saves an edit) and bumps the solution to 'Testing'."""
        if self.is_viewer:
            return
        if not self.new_experiment_name.strip():
            return rx.window_alert("Experiment name cannot be empty.")
        method = (
            self.new_experiment_method_other.strip() or "Other"
            if self.new_experiment_method == "Other"
            else self.new_experiment_method
        )
        with rx.session() as session:
            if self.editing_experiment_id != -1:
                # Edit path: update existing experiment fields
                exp = session.get(Experiment, self.editing_experiment_id)
                if exp:
                    old_name = exp.name
                    old_method = exp.method
                    exp.name = self.new_experiment_name.strip()
                    exp.assumption = self.new_experiment_assumption.strip()
                    exp.description = self.new_experiment_description.strip()
                    exp.success_metric = self.new_experiment_success_metric.strip()
                    exp.method = method
                    exp.updated_by_user_id = self.auth_user_id
                    exp.updated_at = datetime.now(timezone.utc)
                    session.add(exp)
                    sol = session.get(Solution, exp.solution_id)
                    opp = session.get(Opportunity, sol.opportunity_id) if sol else None
                    changes: dict = {}
                    if old_name != exp.name:
                        changes["name"] = {"from": old_name[:80], "to": exp.name[:80]}
                    if old_method != exp.method:
                        changes["method"] = {"from": old_method, "to": exp.method}
                    session.add(AuditLog(
                        user_id=self.auth_user_id,
                        product_id=opp.product_id if opp else None,
                        entity_type="experiment",
                        entity_id=exp.id,
                        action="update",
                        detail=json.dumps({"solution_id": exp.solution_id, "changes": changes}),
                    ))
            else:
                # Create path: new experiment + auto-bump solution to Testing
                new_exp = Experiment(
                    solution_id=self.experiment_target_solution_id,
                    name=self.new_experiment_name.strip(),
                    assumption=self.new_experiment_assumption.strip(),
                    description=self.new_experiment_description.strip(),
                    success_metric=self.new_experiment_success_metric.strip(),
                    method=method,
                    created_by_user_id=self.auth_user_id,
                )
                session.add(new_exp)
                session.commit()
                session.refresh(new_exp)
                sol = session.get(Solution, self.experiment_target_solution_id)
                if sol and sol.status == "Ideation":
                    sol.status = "Testing"
                    session.add(sol)
                opp = session.get(Opportunity, sol.opportunity_id) if sol else None
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=opp.product_id if opp else None,
                    entity_type="experiment",
                    entity_id=new_exp.id,
                    action="create",
                    detail=json.dumps({
                        "name": new_exp.name[:80],
                        "solution_id": new_exp.solution_id,
                        "method": new_exp.method,
                    }),
                ))
            session.commit()
        # reset form
        self.editing_experiment_id = -1
        self.experiment_target_solution_id = -1
        self.experiment_target_solution_name = ""
        self.selected_solution_for_experiment = ""
        self.new_experiment_name = ""
        self.new_experiment_assumption = ""
        self.new_experiment_description = ""
        self.new_experiment_success_metric = ""
        self.new_experiment_method_other = ""
        self._load_and_sync()

    def update_experiment_status(self, exp_id: int, status: str):
        """Advances Draft → Running → Concluded."""
        if self.is_viewer:
            return
        with rx.session() as session:
            exp = session.get(Experiment, exp_id)
            if exp:
                old_status = exp.status
                exp.status = status
                exp.updated_by_user_id = self.auth_user_id
                exp.updated_at = datetime.now(timezone.utc)
                sol = session.get(Solution, exp.solution_id)
                opp = session.get(Opportunity, sol.opportunity_id) if sol else None
                session.add(exp)
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=opp.product_id if opp else None,
                    entity_type="experiment",
                    entity_id=exp_id,
                    action="status_change",
                    detail=f'{{"from": "{old_status}", "to": "{status}"}}',
                ))
                session.commit()
        self._load_and_sync()

    def update_experiment_signal(self, exp_id: int, signal: str):
        """Marks an experiment as Validated or Invalidated."""
        if self.is_viewer:
            return
        with rx.session() as session:
            exp = session.get(Experiment, exp_id)
            if exp:
                old_signal = exp.signal
                exp.signal = signal
                sol = session.get(Solution, exp.solution_id)
                opp = session.get(Opportunity, sol.opportunity_id) if sol else None
                session.add(exp)
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=opp.product_id if opp else None,
                    entity_type="experiment",
                    entity_id=exp_id,
                    action="status_change",
                    detail=f'{{"field": "signal", "from": "{old_signal}", "to": "{signal}"}}',
                ))
                session.commit()
        self._load_and_sync()

    def delete_experiment(self, exp_id: int):
        if self.is_viewer:
            return
        with rx.session() as session:
            exp = session.get(Experiment, exp_id)
            if exp:
                # Resolve product_id via solution → opportunity chain
                sol = session.get(Solution, exp.solution_id)
                opp = session.get(Opportunity, sol.opportunity_id) if sol else None
                prod_id = opp.product_id if opp else None
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=prod_id,
                    entity_type="experiment",
                    entity_id=exp_id,
                    action="delete",
                    detail=f'{{"name": "{exp.name[:120].replace(chr(34), chr(39))}"}}',
                ))
                session.delete(exp)
                session.commit()
        self._load_and_sync()

    _STANDARD_METHODS = {"Prototype Interview", "Fake Door", "A/B Test", "Usability Test", "Survey", "Other"}

    def start_edit_experiment(self, exp: ExperimentItem):
        """Populates the creation form with an existing experiment's data for editing."""
        self.editing_experiment_id = exp.id
        self.new_experiment_name = exp.name
        self.new_experiment_assumption = exp.assumption
        self.new_experiment_description = exp.description
        self.new_experiment_success_metric = exp.success_metric
        if exp.method in self._STANDARD_METHODS:
            self.new_experiment_method = exp.method
            self.new_experiment_method_other = ""
        else:
            self.new_experiment_method = "Other"
            self.new_experiment_method_other = exp.method
        self.experiment_target_solution_id = exp.solution_id
        self.experiment_target_solution_name = exp.solution_name
        self.selected_solution_for_experiment = f"{exp.solution_id} - {exp.solution_name}"

    def update_experiment_evidence(self, exp_id: int, notes: str):
        """Saves evidence notes for a concluded experiment."""
        if self.is_viewer:
            return
        with rx.session() as session:
            exp = session.get(Experiment, exp_id)
            if exp:
                exp.evidence_notes = notes
                session.add(exp)
                session.commit()
        self._load_and_sync()

    def apply_solution_outcome(self, exp_id: int):
        """Applies the experiment's signal as the solution's outcome status (user-confirmed)."""
        if self.is_viewer:
            return
        with rx.session() as session:
            exp = session.get(Experiment, exp_id)
            if exp:
                sol = session.get(Solution, exp.solution_id)
                if sol:
                    old_status = sol.status
                    sol.status = "Shipped" if exp.signal == "Validated" else "Discarded"
                    session.add(sol)
                    opp = session.get(Opportunity, sol.opportunity_id) if sol.opportunity_id else None
                    session.add(AuditLog(
                        user_id=self.auth_user_id,
                        product_id=opp.product_id if opp else None,
                        entity_type="solution",
                        entity_id=sol.id,
                        action="status_change",
                        detail=json.dumps({"from": old_status, "to": sol.status, "via_experiment_id": exp_id}),
                    ))
                    session.commit()
        self._load_and_sync()

    def update_opp_score(self, opp_id: int, field: str, score_str: str):
        """Updates impact_score or sat_gap_score for an opportunity (1-5, 0 = unrated)."""
        if self.is_viewer:
            return
        try:
            score = int(score_str)
        except ValueError:
            return
        score = max(0, min(5, score))
        with rx.session() as session:
            opp = session.get(Opportunity, opp_id)
            if opp:
                if field == "impact":
                    opp.impact_score = score
                elif field == "sat_gap":
                    opp.sat_gap_score = score
                session.add(opp)
                session.commit()
        self._load_and_sync()

    # ── Evidence dropdown filter ──────────────────────────────────────────────

    @rx.var
    def available_interview_choices(self) -> list[str]:
        """Interview choices with already-linked interviews filtered out for the selected opportunity."""
        linked_ids = {e.interview_id for e in self.selected_opportunity.evidence}
        return [
            choice for choice in self.interview_choices
            if int(choice.split(" - ")[0]) not in linked_ids
        ]

    # ── Merge opportunity ─────────────────────────────────────────────────────

    @rx.var
    def merge_target_choices(self) -> list[str]:
        """All opportunities except the current merge source, formatted as 'id - statement'."""
        return [
            f"{item.opportunity_id} - {item.opportunity}"
            for item in self.ledger_data
            if item.opportunity_id != self.merge_source_opp_id
        ]

    @rx.var
    def merge_source_statement(self) -> str:
        for item in self.ledger_data:
            if item.opportunity_id == self.merge_source_opp_id:
                return item.opportunity
        return ""

    @rx.var
    def merge_source_theme(self) -> str:
        for item in self.ledger_data:
            if item.opportunity_id == self.merge_source_opp_id:
                return item.theme
        return ""

    @rx.var
    def merge_target_statement(self) -> str:
        for item in self.ledger_data:
            if item.opportunity_id == self.merge_target_opp_id:
                return item.opportunity
        return ""

    @rx.var
    def merge_target_theme(self) -> str:
        for item in self.ledger_data:
            if item.opportunity_id == self.merge_target_opp_id:
                return item.theme
        return ""

    def open_merge_dialog(self, opp_id: int):
        self.merge_source_opp_id = opp_id
        self.merge_target_opp_id = -1
        self.merge_keep_statement = "target"
        self.merge_keep_theme = "target"
        self.is_merge_dialog_open = True

    def close_merge_dialog(self, _open: bool = False):
        self.is_merge_dialog_open = False
        self.merge_source_opp_id = -1
        self.merge_target_opp_id = -1
        self.merge_keep_statement = "target"
        self.merge_keep_theme = "target"

    def set_merge_target(self, val: str):
        try:
            self.merge_target_opp_id = int(val.split(" - ")[0])
        except Exception:
            self.merge_target_opp_id = -1

    def set_merge_keep_statement(self, val: str):
        self.merge_keep_statement = val

    def set_merge_keep_theme(self, val: str):
        self.merge_keep_theme = val

    def confirm_merge(self):
        """Merges source opportunity into target, transferring all evidence, solutions, and outcome links."""
        if self.is_viewer:
            return
        src_id = self.merge_source_opp_id
        tgt_id = self.merge_target_opp_id
        if src_id == -1 or tgt_id == -1:
            return

        with rx.session() as session:
            src = session.get(Opportunity, src_id)
            tgt = session.get(Opportunity, tgt_id)
            if not src or not tgt:
                return

            # 1. Transfer evidence (InterviewOpportunityLink) — dedup by interview_id
            existing_tgt_interviews = {
                link.interview_id
                for link in session.exec(
                    select(InterviewOpportunityLink).where(
                        InterviewOpportunityLink.opportunity_id == tgt_id
                    )
                ).all()
            }
            src_evidence = session.exec(
                select(InterviewOpportunityLink).where(
                    InterviewOpportunityLink.opportunity_id == src_id
                )
            ).all()
            for link in src_evidence:
                if link.interview_id not in existing_tgt_interviews:
                    link.opportunity_id = tgt_id
                    session.add(link)
                else:
                    session.delete(link)

            # 2. Transfer outcome links (OutcomeOpportunityLink) — dedup by outcome_id
            existing_tgt_outcomes = {
                link.outcome_id
                for link in session.exec(
                    select(OutcomeOpportunityLink).where(
                        OutcomeOpportunityLink.opportunity_id == tgt_id
                    )
                ).all()
            }
            src_outcome_links = session.exec(
                select(OutcomeOpportunityLink).where(
                    OutcomeOpportunityLink.opportunity_id == src_id
                )
            ).all()
            for link in src_outcome_links:
                if link.outcome_id not in existing_tgt_outcomes:
                    link.opportunity_id = tgt_id
                    session.add(link)
                else:
                    session.delete(link)

            # 3. Transfer solutions (experiments follow automatically via solution_id)
            src_solutions = session.exec(
                select(Solution).where(Solution.opportunity_id == src_id)
            ).all()
            for sol in src_solutions:
                sol.opportunity_id = tgt_id
                session.add(sol)

            # 4. Re-parent child opportunities that pointed to source
            child_opps = session.exec(
                select(Opportunity).where(Opportunity.parent_id == src_id)
            ).all()
            for child in child_opps:
                child.parent_id = tgt_id
                session.add(child)

            # 5. Apply chosen statement / theme to target
            if self.merge_keep_statement == "source":
                tgt.statement = src.statement
            if self.merge_keep_theme == "source":
                tgt.theme = src.theme
            session.add(tgt)

            session.commit()

            # 6. Delete source (all dependents have been moved)
            session.delete(src)
            session.commit()

        self.close_merge_dialog()
        self._load_and_sync()

        # If the user was viewing the source opportunity detail, redirect to the list
        if self.selected_opportunity_id == src_id:
            return rx.redirect("/opportunities")

