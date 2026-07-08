"""Service configuration from environment (Phase 4)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    adapter_model: str
    vllm_base_url: str
    vllm_api_key: str
    jwt_secret: str
    redis_url: str = ""
    rate_limit_per_minute: int = 60
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""
    review_queue_path: str = ""
    erp_sink_path: str = ""
    slack_webhook_url: str = ""
    metering_db_path: str = ""
    org_db_path: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            adapter_model=os.environ.get("ADAPTER_MODEL", "qwen3-4b-sft-full-r8"),
            vllm_base_url=os.environ.get("VLLM_BASE_URL", ""),
            vllm_api_key=os.environ.get("VLLM_API_KEY", "EMPTY"),
            jwt_secret=os.environ.get("JWT_SECRET", ""),
            redis_url=os.environ.get("REDIS_URL", ""),
            rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
            langfuse_public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
            langfuse_secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
            langfuse_host=os.environ.get("LANGFUSE_HOST", ""),
            review_queue_path=os.environ.get("REVIEW_QUEUE_PATH", ""),
            erp_sink_path=os.environ.get("ERP_SINK_PATH", ""),
            slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL", ""),
            metering_db_path=os.environ.get("METERING_DB_PATH", ""),
            org_db_path=os.environ.get("ORG_DB_PATH", ""),
        )
