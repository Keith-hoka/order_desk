"""Textual pins on the Modal serving script (it is infra, not importable in CI)."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "modal_vllm.py"


def test_modal_script_pins_models_and_gpus() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'modal.App("order-desk-vllm")' in text
    assert '"Qwen/Qwen3-4B-Instruct-2507"' in text
    assert '"Qwen/Qwen3-30B-A3B-Instruct-2507"' in text
    assert '"qwen3-4b-instruct-2507"' in text
    assert '"qwen3-30b-a3b-instruct-2507"' in text
    assert 'gpu="A10G"' in text
    assert 'gpu="A100-80GB"' in text


def test_modal_script_wires_auth_cache_and_limits() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'modal.Secret.from_name("order-desk-vllm")' in text
    assert '"--api-key"' in text
    assert 'os.environ["VLLM_API_KEY"]' in text
    assert 'modal.Volume.from_name("order-desk-hf-cache"' in text
    assert '"--max-model-len"' in text
    assert "vllm==0.11.0" in text
