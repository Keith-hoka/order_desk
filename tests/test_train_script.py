"""Textual pins on the Modal training script (infra, not importable in CI)."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "modal_train.py"


def test_train_script_pins_stack_and_base_model() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"Qwen/Qwen3-4B-Instruct-2507"' in text
    assert "transformers==4.57.1" in text  # serving parity
    assert "trl==0.24.0" in text
    assert "peft==0.18.0" in text
    assert "bitsandbytes==0.48.2" in text


def test_train_script_qlora_and_completion_only() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'bnb_4bit_quant_type="nf4"' in text
    assert "bnb_4bit_use_double_quant=True" in text
    assert "completion_only_loss=True" in text
    assert 'metric_for_best_model="eval_loss"' in text
    assert "load_best_model_at_end=True" in text
    assert "lora_alpha=2 * rank" in text


def test_train_script_persists_adapter_and_meta() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "/models/adapters/" in text
    assert "training_meta.json" in text
    assert "volume.commit()" in text
    assert "best_val_loss" in text
