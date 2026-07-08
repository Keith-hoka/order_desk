"""Extraction endpoint (Phase 4). Backend client is injectable for testing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from order_desk.api.auth import Principal, require_auth
from order_desk.api.models import ExtractMeta, ExtractRequest, ExtractResponse
from order_desk.api.rate_limit import enforce_rate_limit
from order_desk.api.tracing import NoopTracer, Tracer
from order_desk.baseline import parse_extraction
from order_desk.confidence import field_confidences, overall_confidence
from order_desk.extract_client import ExtractClient

router = APIRouter()


def get_client(request: Request) -> ExtractClient:
    client = getattr(request.app.state, "extract_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="extraction backend not configured")
    return client


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    client = getattr(request.app.state, "extract_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="backend not configured")
    return {"status": "ready"}


@router.post("/extract", response_model=ExtractResponse)
def extract(
    request: Request,
    payload: ExtractRequest,
    client: ExtractClient = Depends(get_client),
    principal: Principal | None = Depends(require_auth),
    _rate: None = Depends(enforce_rate_limit),
) -> ExtractResponse:
    result = client.extract(payload.subject, payload.body)
    parsed, repaired = parse_extraction(result.raw)
    if parsed is None:
        raise HTTPException(status_code=422, detail="model output failed strict extraction schema")
    confidences = field_confidences(result.raw, result.tokens, parsed)
    overall = overall_confidence(confidences)
    tracer: Tracer = getattr(request.app.state, "tracer", None) or NoopTracer()
    tracer.record_extraction(
        subject=payload.subject,
        body=payload.body,
        extraction=parsed.model_dump(),
        confidence=confidences,
        metadata={
            "model": result.model,
            "adapter": getattr(client, "model", result.model),
            "latency_s": result.latency_s,
            "parse_repaired": repaired,
            "overall_confidence": overall,
        },
    )
    if principal is not None and principal.org_id is not None:
        metering = getattr(request.app.state, "metering", None)
        if metering is not None:
            metering.record(
                principal.org_id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
    return ExtractResponse(
        extraction=parsed,
        confidence=confidences,
        meta=ExtractMeta(
            model=result.model,
            adapter=getattr(client, "model", result.model),
            latency_s=result.latency_s,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            parse_repaired=repaired,
            overall_confidence=overall,
        ),
    )
