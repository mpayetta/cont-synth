import reflex as rx


class NavigationStateMixin(rx.State, mixin=True):
    """Top-level navigation and view routing mixin.

    NOTE: Field definitions & defaults live on the concrete State class to keep
    Reflex / Pydantic happy. This mixin only provides behavior.
    """

    def handle_navigation(self, view_name: str):
        """Safely handles routing and triggers domain-specific data loads."""
        self.current_view = view_name

        # Tell each domain to load its fresh data ONLY when navigated to
        if view_name == "logs":
            self.load_history()
        elif view_name == "ledger":
            self.load_ledger()
