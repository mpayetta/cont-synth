"""
Shared server-side pagination utilities.

Usage example (in a state mixin):

    from .pagination import PAGE_SIZE, apply_pagination, total_pages

    def load_my_data(self):
        with rx.session() as session:
            total = session.exec(select(func.count(MyModel.id)).where(...)).one()
            self.my_total = total

            rows = session.exec(
                apply_pagination(
                    select(MyModel).where(...).order_by(MyModel.created_at.desc()),
                    self.my_page,
                )
            ).all()
            ...

    def my_next_page(self):
        if self.my_page < total_pages(self.my_total) - 1:
            self.my_page += 1
            self.load_my_data()

    def my_prev_page(self):
        if self.my_page > 0:
            self.my_page -= 1
            self.load_my_data()
"""

PAGE_SIZE: int = 20


def apply_pagination(query, page: int, page_size: int = PAGE_SIZE):
    """Apply .offset() and .limit() to any SQLModel select query."""
    return query.offset(page * page_size).limit(page_size)


def total_pages(total: int, page_size: int = PAGE_SIZE) -> int:
    """Return total page count (minimum 1)."""
    if page_size <= 0:
        return 1
    return max(1, (total + page_size - 1) // page_size)


def clamp_page(page: int, total: int, page_size: int = PAGE_SIZE) -> int:
    """Clamp page index to a valid range [0, total_pages - 1]."""
    return max(0, min(page, total_pages(total, page_size) - 1))
