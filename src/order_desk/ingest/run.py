"""Connect the ingest layer to the pipeline (Phase 6).

Standardize each raw email from a source, run it through the pipeline, and
merge the standardization asks (e.g. the reply-history flag) into the pipeline
state's asks alongside blend asks.
"""

from __future__ import annotations

from order_desk.ingest.source import EmailSource
from order_desk.ingest.standardize import standardize_email
from order_desk.pipeline.build import run_email
from order_desk.pipeline.policy import PipelineState


def process_raw(app, raw: str) -> PipelineState:
    """Standardize one raw email and run it through the pipeline."""
    std = standardize_email(raw)
    state = run_email(app, std.subject, std.body)
    if std.asks:
        state.asks = list(state.asks) + std.asks
    return state


def process_source(app, source: EmailSource) -> list[PipelineState]:
    """Standardize and run every email from a source."""
    return [process_raw(app, raw) for raw in source.fetch()]
