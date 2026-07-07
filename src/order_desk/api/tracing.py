"""Observability tracing for the extraction API (Phase 4).

Langfuse is optional and hidden behind a thin Tracer protocol: production
sends traces to Langfuse Cloud, tests inject a recording fake, and an unset
LANGFUSE_* config yields a no-op tracer. Traces capture the semantic payload
-- input email, extracted order, per-field confidence, adapter, latency,
whether repair fired -- so the SDK's version churn touches only this adapter,
never the route logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class TraceEvent:
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    metadata: dict[str, Any]


class Tracer(Protocol):
    def record_extraction(
        self,
        *,
        subject: str,
        body: str,
        extraction: dict[str, Any],
        confidence: dict[str, float],
        metadata: dict[str, Any],
    ) -> None: ...


class NoopTracer:
    """Default when observability is unconfigured; records nothing."""

    def record_extraction(self, **_kwargs: Any) -> None:
        return None


class RecordingTracer:
    """Test/dev tracer that keeps events in memory for assertions."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def record_extraction(
        self,
        *,
        subject: str,
        body: str,
        extraction: dict[str, Any],
        confidence: dict[str, float],
        metadata: dict[str, Any],
    ) -> None:
        self.events.append(
            TraceEvent(
                name="extract",
                input={"subject": subject, "body": body},
                output={"extraction": extraction, "confidence": confidence},
                metadata=metadata,
            )
        )


class LangfuseTracer:
    """Production tracer sending traces to Langfuse. SDK imported lazily."""

    def __init__(self, public_key: str, secret_key: str, host: str) -> None:
        from langfuse import Langfuse

        self._client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    def record_extraction(
        self,
        *,
        subject: str,
        body: str,
        extraction: dict[str, Any],
        confidence: dict[str, float],
        metadata: dict[str, Any],
    ) -> None:
        self._client.trace(
            name="extract",
            input={"subject": subject, "body": body},
            output={"extraction": extraction, "confidence": confidence},
            metadata=metadata,
        )


def build_tracer(public_key: str, secret_key: str, host: str) -> Tracer:
    """Langfuse tracer when fully configured, else a no-op."""
    if public_key and secret_key and host:
        return LangfuseTracer(public_key, secret_key, host)
    return NoopTracer()
