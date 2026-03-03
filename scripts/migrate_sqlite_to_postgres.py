#!/usr/bin/env python3
"""Migrates all data from the SQLite database (reflex.db) into PostgreSQL.

Prerequisites:
    The PostgreSQL schema must already exist before running this script:
        alembic upgrade head

Usage (local dev — both defaults apply):
    python scripts/migrate_sqlite_to_postgres.py

Usage (server — point at a remote SQLite file and/or a remote PG instance):
    DATABASE_URL=postgresql://user:pass@host/db \\
        python scripts/migrate_sqlite_to_postgres.py --sqlite-path /path/to/reflex.db

Optional flags:
    --sqlite-path   Path to reflex.db  (default: ./reflex.db next to this repo)
    --postgres-url  PostgreSQL DSN     (default: $DATABASE_URL, then local dev)
"""

import argparse
import os
import sys

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, text

# ── Constants ──────────────────────────────────────────────────────────────────

# Alembic's own version table — never touch it.
SKIP_TABLES = {"alembic_version"}

# Insertion order must respect FK dependencies so that referenced rows exist
# before referencing rows are inserted.
#
# For the two self-referential tables (opportunity.parent_id → opportunity.id
# and solution.parent_id → solution.id) we rely on FK enforcement being
# temporarily suspended (see Step 2 below) rather than a full topological sort.
# Rows are still fetched in SQLite rowid order, which equals insertion order,
# so parents (lower id, created first) naturally precede their children.
TABLE_ORDER = [
    "persona",
    "product",
    "user",
    "outcome",
    "opportunity",               # self-ref: parent_id → opportunity.id
    "outcomeopportunitylink",
    "interview",
    "interviewopportunitylink",
    "solution",                  # self-ref: parent_id → solution.id
    "experiment",
    "participant",
    "interviewparticipantlink",
    "llmusagelog",
    "knowledgechunk",            # new PG-only table — absent/empty in SQLite
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _reset_sequence(conn: sa.engine.Connection, table_name: str) -> None:
    """Advance the serial sequence to MAX(id)+1 so future INSERTs don't collide.

    Uses a DO block so the NULL check happens inside PostgreSQL — calling
    setval(NULL, …) would abort the transaction, which a Python try/except
    cannot prevent on the server side.
    """
    # Only attempt sequence reset when an 'id' column actually exists.
    # Bridge tables (e.g. outcomeopportunitylink) use composite PKs and have
    # no 'id' column — pg_get_serial_sequence raises an error (not NULL) for
    # columns that don't exist, so we guard with information_schema first.
    conn.execute(text(
        f"DO $$ DECLARE seq TEXT; BEGIN "
        f"  IF EXISTS ("
        f"    SELECT 1 FROM information_schema.columns "
        f"    WHERE table_name = '{table_name}' AND column_name = 'id'"
        f"  ) THEN "
        f"    seq := pg_get_serial_sequence('{table_name}', 'id'); "
        f"    IF seq IS NOT NULL THEN "
        f"      PERFORM setval(seq, COALESCE((SELECT MAX(id) FROM \"{table_name}\"), 0) + 1, false); "
        f"    END IF; "
        f"  END IF; "
        f"END $$"
    ))


# ── Core migration logic ───────────────────────────────────────────────────────

def migrate(sqlite_url: str, postgres_url: str) -> None:
    print(f"Source  (SQLite):   {sqlite_url}")
    print(f"Target  (Postgres): {postgres_url}\n")

    src_engine = create_engine(sqlite_url)
    dst_engine = create_engine(postgres_url)

    src_tables = set(inspect(src_engine).get_table_names())
    dst_tables = set(inspect(dst_engine).get_table_names())

    # Tables present on both sides (in dependency order).
    tables_to_migrate = [
        t for t in TABLE_ORDER
        if t not in SKIP_TABLES and t in src_tables and t in dst_tables
    ]
    # All destination tables we manage (superset — includes PG-only tables).
    tables_to_clear = [
        t for t in TABLE_ORDER
        if t not in SKIP_TABLES and t in dst_tables
    ]

    with src_engine.connect() as src, dst_engine.connect() as dst:

        # ── Step 1: Suspend FK enforcement ────────────────────────────────────
        # Do this FIRST, before clearing, so individual DELETEs don't need to
        # respect FK order and don't block waiting for referencing rows to go.
        #
        # Requires SUPERUSER or REPLICATION privilege on the connecting role.
        # The default 'postgres' user on self-hosted instances always has this.
        # On managed clouds (RDS, Cloud SQL, Supabase) use the admin user.
        dst.execute(text("SET session_replication_role = 'replica'"))

        # ── Step 2: Wipe destination tables ───────────────────────────────────
        # DELETE one table at a time rather than a single TRUNCATE so we never
        # need an ACCESS EXCLUSIVE lock on all tables simultaneously — which
        # would block (or deadlock) if the Reflex app or any other connection
        # is still open.  With FK enforcement off (step 1) order doesn't matter.
        if tables_to_clear:
            print(f"Clearing {len(tables_to_clear)} destination tables …")
            for table_name in reversed(tables_to_clear):
                dst.execute(text(f'DELETE FROM "{table_name}"'))
            print()

        # ── Step 3: Copy rows ─────────────────────────────────────────────────
        dst_meta = sa.MetaData()
        dst_meta.reflect(bind=dst_engine)

        total_rows = 0
        for table_name in tables_to_migrate:
            # Fetch from SQLite in rowid order (= insertion order = id order).
            rows = (
                src.execute(text(f'SELECT * FROM "{table_name}" ORDER BY rowid'))
                .mappings()
                .all()
            )
            if not rows:
                print(f"  [skip] {table_name!r}  (0 rows in source)")
                continue

            dst.execute(dst_meta.tables[table_name].insert(), [dict(r) for r in rows])
            total_rows += len(rows)
            print(f"  [ ok ] {table_name!r}  ({len(rows):,} rows)")

        # ── Step 4: Fix sequences after INSERT ────────────────────────────────
        # INSERTs with explicit ids don't advance the sequence, so nudge each
        # one past the highest migrated id so future app INSERTs don't collide.
        for table_name in tables_to_migrate:
            _reset_sequence(dst, table_name)

        # ── Step 5: Re-enable FK enforcement ──────────────────────────────────
        dst.execute(text("SET session_replication_role = 'origin'"))

        dst.commit()

    print(f"\n✓  Done — {total_rows:,} rows migrated across {len(tables_to_migrate)} tables.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_sqlite = os.path.join(repo_root, "reflex.db")
    default_pg = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/contsynth",
    )

    parser = argparse.ArgumentParser(
        description="Migrate cont-synth data from SQLite → PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--sqlite-path",
        default=default_sqlite,
        help=f"Path to reflex.db  (default: {default_sqlite})",
    )
    parser.add_argument(
        "--postgres-url",
        default=default_pg,
        help="PostgreSQL DSN  (default: $DATABASE_URL or local dev instance)",
    )
    args = parser.parse_args()

    sqlite_path = os.path.abspath(args.sqlite_path)
    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite file not found: {sqlite_path}", file=sys.stderr)
        sys.exit(1)

    migrate(f"sqlite:///{sqlite_path}", args.postgres_url)


if __name__ == "__main__":
    main()
