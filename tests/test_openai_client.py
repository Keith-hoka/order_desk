import json
from pathlib import Path
from types import SimpleNamespace

from order_desk.openai_client import (
    OpenAIBaselineClient,
    classify_schema,
    strip_keywords,
    wire_extraction_schema,
)
from order_desk.schemas import EmailClass

SNAPSHOT = Path(__file__).parent / "snapshots" / "extracted_order.schema.json"


class StubCompletions:
    def __init__(self, content: str, model: str) -> None:
        self.content = content
        self.model = model
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
            usage=SimpleNamespace(prompt_tokens=123, completion_tokens=45),
            model=self.model,
        )


def stub_client(content: str, model: str = "gpt-4o-mini-2024-07-18"):
    completions = StubCompletions(content, model)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_wire_schema_is_snapshot_minus_stripped_keywords() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snapshot_text = json.dumps(snapshot)
    assert '"minLength"' in snapshot_text and '"minimum"' in snapshot_text
    wire = wire_extraction_schema()
    assert wire == strip_keywords(snapshot)
    wire_text = json.dumps(wire)
    assert '"minLength"' not in wire_text and '"minimum"' not in wire_text
    assert wire["additionalProperties"] is False
    assert set(wire["required"]) == set(snapshot["required"])
    line_item = wire["$defs"]["LineItem"]
    assert line_item["additionalProperties"] is False
    assert set(line_item["required"]) == set(snapshot["$defs"]["LineItem"]["required"])


def test_classify_stage_call_shape_and_unwrap() -> None:
    client, completions = stub_client('{"label": "new_order"}')
    adapter = OpenAIBaselineClient("gpt-4o-mini", client=client)
    result = adapter.run_stage("classify", "SYS", "USER", "R1")
    assert result.raw == "new_order"
    assert (result.input_tokens, result.output_tokens) == (123, 45)
    assert result.latency_s >= 0
    kwargs = completions.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["temperature"] == 0
    assert kwargs["max_completion_tokens"] == 20
    assert kwargs["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]
    fmt = kwargs["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] == classify_schema()
    enum = fmt["json_schema"]["schema"]["properties"]["label"]["enum"]
    assert set(enum) == {member.value for member in EmailClass}
    assert adapter.resolved_models == {"gpt-4o-mini-2024-07-18"}


def test_extract_stage_passthrough_and_schema() -> None:
    client, completions = stub_client('{"anything": true}')
    adapter = OpenAIBaselineClient("gpt-4o-mini", client=client)
    result = adapter.run_stage("extract", "SYS", "USER", "R1")
    assert result.raw == '{"anything": true}'
    kwargs = completions.kwargs
    assert kwargs["max_completion_tokens"] == 1500
    fmt = kwargs["response_format"]
    assert fmt["json_schema"]["name"] == "extracted_order"
    assert fmt["json_schema"]["schema"] == wire_extraction_schema()


def test_unwrap_falls_through_on_garbage() -> None:
    client, _ = stub_client("not json at all")
    adapter = OpenAIBaselineClient("gpt-4o-mini", client=client)
    assert adapter.run_stage("classify", "S", "U", "R").raw == "not json at all"
    wrong_key, _ = stub_client('{"wrong_key": "x"}')
    adapter = OpenAIBaselineClient("gpt-4o-mini", client=wrong_key)
    assert adapter.run_stage("classify", "S", "U", "R").raw == '{"wrong_key": "x"}'
