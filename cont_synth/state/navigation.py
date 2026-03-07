import json
import re
from collections import Counter
import reflex as rx
from datetime import date, datetime, timedelta, timezone
from sqlmodel import select
from .core import LlmUsageItem, ProductItem, DashboardBarItem, RecentInterviewItem, CoachFreqItem, WorkspaceMemberItem, AuditLogItem
from .pagination import PAGE_SIZE, apply_pagination, total_pages, clamp_page

_AUDIT_PAGE_SIZE = PAGE_SIZE  # 20 rows per page
from .auth import _hash_password
from ..models import (
    Product,
    ProductMember,
    User,
    LlmUsageLog,
    Opportunity,
    Outcome,
    Interview,
    InterviewFeedback,
    Solution,
    Experiment,
    Persona,
    AuditLog,
    OutcomeOpportunityLink,
    InterviewOpportunityLink,
)

_TS_GROUP_RE = re.compile(r'\s*\([^)]*\d+:\d{2}[^)]*\)')


def _strip_ts(text: str) -> str:
    """Remove timestamp parentheticals like ' (0:47)' or ' (6:43 \'quote\')' from a string."""
    return _TS_GROUP_RE.sub('', text).strip()


_PERSONA_COLORS = [
    "red",
    "amber",
    "green",
    "blue",
    "violet",
    "crimson",
]


def _persona_color(name: str) -> str:
    return _PERSONA_COLORS[sum(ord(c) for c in name) % len(_PERSONA_COLORS)]


_URL_MAP: dict[str, str] = {
    "home": "/",
    "synthesize": "/synthesize",
    "synthesis_review": "/review",
    "ledger": "/opportunities",
    "opportunity": "/opportunities",
    "prep": "/prep",
    "logs": "/interviews",
    "interview_detail": "/interviews",
    "llm_usage": "/llm-usage",
    "participants": "/participants",
    "account": "/account",
    "knowledge_base": "/knowledge-base",
    "members": "/workspace/members",
}


