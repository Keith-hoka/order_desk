"""Modal QLoRA trainer for the Qwen3-4B extraction fine-tune (step 3.2).

Parameterized over (subset, rank): each run QLoRA-tunes
Qwen/Qwen3-4B-Instruct-2507 on data/sft/train_{subset}.jsonl (uploaded to the
volume) and writes a LoRA adapter to /models/adapters/qwen3-4b-sft-{subset}-
r{rank}/, committed to the shared volume for Phase 4 serving.

Locked decisions:
- Stack pinned with its contemporaries (as in Phase 2): trl/peft/
  transformers 4.57.1 (serving parity)/bitsandbytes/accelerate.
- QLoRA: NF4 4-bit + double-quant, bf16 compute; LoRA on all attention and
  MLP linears, alpha = 2*rank, dropout 0.05.
- Qwen3 chat template applied by SFTTrainer; completion-only loss masks the
  prompt so only the assistant JSON contributes to the loss.
- Fixed hyperparameters across curve points for comparability; per-epoch
  checkpoints, final adapter = lowest val-loss checkpoint (val loss selects,
  not a task metric -- SPEC eval-purity discipline).

Usage:
  uv run modal run scripts/modal_train.py::upload_sft
  uv run modal run scripts/modal_train.py::train --subset full --rank 16
"""

import json
import os

import modal

app = modal.App("order-desk-train")

HOURS = 60 * 60
BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.8.0",
        "transformers==4.57.1",
        "trl==0.24.0",
        "peft==0.18.0",
        "bitsandbytes==0.48.2",
        "accelerate==1.10.1",
        "datasets==4.0.0",
        "hf_transfer==0.1.9",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/models"})
)

volume = modal.Volume.from_name("order-desk-hf-cache", create_if_missing=True)


@app.function(image=image, volumes={"/models": volume}, timeout=1 * HOURS)
def upload_sft(files: dict[str, str]) -> None:
    """Receive local SFT jsonl contents and persist them to the volume."""
    import pathlib

    target = pathlib.Path("/models/sft")
    target.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (target / name).write_text(content, encoding="utf-8")
        print(f"wrote /models/sft/{name} ({content.count(chr(10))} lines)")
    volume.commit()


@app.function(image=image, gpu="L40S", volumes={"/models": volume}, timeout=4 * HOURS)
def train(subset: str, rank: int, epochs: int = 3, seed: int = 42) -> dict:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    adapter_name = f"qwen3-4b-sft-{subset}-r{rank}"
    out_dir = f"/models/adapters/{adapter_name}"
    train_path = f"/models/sft/train_{subset}.jsonl"
    val_path = "/models/sft/val_gold.jsonl"

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=quant, torch_dtype=torch.bfloat16, device_map="auto"
    )
    peft_config = LoraConfig(
        r=rank,
        lora_alpha=2 * rank,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=LORA_TARGETS,
    )

    train_ds = load_dataset("json", data_files=train_path, split="train")
    eval_ds = load_dataset("json", data_files=val_path, split="train")

    config = SFTConfig(
        output_dir=out_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=2,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        tf32=True,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        bf16=True,
        max_length=2048,
        packing=False,
        completion_only_loss=True,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=10,
        seed=seed,
        data_seed=seed,
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        args=config,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=peft_config,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(out_dir)

    history = trainer.state.log_history
    eval_losses = [row["eval_loss"] for row in history if "eval_loss" in row]
    meta = {
        "adapter": adapter_name,
        "base_model": BASE_MODEL,
        "subset": subset,
        "rank": rank,
        "lora_alpha": 2 * rank,
        "epochs": epochs,
        "seed": seed,
        "gpu": "L40S",
        "effective_batch": 16,
        "best_val_loss": min(eval_losses) if eval_losses else None,
        "final_val_loss": eval_losses[-1] if eval_losses else None,
        "eval_losses": eval_losses,
        "global_steps": trainer.state.global_step,
        "pins": {
            "transformers": "4.57.1",
            "trl": "0.24.0",
            "peft": "0.18.0",
            "bitsandbytes": "0.48.2",
        },
    }
    with open(os.path.join(out_dir, "training_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
    volume.commit()
    print(f"saved adapter {adapter_name}: best_val_loss={meta['best_val_loss']}")
    return meta


@app.local_entrypoint()
def upload() -> None:
    import pathlib

    files = {}
    sft_dir = pathlib.Path("data/sft")
    for path in sorted(sft_dir.glob("train_*.jsonl")):
        files[path.name] = path.read_text(encoding="utf-8")
    files["val_gold.jsonl"] = pathlib.Path("data/sft/val_gold.jsonl").read_text(encoding="utf-8")
    upload_sft.remote(files)
