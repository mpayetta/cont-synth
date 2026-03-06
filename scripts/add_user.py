"""
Add a new user to the database.

Usage:
    python scripts/add_user.py <username> <fullname> <password> [--role admin|user]

Examples:
    python scripts/add_user.py alice "Alice Smith" secret123
    python scripts/add_user.py bob "Bob Jones" pass456 --role admin
"""
import argparse
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import create_engine, Session, select
from cont_synth.models import User
from cont_synth.state.auth import _hash_password


def get_engine():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Default local dev PostgreSQL URL (same as Reflex default)
        db_url = "postgresql://postgres:password@localhost:5432/cont_synth"
    return create_engine(db_url)


def add_user(username: str, fullname: str, password: str, role: str = "user"):
    engine = get_engine()
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            print(f"Error: user '{username}' already exists.")
            sys.exit(1)

        user = User(
            username=username,
            fullname=fullname,
            password_hash=_hash_password(password),
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"Created user '{username}' (id={user.id}, role={role})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a user to cont-synth.")
    parser.add_argument("username", help="Login username")
    parser.add_argument("fullname", help="Display name")
    parser.add_argument("password", help="Plain-text password (will be hashed)")
    parser.add_argument(
        "--role",
        choices=["user", "admin"],
        default="user",
        help="User role (default: user)",
    )
    args = parser.parse_args()
    add_user(args.username, args.fullname, args.password, args.role)
