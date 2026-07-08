"""Modal vLLM serving for the Phase 2 Qwen baselines (step 2.4b).

Two OpenAI-compatible vLLM servers behind Modal web endpoints, sharing one
HF-cache volume, each scaling to zero after idle:

- qwen3_4b        -> Qwen/Qwen3-4B-Instruct-2507       on A10G
- qwen3_30b_a3b   -> Qwen/Qwen3-30B-A3B-Instruct-2507  on A100-80GB

Pins: vllm==0.11.0 with transformers==4.57.1. The transitive float to
transformers 5.x removed all_special_tokens_extended and crashed 0.11.0's
tokenizer path -- a pinned framework over floating transitives is not
reproducibility, so the ecosystem is pinned to the framework's
contemporaries.

Auth: vLLM reads VLLM_API_KEY natively from its environment, injected by the
Modal secret `order-desk-vllm`. Deliberately never passed on the command
line: vLLM logs its non-default CLI args at startup, which is exactly how a
key leaks into pasted logs.

Cold starts: run `modal run scripts/modal_vllm.py::download_weights` once
after (re)deploying, so web containers only load weights from the volume and
no HTTP request ever waits behind a multi-GB download.

Deploy:  uv run modal deploy scripts/modal_vllm.py
"""

import subprocess

import modal

app = modal.App("order-desk-vllm")

VLLM_PORT = 8000
MINUTES = 60

MODELS = {
    "qwen3-4b-instruct-2507": "Qwen/Qwen3-4B-Instruct-2507",
    "qwen3-30b-a3b-instruct-2507": "Qwen/Qwen3-30B-A3B-Instruct-2507",
}

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.11.0", "transformers==4.57.1", "hf_transfer==0.1.9")
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_XET_HIGH_PERFORMANCE": "1",
            "HF_HOME": "/models",
        }
    )
)

volume = modal.Volume.from_name("order-desk-hf-cache", create_if_missing=True)
secret = modal.Secret.from_name("order-desk-vllm")


def _serve(served_name: str) -> None:
    # VLLM_API_KEY arrives via the secret's environment; vLLM picks it up
    # natively, keeping the key out of argv and out of startup logs.
    subprocess.Popen(
        [
            "vllm",
            "serve",
            MODELS[served_name],
            "--served-model-name",
            served_name,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
            "--max-model-len",
            "8192",
        ]
    )


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/models": volume},
    secrets=[secret],
    scaledown_window=8 * MINUTES,
    timeout=30 * MINUTES,
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
def qwen3_4b() -> None:
    _serve("qwen3-4b-instruct-2507")


@app.function(
    image=image,
    gpu="A100-80GB",
    volumes={"/models": volume},
    secrets=[secret],
    scaledown_window=8 * MINUTES,
    timeout=30 * MINUTES,
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=VLLM_PORT, startup_timeout=30 * MINUTES)
def qwen3_30b_a3b() -> None:
    _serve("qwen3-30b-a3b-instruct-2507")


ADAPTERS = {
    name: f"/models/adapters/{name}"
    for name in (
        "qwen3-4b-sft-500-r16",
        "qwen3-4b-sft-1000-r16",
        "qwen3-4b-sft-2000-r16",
        "qwen3-4b-sft-full-r8",
        "qwen3-4b-sft-full-r16",
        "qwen3-4b-sft-full-r32",
        "qwen3-4b-sft-flywheel-r8",
    )
}


def _serve_lora(served_names: dict[str, str]) -> None:
    # base model served with LoRA modules mounted; request `model` selects the
    # adapter by name. VLLM_API_KEY arrives via the secret's environment.
    modules = [f"{name}={path}" for name, path in served_names.items()]
    subprocess.Popen(
        [
            "vllm",
            "serve",
            "Qwen/Qwen3-4B-Instruct-2507",
            "--enable-lora",
            "--max-lora-rank",
            "32",
            "--lora-modules",
            *modules,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
            "--max-model-len",
            "8192",
        ]
    )


@app.function(
    image=image,
    gpu="L40S",
    volumes={"/models": volume},
    secrets=[secret],
    scaledown_window=8 * MINUTES,
    timeout=30 * MINUTES,
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
def qwen3_4b_adapter() -> None:
    _serve_lora(ADAPTERS)


@app.function(image=image, volumes={"/models": volume}, timeout=60 * MINUTES)
def download_weights() -> None:
    from huggingface_hub import snapshot_download

    for repo in MODELS.values():
        snapshot_download(repo)
        print(f"downloaded {repo}")
    volume.commit()
