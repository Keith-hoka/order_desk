from order_desk.api.tracing import NoopTracer, RecordingTracer, build_tracer


def test_noop_records_nothing() -> None:
    tracer = NoopTracer()
    tracer.record_extraction(
        subject="s", body="b", extraction={}, confidence={}, metadata={}
    )  # no exception, nothing kept


def test_recording_tracer_captures_payload() -> None:
    tracer = RecordingTracer()
    tracer.record_extraction(
        subject="order",
        body="send tape",
        extraction={"customer_po_text": "PO-1"},
        confidence={"customer_po_text": 0.9},
        metadata={"adapter": "full-r8", "latency_s": 0.1},
    )
    assert len(tracer.events) == 1
    event = tracer.events[0]
    assert event.name == "extract"
    assert event.input == {"subject": "order", "body": "send tape"}
    assert event.output["extraction"] == {"customer_po_text": "PO-1"}
    assert event.output["confidence"] == {"customer_po_text": 0.9}
    assert event.metadata["adapter"] == "full-r8"


def test_build_tracer_noop_when_unconfigured() -> None:
    assert isinstance(build_tracer("", "", ""), NoopTracer)
    assert isinstance(build_tracer("pk", "", "host"), NoopTracer)  # partial config -> noop


def test_recording_tracer_accumulates() -> None:
    tracer = RecordingTracer()
    for i in range(3):
        tracer.record_extraction(
            subject=f"s{i}", body="b", extraction={}, confidence={}, metadata={}
        )
    assert len(tracer.events) == 3
