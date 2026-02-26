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
)
from .core import (
    PersonaBadge,
    QuoteItem,
    SolutionItem,
    OutcomeItem,
    LedgerItem,
)


class LedgerStateMixin(rx.State, mixin=True):
    """Global ledger, drawer workspace, outcomes, solutions, and evidence state mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

    @rx.var
    def selectable_outcomes(self) -> list[str]:
        """Names of outcomes plus a None/unmapped option."""
        return ["None (Unmapped)"] + [o.name for o in self.outcomes]

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

            # 1. BULLETPROOF FLATTENING (Handles Cycles & Orphans)
            opp_children_map = {}
            opp_top_level = []

            for opp in opportunities:
                # Only treat as a child if the parent actually exists in the DB
                if opp.parent_id and opp.parent_id in opp_dict:
                    opp_children_map.setdefault(opp.parent_id, []).append(opp)
                else:
                    opp_top_level.append(opp)

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
            now = datetime.now(timezone.utc)

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
                    )
                )

            # Remove the alphabetical sort to preserve tree order!
            self.ledger_data = new_ledger

            # Generate choices for the Parent Select dropdown
            self.parent_opp_choices = ["None"] + [
                f"{item.opportunity_id} - {item.opportunity[:50]}..."
                for item in new_ledger
            ]

            self.available_personas = list(personas_set)
            if self.available_personas and not self.target_persona:
                self.target_persona = self.available_personas[0]

            all_interviews = session.exec(select(Interview)).all()
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

    # Drawer / workspace
    def open_drawer(self, item: LedgerItem):
        """Opens the workspace and syncs state to the selected opportunity."""
        self.selected_opportunity = item

        if len(item.linked_outcomes) > 0:
            self.selected_opp_outcome_name = item.linked_outcomes[0].name
        else:
            self.selected_opp_outcome_name = "None (Unmapped)"

        self.cancel_edit()
        self.is_drawer_open = True

    def close_drawer(self):
        self.is_drawer_open = False

    def handle_drawer_change(self, is_open: bool):
        """Catches when the drawer is opened/closed via UI."""
        self.is_drawer_open = is_open

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

        def delete_recursive(session: rx.session, sol_id: int):
            children = session.exec(
                select(Solution).where(Solution.parent_id == sol_id)
            ).all()
            for c in children:
                delete_recursive(session, c.id)
            sol = session.get(Solution, sol_id)
            if sol:
                session.delete(sol)

        with rx.session() as session:
            delete_recursive(session, solution_id)
            session.commit()

        self.load_ledger()
        self._sync_drawer()

    def start_edit_solution(self, sol: SolutionItem):
        """Populates the input form with an existing solution's data."""
        self.editing_solution_id = sol.id
        self.new_solution_name = sol.name
        self.new_solution_desc = sol.description

    def _sync_drawer(self):
        """Refreshes the drawer UI after database changes."""
        if self.selected_opportunity and self.selected_opportunity.opportunity_id != 0:
            for item in self.ledger_data:
                if item.opportunity_id == self.selected_opportunity.opportunity_id:
                    self.selected_opportunity = item
                    self.selected_opp_outcome_name = (
                        item.linked_outcomes[0].name
                        if len(item.linked_outcomes) > 0
                        else ""
                    )
                    break

    def add_manual_solution(self, opportunity_id: int):
        """Saves a human-brainstormed solution or updates an existing one."""
        if not self.new_solution_name.strip():
            return rx.window_alert("Solution name cannot be empty.")

        with rx.session() as session:
            if self.editing_solution_id != -1:
                sol = session.get(Solution, self.editing_solution_id)
                if sol:
                    sol.name = self.new_solution_name.strip()
                    sol.description = self.new_solution_desc.strip()
                    session.add(sol)
            else:
                new_sol = Solution(
                    opportunity_id=opportunity_id,
                    parent_id=(
                        self.target_parent_id if self.target_parent_id != -1 else None
                    ),
                    name=self.new_solution_name.strip(),
                    description=self.new_solution_desc.strip(),
                )
                session.add(new_sol)
            session.commit()

        self.editing_solution_id = -1
        self.target_parent_id = -1
        self.target_parent_name = ""
        self.new_solution_name = ""
        self.new_solution_desc = ""

        self.load_ledger()
        self._sync_drawer()

    # Outcomes
    def create_outcome(self):
        """Creates a new top-level business outcome."""
        if not self.new_outcome_name.strip():
            return
        with rx.session() as session:
            new_out = Outcome(
                name=self.new_outcome_name.strip(),
                description="",
                product_id=int(self.active_product_id),
            )
            session.add(new_out)
            session.commit()

        self.active_outcome_name = self.new_outcome_name.strip()
        self.new_outcome_name = ""
        self.load_outcomes()
        self.load_ledger()

    def change_outcome_filter(self, name: str):
        """Changes the global board filter and reloads."""
        self.active_outcome_name = name
        self.load_ledger()

    def set_primary_outcome(self, outcome_name: str):
        """Forces an opportunity to have only ONE primary outcome, or none."""
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

        self.load_ledger()
        self._sync_drawer()

    # Opportunity CRUD
    def handle_opp_dialog_change(self, is_open: bool):
        self.is_opp_dialog_open = is_open
        if not is_open:
            self.editing_opp_id = -1
            self.manual_opp_theme = "Uncategorized"
            self.manual_opp_statement = ""
            self.manual_opp_parent_id = "None"

    def open_opp_dialog(self):
        self.editing_opp_id = -1
        self.manual_opp_theme = "Uncategorized"
        self.manual_opp_statement = ""
        self.manual_opp_parent_id = "None"
        self.is_opp_dialog_open = True

    def close_opp_dialog(self):
        self.is_opp_dialog_open = False

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

        self.is_opp_dialog_open = True

    def save_manual_opportunity(self):
        """Handles both creating a new opportunity and updating an existing one."""
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

            if self.editing_opp_id != -1:
                opp = session.get(Opportunity, self.editing_opp_id)
                if opp:
                    opp.theme = self.manual_opp_theme.strip()
                    opp.statement = self.manual_opp_statement.strip()
                    opp.parent_id = parent_id_val
                    session.add(opp)

                    # Inherit outcomes if we just assigned a parent and it currently has none
                    existing_outcomes = session.exec(
                        select(OutcomeOpportunityLink).where(
                            OutcomeOpportunityLink.opportunity_id == opp.id
                        )
                    ).all()
                    if len(existing_outcomes) == 0 and parent_outcome_ids:
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
                )
                session.add(new_opp)
                session.commit()
                session.refresh(new_opp)

                # Automatically inherit outcomes from parent on creation
                for out_id in parent_outcome_ids:
                    session.add(
                        OutcomeOpportunityLink(
                            opportunity_id=new_opp.id, outcome_id=out_id
                        )
                    )

            session.commit()

        self.close_opp_dialog()
        self.load_ledger()
        self._sync_drawer()

    def delete_opportunity(self, opp_id: int):
        """Safely deletes an opportunity and all nested relationships."""
        with rx.session() as session:
            opp = session.get(Opportunity, opp_id)
            if not opp:
                return

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

        if (
            self.selected_opportunity
            and self.selected_opportunity.opportunity_id == opp_id
        ):
            self.close_drawer()

        self.load_ledger()

    # Evidence mapping
    def add_real_evidence(self, opportunity_id: int):
        """Links a missed quote from a real interview to this opportunity."""
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
            session.commit()

        self.manual_quote_text = ""
        self.selected_interview_choice = ""
        self.load_ledger()
        self._sync_drawer()

    def delete_evidence(self, opportunity_id: int, interview_id: int):
        """Unlinks an interview quote from an opportunity."""
        with rx.session() as session:
            link = session.get(InterviewOpportunityLink, (interview_id, opportunity_id))
            if link:
                session.delete(link)
                session.commit()

        self.load_ledger()
        self._sync_drawer()