class NavigationStateMixin(rx.State, mixin=True):

    @rx.var
    def is_workspace_admin(self) -> bool:
        """True when the logged-in user is an admin of the active workspace."""
        return self.workspace_role == "admin" or self.auth_user_role == "admin"

    @rx.var
    def is_viewer(self) -> bool:
        """True when the user has read-only access to the active workspace."""
        return self.workspace_role == "viewer"

    def load_products(self):
        """Fetches all products accessible to the current user (owned + shared via ProductMember)."""
        with rx.session() as session:
            # Products owned by this user
            owned = session.exec(
                select(Product).where(Product.user_id == self.auth_user_id)
            ).all()
            owned_ids = {p.id for p in owned}

            # Products shared with this user via ProductMember
            member_rows = session.exec(
                select(ProductMember).where(ProductMember.user_id == self.auth_user_id)
            ).all()
            shared_ids = {m.product_id for m in member_rows} - owned_ids
            shared = (
                session.exec(select(Product).where(Product.id.in_(shared_ids))).all()
                if shared_ids
                else []
            )

            all_products = list(owned) + list(shared)

            if not all_products:
                # Failsafe: create a default workspace for this user
                default_prod = Product(name="Default Product", user_id=self.auth_user_id)
                session.add(default_prod)
                session.commit()
                session.refresh(default_prod)
                session.add(ProductMember(
                    product_id=default_prod.id,
                    user_id=self.auth_user_id,
                    role="admin",
                ))
                session.commit()
                all_products = [default_prod]

            self.products = [ProductItem(id=p.id, name=p.name) for p in all_products]

            # Ensure the active product is accessible to this user
            if not any(str(p.id) == self.active_product_id for p in self.products):
                self.active_product_id = str(self.products[0].id)

            # Load workspace role for the active product
            self._load_workspace_role_in_session(session)

    def _load_workspace_role_in_session(self, session) -> None:
        """Sets self.workspace_role based on the active product and current user."""
        prod_id = int(self.active_product_id)
        prod = session.get(Product, prod_id)
        if prod and prod.user_id == self.auth_user_id:
            self.workspace_role = "admin"
            return
        member = session.exec(
            select(ProductMember).where(
                ProductMember.product_id == prod_id,
                ProductMember.user_id == self.auth_user_id,
            )
        ).first()
        self.workspace_role = member.role if member else ""

    def change_product(self, product_id: str):
        """Switches the global product context, persists to localStorage, and redirects to home."""
        self.active_product_id = product_id
        rx.call_script(f"localStorage.setItem('active_product_id', '{product_id}')")
        # Refresh workspace role for the newly selected product
        with rx.session() as session:
            self._load_workspace_role_in_session(session)
        # Always reload home data — redirect to "/" won't re-mount if already on home
        self.current_view = "home"
        self.load_data_for_current_view()
        return rx.redirect("/")

    def handle_navigation(self, view_name: str):
        """Navigate to the URL corresponding to view_name."""
        self.highlighted_quote_text = ""
        if self.current_view == "prep":
            self.prep_questions = ""
            self.prep_extra_context = ""
        return rx.redirect(_URL_MAP.get(view_name, "/"))

    def load_llm_usage(self):
        """Fetches all LLM usage log rows for the dashboard. Admin-only: shows all users."""
        if self.auth_user_role != "admin":
            return
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
            self.load_ledger()
            self.load_dashboard()
        elif self.current_view == "logs":
            self.load_interview_log()
            self.load_coach_data()
        elif self.current_view == "ledger":
            self.load_ledger()  # Ledger loads outcomes, opportunities, and personas
        elif self.current_view == "prep":
            self.load_ledger()  # loads available_personas for the persona selector
            self.load_prep_data()  # loads opportunities and running experiments for OST selectors
            self.load_coach_feedback_for_prep()
            self.load_guide_history()
        elif self.current_view in ("llm_usage", "account"):
            self.load_llm_usage()
            if self.current_view == "account":
                self._prefill_account_settings()
        elif self.current_view == "participants":
            self.load_participants()
        elif self.current_view == "interview_detail":
            self.load_interview_detail_data()
        elif self.current_view == "opportunity":
            self.load_ledger()
            for item in self.ledger_data:
                if item.opportunity_id == self.selected_opportunity_id:
                    self.selected_opportunity = item
                    self.selected_opp_outcome_name = (
                        item.linked_outcomes[0].name
                        if len(item.linked_outcomes) > 0
                        else "None (Unmapped)"
                    )
                    break
            self.experiment_target_solution_id = -1
            self.experiment_target_solution_name = ""
            self.selected_solution_for_experiment = ""
            self.is_editing_opp_detail = False
            self.editing_solution_id = -1
        elif self.current_view == "knowledge_base":
            self.load_kb_documents()
        elif self.current_view == "members":
            self.load_workspace_members()

    def load_coach_data(self):
        """Loads all InterviewFeedback records for the coaching dashboard."""
        prod_id = int(self.active_product_id)
        with rx.session() as session:
            interviews = session.exec(
                select(Interview)
                .where(Interview.product_id == prod_id)
                .order_by(Interview.date_logged.asc())
            ).all()

            score_history: list[dict] = []
            all_stop: list[str] = []
            all_keep: list[str] = []

            for inv in interviews:
                fb = session.exec(
                    select(InterviewFeedback).where(InterviewFeedback.interview_id == inv.id)
                ).first()
                if fb:
                    date_str = inv.interview_date or inv.date_logged.strftime("%Y-%m-%d")
                    score_history.append({
                        "date": date_str,
                        "score": fb.score,
                        "interview_id": inv.id,
                    })
                    all_stop.extend(_strip_ts(x) for x in (json.loads(fb.stop_doing) if fb.stop_doing else []))
                    all_keep.extend(_strip_ts(x) for x in (json.loads(fb.keep_doing) if fb.keep_doing else []))

        self.coach_score_history = score_history

        stop_counts = Counter(all_stop)
        keep_counts = Counter(all_keep)
        self.coach_top_stop_doing = [
            CoachFreqItem(text=t, count=c) for t, c in stop_counts.most_common(5)
        ]
        self.coach_top_keep_doing = [
            CoachFreqItem(text=t, count=c) for t, c in keep_counts.most_common(5)
        ]

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
        """Creates a new workspace for the current user."""
        if not self.new_product_name.strip():
            return
        with rx.session() as session:
            new_prod = Product(name=self.new_product_name.strip(), user_id=self.auth_user_id)
            session.add(new_prod)
            session.commit()
            session.refresh(new_prod)
            # Create admin ProductMember entry for the creator
            session.add(ProductMember(
                product_id=new_prod.id,
                user_id=self.auth_user_id,
                role="admin",
            ))
            session.commit()
            self.active_product_id = str(new_prod.id)  # Instantly switch to it!
            self.workspace_role = "admin"

        self.new_product_name = ""
        self.load_data_for_current_view()

    def open_manage_product(self):
        """Sets the input to the active product's current name."""
        active_prod = next((p for p in self.products if str(p.id) == self.active_product_id), None)
        if active_prod:
            self.edit_product_name = active_prod.name

    def update_current_product(self):
        """Saves the renamed product to the database. Workspace admins only."""
        if not self.is_workspace_admin:
            return
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
            # 1. Only the product owner can delete the workspace
            prod_id = int(self.active_product_id)
            prod_check = session.get(Product, prod_id)
            if not prod_check or prod_check.user_id != self.auth_user_id:
                return rx.window_alert("Only the workspace owner can delete it.")

            # Prevent deleting the very last workspace owned by this user
            owned_prods = session.exec(
                select(Product).where(Product.user_id == self.auth_user_id)
            ).all()
            if len(owned_prods) <= 1:
                return rx.window_alert("Cannot delete the only workspace. Create a new one first.")

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

            # 5. Delete ProductMember rows for this product
            members = session.exec(
                select(ProductMember).where(ProductMember.product_id == prod_id)
            ).all()
            for m in members:
                session.delete(m)

            # 6. Delete the Product itself
            prod = session.get(Product, prod_id)
            if prod: session.delete(prod)

            session.commit()

        # 6. Fallback to the first available product
        self.load_products()
        if self.products:
            self.active_product_id = str(self.products[0].id)
        self.load_data_for_current_view()

    # ── Workspace Member Management ───────────────────────────────────────────

    def load_workspace_members(self):
        """Loads all members of the active product workspace. Workspace admins only."""
        if not self.is_workspace_admin:
            return
        self.open_manage_product()
        prod_id = int(self.active_product_id)
        with rx.session() as session:
            product = session.get(Product, prod_id)
            members = session.exec(
                select(ProductMember).where(ProductMember.product_id == prod_id)
            ).all()

            items: list[WorkspaceMemberItem] = []
            for m in members:
                user = session.get(User, m.user_id)
                if not user:
                    continue
                items.append(WorkspaceMemberItem(
                    member_id=m.id,
                    user_id=m.user_id,
                    username=user.username,
                    fullname=user.fullname,
                    role=m.role,
                    joined_at=m.joined_at.strftime("%Y-%m-%d") if m.joined_at else "",
                    is_owner=(product is not None and product.user_id == m.user_id),
                ))
            self.workspace_members = items
        self.load_audit_logs()

    def invite_member_to_product(self):
        """Adds an existing user by username as a member of the active workspace."""
        username = self.invite_username.strip()
        role = self.invite_role
        if not username:
            self.invite_error = "Username is required."
            return
        if not self.is_workspace_admin:
            self.invite_error = "Only workspace admins can invite members."
            return

        prod_id = int(self.active_product_id)
        with rx.session() as session:
            user = session.exec(select(User).where(User.username == username)).first()
            if not user:
                self.invite_error = f"No user found with username '{username}'."
                return

            existing = session.exec(
                select(ProductMember).where(
                    ProductMember.product_id == prod_id,
                    ProductMember.user_id == user.id,
                )
            ).first()
            if existing:
                self.invite_error = f"'{username}' is already a member of this workspace."
                return

            session.add(ProductMember(
                product_id=prod_id,
                user_id=user.id,
                role=role,
                invited_by_user_id=self.auth_user_id,
            ))
            session.commit()

        self.invite_error = ""
        self.invite_username = ""
        self.invite_role = "member"
        self.load_workspace_members()

    def remove_member(self, member_id: int):
        """Removes a user from the active workspace (admins only; cannot remove owner)."""
        if not self.is_workspace_admin:
            return
        with rx.session() as session:
            member = session.get(ProductMember, member_id)
            if not member:
                return
            prod = session.get(Product, member.product_id)
            if prod and prod.user_id == member.user_id:
                self.invite_error = "Cannot remove the workspace owner."
                return
            target_user = session.get(User, member.user_id)
            session.add(AuditLog(
                user_id=self.auth_user_id,
                product_id=member.product_id,
                entity_type="member",
                entity_id=member.user_id,
                action="delete",
                detail=f'{{"username": "{target_user.username if target_user else member.user_id}", "role": "{member.role}"}}',
            ))
            session.delete(member)
            session.commit()
        self.load_workspace_members()

    def update_member_role(self, member_id: int, new_role: str):
        """Changes the workspace role of an existing member."""
        if not self.is_workspace_admin:
            return
        with rx.session() as session:
            member = session.get(ProductMember, member_id)
            if member:
                prod = session.get(Product, member.product_id)
                if prod and prod.user_id == member.user_id and new_role != "admin":
                    self.invite_error = "Cannot demote the workspace owner."
                    return
                old_role = member.role
                member.role = new_role
                session.add(member)
                target_user = session.get(User, member.user_id)
                session.add(AuditLog(
                    user_id=self.auth_user_id,
                    product_id=member.product_id,
                    entity_type="member",
                    entity_id=member.user_id,
                    action="role_change",
                    detail=f'{{"username": "{target_user.username if target_user else member.user_id}", "from": "{old_role}", "to": "{new_role}"}}',
                ))
                session.commit()
        self.load_workspace_members()

    def create_workspace_user(self):
        """App admin creates a brand-new user and adds them to the active workspace."""
        if not self.is_admin:
            self.create_user_error = "Only app admins can create new users."
            return
        username = self.create_user_username.strip()
        fullname = self.create_user_fullname.strip()
        password = self.create_user_password
        workspace_role = self.create_user_workspace_role

        if not username or not fullname or not password:
            self.create_user_error = "Username, full name, and password are all required."
            return

        with rx.session() as session:
            if session.exec(select(User).where(User.username == username)).first():
                self.create_user_error = f"Username '{username}' is already taken."
                return

            new_user = User(
                username=username,
                fullname=fullname,
                password_hash=_hash_password(password),
                role="user",
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            session.add(ProductMember(
                product_id=int(self.active_product_id),
                user_id=new_user.id,
                role=workspace_role,
                invited_by_user_id=self.auth_user_id,
            ))
            session.commit()

        self.create_user_username = ""
        self.create_user_fullname = ""
        self.create_user_password = ""
        self.create_user_error = ""
        self.load_workspace_members()

    def load_audit_logs(self):
        """Loads a paginated, filtered page of AuditLog rows for the active workspace."""
        if not self.is_workspace_admin:
            return
        prod_id = int(self.active_product_id)
        with rx.session() as session:
            # Build filtered query
            query = select(AuditLog).where(AuditLog.product_id == prod_id)
            if self.audit_filter_action:
                query = query.where(AuditLog.action == self.audit_filter_action)
            if self.audit_filter_entity_type:
                query = query.where(AuditLog.entity_type == self.audit_filter_entity_type)

            all_rows = session.exec(query.order_by(AuditLog.created_at.desc())).all()
            self.audit_log_total = len(all_rows)

            # Clamp page
            self.audit_log_page = clamp_page(self.audit_log_page, self.audit_log_total, _AUDIT_PAGE_SIZE)

            start = self.audit_log_page * _AUDIT_PAGE_SIZE
            page_rows = all_rows[start : start + _AUDIT_PAGE_SIZE]

            # Resolve usernames in one pass
            user_cache: dict[int, str] = {}
            items: list[AuditLogItem] = []
            for r in page_rows:
                if r.user_id not in user_cache:
                    u = session.get(User, r.user_id)
                    user_cache[r.user_id] = u.username if u else f"user#{r.user_id}"
                items.append(AuditLogItem(
                    id=r.id,
                    username=user_cache[r.user_id],
                    entity_type=r.entity_type,
                    entity_id=r.entity_id,
                    action=r.action,
                    detail=r.detail or "",
                    created_at=r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                ))
            self.audit_logs = items

    @rx.var
    def audit_log_has_prev(self) -> bool:
        return self.audit_log_page > 0

    @rx.var
    def audit_log_has_next(self) -> bool:
        return (self.audit_log_page + 1) * _AUDIT_PAGE_SIZE < self.audit_log_total

    @rx.var
    def audit_log_page_label(self) -> str:
        if self.audit_log_total == 0:
            return "No results"
        start = self.audit_log_page * _AUDIT_PAGE_SIZE + 1
        end = min(start + _AUDIT_PAGE_SIZE - 1, self.audit_log_total)
        return f"{start}–{end} of {self.audit_log_total}"
