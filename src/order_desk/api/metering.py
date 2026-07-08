"""Per-org usage metering (Phase 11).

Records what each org consumes -- extraction count and input/output tokens --
keyed by org and billing period (year-month), so the quota check (Phase 11.3)
and Stripe usage reporting (Phase 11.4) have a per-org, per-month number. Usage
is billing data, so it must survive restarts: the production store is SQLite
(SqliteMeteringStore), durable across restarts, with an in-memory store for
tests and dev. The store is a protocol so callers are agnostic. Accumulation is
an atomic UPSERT, safe under concurrent extraction requests.

This is honest about the skeleton's remaining edges: multi-tenant isolation is
at the application layer (org_id keys), not database row-level security.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


def current_period(now: datetime | None = None) -> str:
    """Billing period key: UTC year-month, e.g. '2026-07'."""
    dt = now or datetime.now(UTC)
    return dt.strftime("%Y-%m")


@dataclass
class Usage:
    org_id: str
    period: str
    extractions: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class MeteringStore(Protocol):
    def record(
        self, org_id: str, *, input_tokens: int, output_tokens: int, period: str | None = None
    ) -> Usage: ...

    def usage(self, org_id: str, period: str | None = None) -> Usage: ...


@dataclass
class InMemoryMeteringStore:
    """Dev/test metering: usage accumulates in a dict, resets on restart."""

    _usage: dict[tuple[str, str], Usage] = field(default_factory=dict)

    def record(
        self, org_id: str, *, input_tokens: int, output_tokens: int, period: str | None = None
    ) -> Usage:
        period = period or current_period()
        key = (org_id, period)
        u = self._usage.get(key) or Usage(org_id=org_id, period=period)
        u.extractions += 1
        u.input_tokens += input_tokens
        u.output_tokens += output_tokens
        self._usage[key] = u
        return u

    def usage(self, org_id: str, period: str | None = None) -> Usage:
        period = period or current_period()
        return self._usage.get((org_id, period)) or Usage(org_id=org_id, period=period)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    org_id TEXT NOT NULL,
    period TEXT NOT NULL,
    extractions INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (org_id, period)
)
"""


class SqliteMeteringStore:
    """Durable metering backed by SQLite; usage survives restarts.

    The db path can point at a persistent volume in production. Accumulation is
    a single UPSERT so concurrent extraction requests increment atomically.
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record(
        self, org_id: str, *, input_tokens: int, output_tokens: int, period: str | None = None
    ) -> Usage:
        period = period or current_period()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO usage (org_id, period, extractions, input_tokens, output_tokens)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT (org_id, period) DO UPDATE SET
                    extractions = extractions + 1,
                    input_tokens = input_tokens + excluded.input_tokens,
                    output_tokens = output_tokens + excluded.output_tokens
                """,
                (org_id, period, input_tokens, output_tokens),
            )
            conn.commit()
        return self.usage(org_id, period)

    def usage(self, org_id: str, period: str | None = None) -> Usage:
        period = period or current_period()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT extractions, input_tokens, output_tokens FROM usage "
                "WHERE org_id = ? AND period = ?",
                (org_id, period),
            ).fetchone()
        if row is None:
            return Usage(org_id=org_id, period=period)
        return Usage(
            org_id=org_id,
            period=period,
            extractions=row["extractions"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
        )
