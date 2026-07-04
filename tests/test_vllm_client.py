from types import SimpleNamespace

import pytest

from order_desk.openai_client import wire_extraction_schema
from order_desk.schemas import EmailClass
from order_desk.vllm_client import VLLMBaselineClient


class StubCompletions:
    def __init__(self, content: str, model: str) -> None:
        self.content = content
        self.model = model
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
            usage=SimpleNamespace(prompt_tokens=200, completion_tokens=30),
            model=self.model,
        )


def stub_client(content: str, model: str = "Qwen/Qwen3-4B-Instruct-2507"):
    completions = StubCompletions(content, model)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_unknown_variant_rejected() -> None:
    client, _ = stub_client("x")
    with pytest.raises(ValueError, match="unknown variant"):
        VLLMBaselineClient("m", "http://x", variant="banana", client=client)


def test_classify_is_guided_choice_in_both_variants() -> None:
    labels = {member.value for member in EmailClass}
    for variant in ("xgrammar", "free"):
        client, completions = stub_client("new_order")
        adapter = VLLMBaselineClient("m", "http://x", variant=variant, client=client)
        result = adapter.run_stage("classify", "SYS", "USER", "R1")
        assert result.raw == "new_order"
        assert (result.input_tokens, result.output_tokens) == (200, 30)
        kwargs = completions.kwargs
        assert kwargs["temperature"] == 0
        assert kwargs["max_tokens"] == 10
        assert set(kwargs["extra_body"]["guided_choice"]) == labels
        assert adapter.resolved_models == {"Qwen/Qwen3-4B-Instruct-2507"}


def test_extract_xgrammar_passes_wire_schema() -> None:
    client, completions = stub_client("{}")
    adapter = VLLMBaselineClient("m", "http://x", variant="xgrammar", client=client)
    adapter.run_stage("extract", "SYS", "USER", "R1")
    kwargs = completions.kwargs
    assert kwargs["max_tokens"] == 1500
    assert kwargs["extra_body"] == {"guided_json": wire_extraction_schema()}


def test_extract_free_sends_no_constraints() -> None:
    client, completions = stub_client("sure, here you go: {}")
    adapter = VLLMBaselineClient("m", "http://x", variant="free", client=client)
    result = adapter.run_stage("extract", "SYS", "USER", "R1")
    assert result.raw == "sure, here you go: {}"
    assert completions.kwargs["extra_body"] == {}
