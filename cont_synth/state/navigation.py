import reflex as rx
from datetime import date, timedelta
from sqlmodel import select
from .core import LlmUsageItem, ProductItem, DashboardBarItem, RecentInterviewItem
from ..models import (
    Product,
    LlmUsageLog,
    Opportunity,
    Outcome,
    Interview,
    Solution,
    Experiment,
    Persona,
    OutcomeOpportunityLink,
    InterviewOpportunityLink,
)

_PERSONA_COLORS = [
    "blue", "purple", "orange", "green", "pink", "teal", "ruby", "iris", "indigo",
]


def _persona_color(name: str) -> str:
    return _PERSONA_COLORS[sum(ord(c) for c in name) % len(_PERSONA_COLORS)]


class NavigationStateMixin(rx.State, mixin=True):

    def load_products(self):
        """Fetches all products and ensures an active product is selected."""
        with rx.session() as session:
            db_products = session.exec(select(Product)).all()
            if not db_products:
                # Failsafe if the database migration seed was skipped
                default_prod = Product(id=1, name="Default Product")
                session.add(default_prod)
                session.commit()
                db_products = [default_prod]

            self.products = [ProductItem(id=p.id, name=p.name) for p in db_products]

            # Ensure the active product actually exists
            if not any(str(p.id) == self.active_product_id for p in self.products):
                self.active_product_id = str(self.products[0].id)

    def change_product(self, product_id: str):
        """Switches the global product context, persists to localStorage, and refreshes data."""
        self.active_product_id = product_id
        self.load_data_for_current_view()
        return rx.call_script(f"localStorage.setItem('active_product_id', '{product_id}')")

    def handle_navigation(self, view_name: str):
        """Safely handles view routing."""
        self.current_view = view_name
        self.highlighted_quote_text = ""
        self.load_data_for_current_view()

    def load_llm_usage(self):
        """Fetches all LLM usage log rows for the dashboard."""
        with rx.session() as session:
            rows = session.exec(
                select(LlmUsageLog).order_by(LlmUsageLog.created_at.desc())
            ).all()
            self.llm_usage_logs = [
                LlmUsageItem(
                    id=r.id,
                    model_name=r.model_name,
                    operation=r.operation,
                    interview_id=r.interview_id if r.interview_id is not None else 0,
                    prompt_tokens=r.prompt_tokens,
                    output_tokens=r.output_tokens,
                    total_tokens=r.total_tokens,
                    created_at=r.created_at.strftime("%Y-%m-%d %H:%M"),
                )
                for r in rows
            ]

    def load_data_for_current_view(self):
        """The Master Data Router: Loads specific domain data based on the active product."""
        self.load_products()
        if self.current_view == "home":
            self.load_dashboard()
        elif self.current_view == "logs":
            self.load_history()
        elif self.current_view == "ledger":
            self.load_ledger()  # Ledger loads outcomes, opportunities, and personas
        elif self.current_view == "prep":
            self.load_ledger()  # loads available_personas for the persona selector
            self.load_prep_data()  # loads opportunities and running experiments for OST selectors
        elif self.current_view == "llm_usage":
            self.load_llm_usage()
        elif self.current_view == "participants":
            self.load_participants()
        # "interview_detail" and "opportunity" carry their data from the navigation event

    def load_dashboard(self):
        """Loads all data needed for the home dashboard."""
        prod_id = int(self.active_product_id)
        today = date.today()
        MAX_BAR_HEIGHT = 48  # pixels

        with rx.session() as session:
            # ── Interview cadence ─────────────────────────────────────────────
            interviews = session.exec(
                select(Interview)
                .where(Interview.product_id == prod_id)
                .order_by(Interview.date_logged.desc())
            ).all()

            self.dashboard_total_interviews = len(interviews)

            # Compute effective date for each interview (prefer interview_date over date_logged)
            def _eff_date(inv) -> date | None:
                if inv.interview_date:
                    try:
                        return date.fromisoformat(inv.interview_date)
                    except (ValueError, TypeError):
                        pass
                return inv.date_logged.date() if inv.date_logged else None

            # Days since most recent interview
            max_idate: date | None = None
            for inv in interviews:
                d = _eff_date(inv)
                if d and (max_idate is None or d > max_idate):
                    max_idate = d
            self.dashboard_days_since_last = (today - max_idate).days if max_idate else -1

            # Weekly counts: index 0 = current week (0–6 days ago), 7 = 7 weeks ago
            weekly_counts = [0] * 8
            for inv in interviews:
                d = _eff_date(inv)
                if d:
                    days_ago = (today - d).days
                    if 0 <= days_ago <= 55:
                        week_idx = days_ago // 7
                        if week_idx < 8:
                            weekly_counts[week_idx] += 1

            max_count = max(weekly_counts) if any(weekly_counts) else 1
            bars: list[DashboardBarItem] = []
            for i in range(7, -1, -1):  # oldest (7 weeks ago) → newest (current)
                week_start = today - timedelta(days=i * 7 + 6)
                cnt = weekly_counts[i]
                h = int(cnt * MAX_BAR_HEIGHT / max_count) if cnt > 0 else 0
                bars.append(DashboardBarItem(
                    week_label=week_start.strftime("%b %d"),
                    count=cnt,
                    height_css=f"{h}px",
                ))
            self.dashboard_weekly_bars = bars

            # ── Opportunity health ────────────────────────────────────────────
            opps = session.exec(
                select(Opportunity).where(Opportunity.product_id == prod_id)
            ).all()
            opp_ids = [o.id for o in opps]
            self.dashboard_total_opps = len(opp_ids)

            if opp_ids:
                evidence_links = session.exec(
                    select(InterviewOpportunityLink).where(
                        InterviewOpportunityLink.opportunity_id.in_(opp_ids)
                    )
                ).all()
                self.dashboard_opps_with_evidence = len(
                    set(lnk.opportunity_id for lnk in evidence_links)
                )

                solutions = session.exec(
                    select(Solution).where(Solution.opportunity_id.in_(opp_ids))
                ).all()
                self.dashboard_opps_with_solutions = len(
                    set(s.opportunity_id for s in solutions)
                )
                self.dashboard_solutions_testing = sum(
                    1 for s in solutions if s.status == "Testing"
                )

                sol_ids = [s.id for s in solutions]
                experiments = (
                    session.exec(
                        select(Experiment).where(Experiment.solution_id.in_(sol_ids))
                    ).all()
                    if sol_ids
                    else []
                )
            else:
                self.dashboard_opps_with_evidence = 0
                self.dashboard_opps_with_solutions = 0
                self.dashboard_solutions_testing = 0
                experiments = []

            # ── Experiment pipeline ───────────────────────────────────────────
            self.dashboard_exp_draft = sum(1 for e in experiments if e.status == "Draft")
            self.dashboard_exp_running = sum(1 for e in experiments if e.status == "Running")
            concluded = [e for e in experiments if e.status == "Concluded"]
            self.dashboard_exp_concluded = len(concluded)
            self.dashboard_exp_validated = sum(1 for e in concluded if e.signal == "Validated")
            self.dashboard_exp_invalidated = sum(1 for e in concluded if e.signal == "Invalidated")

            # ── Recent activity feed (last 5 interviews) ──────────────────────
            recent: list[RecentInterviewItem] = []
            for inv in interviews[:5]:
                persona = session.get(Persona, inv.persona_id)
                p_name = persona.name if persona else "Unknown"
                quote_count = len(session.exec(
                    select(InterviewOpportunityLink).where(
                        InterviewOpportunityLink.interview_id == inv.id
                    )
                ).all())
                date_str = inv.interview_date or inv.date_logged.strftime("%Y-%m-%d")
                recent.append(RecentInterviewItem(
                    interview_id=inv.id,
                    persona=p_name,
                    persona_color=_persona_color(p_name),
                    date_str=date_str,
                    quote_count=quote_count,
                ))
            self.dashboard_recent_interviews = recent

    def create_product(self):
        """Creates a new workspace."""
        if not self.new_product_name.strip():
            return
        with rx.session() as session:
            new_prod = Product(name=self.new_product_name.strip())
            session.add(new_prod)
            session.commit()
            session.refresh(new_prod)
            self.active_product_id = str(new_prod.id)  # Instantly switch to it!

        self.new_product_name = ""
        self.load_data_for_current_view()

    def open_manage_product(self):
        """Sets the input to the active product's current name."""
        active_prod = next((p for p in self.products if str(p.id) == self.active_product_id), None)
        if active_prod:
            self.edit_product_name = active_prod.name

    def update_current_product(self):
        """Saves the renamed product to the database."""
        if not self.edit_product_name.strip(): return
        with rx.session() as session:
            prod = session.get(Product, int(self.active_product_id))
            if prod:
                prod.name = self.edit_product_name.strip()
                session.add(prod)
                session.commit()
        self.load_data_for_current_view() 

    def delete_current_product(self):
        """Performs a massive cascading delete to wipe the workspace completely."""
        with rx.session() as session:
            # 1. Prevent deleting the very last workspace
            all_prods = session.exec(select(Product)).all()
            if len(all_prods) <= 1:
                return rx.window_alert("Cannot delete the only workspace. Create a new one first.")

            prod_id = int(self.active_product_id)

            # 2. Delete Opportunities & all linked relationships
            opps = session.exec(select(Opportunity).where(Opportunity.product_id == prod_id)).all()
            for opp in opps:
                # Wipe Bridge Links
                for link in session.exec(select(OutcomeOpportunityLink).where(OutcomeOpportunityLink.opportunity_id == opp.id)).all():
                    session.delete(link)
                for link in session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.opportunity_id == opp.id)).all():
                    session.delete(link)
                
                # Wipe Solutions Recursively
                def delete_sol_recursive(sol_id: int):
                    children = session.exec(select(Solution).where(Solution.parent_id == sol_id)).all()
                    for c in children: delete_sol_recursive(c.id)
                    sol_to_del = session.get(Solution, sol_id)
                    if sol_to_del: session.delete(sol_to_del)

                sols = session.exec(select(Solution).where(Solution.opportunity_id == opp.id)).all()
                for s in sols: delete_sol_recursive(s.id)

                session.delete(opp)

            # 3. Delete Outcomes
            outs = session.exec(select(Outcome).where(Outcome.product_id == prod_id)).all()
            for out in outs: session.delete(out)

            # 4. Delete Interviews
            invs = session.exec(select(Interview).where(Interview.product_id == prod_id)).all()
            for inv in invs: session.delete(inv)

            # 5. Delete the Product itself
            prod = session.get(Product, prod_id)
            if prod: session.delete(prod)
            
            session.commit()

        # 6. Fallback to the first available product
        self.load_products()
        if self.products:
            self.active_product_id = str(self.products[0].id)
        self.load_data_for_current_view()
