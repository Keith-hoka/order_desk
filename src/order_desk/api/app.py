"""FastAPI application factory for the extraction service (Phase 4)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from order_desk.api.billing import build_billing
from order_desk.api.config import Settings
from order_desk.api.metering import InMemoryMeteringStore, SqliteMeteringStore
from order_desk.api.orgs import InMemoryOrgStore, SqliteOrgStore
from order_desk.api.review_routes import review_router
from order_desk.api.routes import router
from order_desk.api.tracing import build_tracer
from order_desk.fulfillment.notify import build_notifier


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="order_desk extraction service", version="0.1.0")
    app.include_router(router)
    app.include_router(review_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    settings = settings or Settings.from_env()
    app.state.settings = settings
    app.state.jwt_secret = settings.jwt_secret
    if settings.metering_db_path:
        app.state.metering = SqliteMeteringStore(settings.metering_db_path)
    else:
        app.state.metering = InMemoryMeteringStore()
    if settings.org_db_path:
        app.state.org_store = SqliteOrgStore(settings.org_db_path)
    else:
        app.state.org_store = InMemoryOrgStore()
    app.state.billing = build_billing(settings.stripe_api_key or None)
    if settings.redis_url:
        import redis as redis_lib

        from order_desk.api.rate_limit import RateLimiter, RedisCounter

        counter = RedisCounter(redis_lib.from_url(settings.redis_url))
        app.state.rate_limiter = RateLimiter(counter, settings.rate_limit_per_minute)
    else:
        app.state.rate_limiter = None
    app.state.tracer = build_tracer(
        settings.langfuse_public_key, settings.langfuse_secret_key, settings.langfuse_host
    )
    if settings.vllm_base_url:
        from order_desk.extract_client import VLLMExtractClient

        app.state.extract_client = VLLMExtractClient(
            settings.adapter_model, settings.vllm_base_url, api_key=settings.vllm_api_key
        )
    else:
        app.state.extract_client = None
    queue_path = settings.review_queue_path
    if queue_path:
        from order_desk.api.review_store import JsonReviewStore

        app.state.review_store = JsonReviewStore(queue_path)
    else:
        app.state.review_store = None

    if settings.erp_sink_path:
        from order_desk.fulfillment.erp import LocalOrderSink

        app.state.order_sink = LocalOrderSink(settings.erp_sink_path)
    else:
        app.state.order_sink = None
    app.state.notifier = build_notifier(settings.slack_webhook_url or None)

    # live extraction from the review UI needs both legs of the pipeline: the
    # adapter endpoint (vLLM on Modal) and the prompted router (OpenAI)
    import os

    if settings.vllm_base_url and os.environ.get("OPENAI_API_KEY"):
        from order_desk.api.live_extract import LiveExtractor

        app.state.live_extractor = LiveExtractor(
            classifier_model=os.environ.get("CLASSIFIER_MODEL", "gpt-4o-mini"),
            adapter_model=settings.adapter_model,
            vllm_base_url=settings.vllm_base_url,
            vllm_api_key=settings.vllm_api_key,
        )
    else:
        app.state.live_extractor = None
    return app


app = create_app()
