from order_desk.pipeline.validator import route_gap, route_report


def _rec(rid, cls):
    return {"id": rid, "email_class": cls}


def _pred(cls):
    return {"classification": cls}


def test_oracle_routing_is_perfect() -> None:
    records = [_rec("1", "new_order"), _rec("2", "inquiry"), _rec("3", "cancellation")]
    preds = {"1": _pred("new_order"), "2": _pred("inquiry"), "3": _pred("cancellation")}
    report = route_report(records, preds)
    assert report["routing_accuracy"] == 1.0
    assert report["classification_accuracy"] == 1.0
    assert report["route_confusion"] == {}


def test_route_beats_class_when_both_map_to_extract() -> None:
    # new_order misclassified as amendment: class wrong, route (EXTRACT) right.
    records = [_rec("1", "new_order"), _rec("2", "new_order")]
    preds = {"1": _pred("amendment"), "2": _pred("new_order")}
    report = route_report(records, preds)
    assert report["classification_accuracy"] == 0.5  # one class wrong
    assert report["routing_accuracy"] == 1.0  # both route to EXTRACT
    assert route_gap(report) == 0.5  # the harmless misclass


def test_route_error_when_route_differs() -> None:
    # new_order misclassified as inquiry: EXTRACT vs INQUIRY, a real route error.
    records = [_rec("1", "new_order")]
    preds = {"1": _pred("inquiry")}
    report = route_report(records, preds)
    assert report["routing_accuracy"] == 0.0
    assert report["route_confusion"] == {"extract->inquiry": 1}


def test_invalid_label_counts_as_invalid_route() -> None:
    records = [_rec("1", "new_order")]
    preds = {"1": _pred("garbage_label")}
    report = route_report(records, preds)
    assert report["invalid_route"] == 1
    assert report["routing_accuracy"] == 0.0


def test_missing_predictions_skipped() -> None:
    records = [_rec("1", "new_order"), _rec("2", "inquiry")]
    preds = {"1": _pred("new_order")}  # no pred for "2"
    report = route_report(records, preds)
    assert report["n"] == 1  # only scored records with a prediction
