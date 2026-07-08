"""Org store: persistent org -> plan lookup (Phase 11).

Holds each tenant's plan, which drives the monthly extraction quota. Backed by
SQLite in production (durable across restarts) with an in-memory store for tests
and dev, behind a protocol so callers are agnostic. Unlike usage (high-frequency
accumulation), org records are low-frequency configuration, but they are still
persisted so a tenant's plan survives restarts and is the single source of truth
for quota enforcement.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from order_desk.api.tenancy import Org, Plan


class OrgStore(Protocol):
    def get(self, org_id: str) -> Org | None: ...

    def upsert(self, org: Org) -> Org: ...


class InMemoryOrgStore:
    """Dev/test org store; seed with orgs at construction."""

    def __init__(self, orgs: list[Org] | None = None) -> None:
        self._orgs: dict[str, Org] = {o.org_id: o for o in (orgs or [])}

    def get(self, org_id: str) -> Org | None:
        return self._orgs.get(org_id)

    def upsert(self, org: Org) -> Org:
        self._orgs[org.org_id] = org
        return org


_SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    plan TEXT NOT NULL
)
"""


class SqliteOrgStore:
    """Durable org store backed by SQLite; org plans survive restarts."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, org_id: str) -> Org | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT org_id, name, plan FROM orgs WHERE org_id = ?", (org_id,)
            ).fetchone()
        if row is None:
            return None
        return Org(org_id=row["org_id"], name=row["name"], plan=Plan(row["plan"]))

    def upsert(self, org: Org) -> Org:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO orgs (org_id, name, plan) VALUES (?, ?, ?)
                ON CONFLICT (org_id) DO UPDATE SET name = excluded.name, plan = excluded.plan
                """,
                (org.org_id, org.name, org.plan.value),
            )
            conn.commit()
        return org
