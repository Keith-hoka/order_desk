"""Modal vLLM serving for the Phase 2 Qwen baselines (step 2.4b).

Two OpenAI-compatible vLLM servers behind Modal web endpoints, sharing one
HF-cache volume, each scaling to zero after idle:

- qwen3_4b        -> Qwen/Qwen3-4B-Instruct-2507       on A10G
- qwen3_30b_a3b   -> Qwen/Qwen3-30B-A3B-Instruct-2507  on A100-80GB

Auth: vllm serve --api-key reads VLLM_API_KEY from the Modal secret
`order-desk-vllm`; the local runner sends the same key from .env. The served
model names are short aliases; the weight identity is pinned here by the HF
repo tag (-2507). Guided decoding backend is left at the vLLM V1 default
(xgrammar); the request-level guided_json/guided_choice constraints come
from the client adapter.

Deploy:  uv run modal deploy scripts/modal_vllm.py
"""

import os
import subprocess

import modal

app = modal.App("order-desk-vllm")

VLLM_PORT = 8000
MINUTES = 60

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.11.0", "hf_transfer==0.1.9")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/models"})
)

volume = modal.Volume.from_name("order-desk-hf-cache", create_if_missing=True)
secret = modal.Secret.from_name("order-desk-vllm")


def _serve(hf_model: str, served_name: str) -> None:
    cmd = [
        "vllm",
        "serve",
        hf_model,
        "--served-model-name",
        served_name,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--max-model-len",
        "8192",
        "--api-key",
        os.environ["VLLM_API_KEY"],
    ]
    subprocess.Popen(cmd)


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/models": volume},
    secrets=[secret],
    scaledown_window=8 * MINUTES,
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
def qwen3_4b() -> None:
    _serve("Qwen/Qwen3-4B-Instruct-2507", "qwen3-4b-instruct-2507")


@app.function(
    image=image,
    gpu="A100-80GB",
    volumes={"/models": volume},
    secrets=[secret],
    scaledown_window=8 * MINUTES,
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=VLLM_PORT, startup_timeout=30 * MINUTES)
def qwen3_30b_a3b() -> None:
    _serve("Qwen/Qwen3-30B-A3B-Instruct-2507", "qwen3-30b-a3b-instruct-2507")
