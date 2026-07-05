"""Textual pins on the Modal serving script (it is infra, not importable in CI)."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "modal_vllm.py"


def test_modal_script_pins_models_gpus_and_deps() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'modal.App("order-desk-vllm")' in text
    assert '"Qwen/Qwen3-4B-Instruct-2507"' in text
    assert '"Qwen/Qwen3-30B-A3B-Instruct-2507"' in text
    assert '"qwen3-4b-instruct-2507"' in text
    assert '"qwen3-30b-a3b-instruct-2507"' in text
    assert 'gpu="A10G"' in text
    assert 'gpu="A100-80GB"' in text
    assert "vllm==0.11.0" in text
    assert "transformers==4.57.1" in text  # the transitive float broke 0.11.0 once


def test_modal_script_keeps_the_key_out_of_argv() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'modal.Secret.from_name("order-desk-vllm")' in text
    assert "--api-key" not in text  # vLLM logs argv at startup; env var only
    assert "os.environ" not in text


def test_modal_script_wires_cache_limits_and_predownload() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'modal.Volume.from_name("order-desk-hf-cache"' in text
    assert '"--max-model-len"' in text
    assert "def download_weights" in text
    assert "snapshot_download" in text
    assert "volume.commit()" in text


def test_modal_script_has_lora_adapter_endpoint() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "def qwen3_4b_adapter" in text
    assert "--enable-lora" in text
    assert "--max-lora-rank" in text
    assert '"qwen3-4b-sft-full-r16"' in text
