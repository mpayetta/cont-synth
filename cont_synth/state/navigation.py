import reflex as rx
from sqlmodel import select
from ..models import Product
from .core import ProductItem
from ..models import (
    Product,
    Opportunity,
    Outcome,
    Interview,
    Solution,
    OutcomeOpportunityLink,
    InterviewOpportunityLink,
)


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
        """Switches the global product context and triggers a data refresh."""
        self.active_product_id = product_id
        self.load_data_for_current_view()

    def handle_navigation(self, view_name: str):
        """Safely handles view routing."""
        self.current_view = view_name
        self.load_data_for_current_view()

    def load_data_for_current_view(self):
        """The Master Data Router: Loads specific domain data based on the active product."""
        self.load_products()
        if self.current_view == "logs":
            self.load_history()
        elif self.current_view in ["ledger", "tree", "prep"]:
            self.load_ledger()  # Ledger loads outcomes, opportunities, and personas

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
