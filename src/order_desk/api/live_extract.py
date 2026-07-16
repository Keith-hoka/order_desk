"""Live extraction for the review UI.

Runs one pasted email through the real pipeline -- OpenAI-prompted routing,
then the fine-tuned adapter on Modal via vLLM -- and shapes the result into a
ReviewItem the exception queue can serve. The pipeline graph is compiled once
at startup; each call is a synchronous invoke (the adapter endpoint may cold
start, so the first call can be slow).
"""

from __future__ import annotations

from pathlib import Path

from order_desk.calibration import IsotonicCalibrator
from order_desk.review.priority import ReviewItem, build_review_item

DEFAULT_CALIBRATOR = Path("docs/phase4_calibrator.json")


class LiveExtractor:
    def __init__(
        self,
        classifier_model: str,
        adapter_model: str,
        vllm_base_url: str,
        vllm_api_key: str,
        calibrator_path: Path | str = DEFAULT_CALIBRATOR,
    ) -> None:
        from order_desk.pipeline.build import build_production_pipeline

        self._app = build_production_pipeline(
            classifier_model, adapter_model, vllm_base_url, vllm_api_key
        )
        self._calibrator = IsotonicCalibrator.load(Path(calibrator_path))

    def extract(self, subject: str, body: str, item_id: str) -> ReviewItem:
        from order_desk.pipeline.build import run_email

        state = run_email(self._app, subject, body)
        return build_review_item(state, self._calibrator, item_id)

    def extract_raw(self, raw: str, item_id: str) -> ReviewItem:
        """Standardize a raw RFC822 message (as fetched over IMAP), then extract."""
        from order_desk.ingest.run import process_raw

        state = process_raw(self._app, raw)
        return build_review_item(state, self._calibrator, item_id)
