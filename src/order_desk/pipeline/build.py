"""Production pipeline entry point (Phase 5).

Wires the real prompted classifier and adapter extractor from configuration
into the compiled LangGraph, and runs an email end-to-end.
"""

from __future__ import annotations

from order_desk.pipeline.graph import build_graph
from order_desk.pipeline.nodes import build_production_nodes
from order_desk.pipeline.policy import PipelineState


def build_production_pipeline(
    classifier_model: str,
    adapter_model: str,
    vllm_base_url: str,
    vllm_api_key: str,
):
    """Compile the pipeline with real classifier + extractor from config."""
    classifier, extractor = build_production_nodes(
        classifier_model, adapter_model, vllm_base_url, vllm_api_key
    )
    return build_graph(classifier, extractor)


def run_email(app, subject: str, body: str) -> PipelineState:
    """Invoke a compiled pipeline on one email, return the final state."""
    result = app.invoke(PipelineState(subject=subject, body=body))
    return PipelineState.model_validate(result)
