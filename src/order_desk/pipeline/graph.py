"""LangGraph orchestration graph for the extraction pipeline (Phase 5).

A StateGraph over PipelineState: classify -> (conditional edge on route) ->
extract | cancel | inquiry | discard -> finalize. Routing is a declarative
conditional edge reading state.route, not if-else buried in a function --
only the EXTRACT branch reaches the learned extraction node.

Classifier and extractor are injected (protocols): production wires the real
prompted classifier and the vLLM extract client, tests wire fakes. Every node
is a pure State -> dict update, so the whole graph is offline-testable.
"""

from __future__ import annotations

from typing import Protocol

from langgraph.graph import END, START, StateGraph

from order_desk.pipeline.policy import (
    Classification,
    PipelineState,
    RouteDecision,
    detect_product_inquiry,
    policy_violations,
    route_for_class,
)
from order_desk.schemas import ExtractedOrder

BLEND_ASK = (
    "email contains a product inquiry; extracted items may include "
    "non-order products -- review needed"
)


class ClassifierFn(Protocol):
    def __call__(self, subject: str, body: str) -> Classification: ...


class ExtractorFn(Protocol):
    def __call__(self, subject: str, body: str) -> tuple[ExtractedOrder, dict[str, float]]: ...


def _classify_node(state: PipelineState, classifier: ClassifierFn) -> dict:
    classification = classifier(state.subject, state.body)
    route = route_for_class(classification.email_class)
    return {"classification": classification, "route": route}


def _extract_node(state: PipelineState, extractor: ExtractorFn) -> dict:
    extraction, confidence = extractor(state.subject, state.body)
    asks = list(state.asks)
    if detect_product_inquiry(state.body):
        asks.append(BLEND_ASK)
    return {"extraction": extraction, "confidence": confidence, "asks": asks}


def _cancel_node(state: PipelineState) -> dict:
    # Cancellation path: no extraction; downstream pulls the referenced PO.
    return {}


def _finalize_node(state: PipelineState) -> dict:
    return {"violations": policy_violations(state)}


def _route_branch(state: PipelineState) -> str:
    """Conditional edge: map the route decision to the next node name."""
    assert state.route is not None
    return state.route.value


def build_graph(classifier: ClassifierFn, extractor: ExtractorFn):
    """Compile the pipeline graph with injected classifier and extractor."""
    graph = StateGraph(PipelineState)

    graph.add_node("classify", lambda s: _classify_node(s, classifier))
    graph.add_node("extract", lambda s: _extract_node(s, extractor))
    graph.add_node("cancel", _cancel_node)
    graph.add_node("inquiry", lambda s: {})
    graph.add_node("discard", lambda s: {})
    graph.add_node("finalize", _finalize_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        _route_branch,
        {
            RouteDecision.EXTRACT.value: "extract",
            RouteDecision.CANCEL.value: "cancel",
            RouteDecision.INQUIRY.value: "inquiry",
            RouteDecision.DISCARD.value: "discard",
        },
    )
    for node in ("extract", "cancel", "inquiry", "discard"):
        graph.add_edge(node, "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def run_pipeline(
    subject: str, body: str, classifier: ClassifierFn, extractor: ExtractorFn
) -> PipelineState:
    """Convenience runner: build, invoke, return the final PipelineState."""
    app = build_graph(classifier, extractor)
    result = app.invoke(PipelineState(subject=subject, body=body))
    return PipelineState.model_validate(result)
