"""FastAPI application factory for the extraction service (Phase 4)."""

from __future__ import annotations

from fastapi import FastAPI

from order_desk.api.config import Settings
from order_desk.api.routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="order_desk extraction service", version="0.1.0")
    app.include_router(router)
    settings = settings or Settings.from_env()
    app.state.settings = settings
    app.state.jwt_secret = settings.jwt_secret
    if settings.vllm_base_url:
        from order_desk.extract_client import VLLMExtractClient

        app.state.extract_client = VLLMExtractClient(
            settings.adapter_model, settings.vllm_base_url, api_key=settings.vllm_api_key
        )
    else:
        app.state.extract_client = None
    return app


app = create_app()
