import random

import pytest
from pydantic import ValidationError

from order_desk.customers import CustomerBook, expand_po, load_customers, po_regex


@pytest.fixture(scope="module")
def book() -> CustomerBook:
    return load_customers()


def test_loads_expected_shape(book: CustomerBook) -> None:
    assert len(book.customers) == 8
    assert all(c.contacts and c.delivery_addresses for c in book.customers)


def test_resolution_is_case_insensitive_and_total(book: CustomerBook) -> None:
    hit = book.resolve_customer("Dana.Whitfield@Harbourline.com.au")
    assert hit is not None and hit.customer_id == "CUST-0001"
    assert book.resolve_customer("someone@unknowndomain.com") is None
    assert book.resolve_customer("not-an-email") is None


def test_multi_domain_customer_resolves_to_one_account(book: CustomerBook) -> None:
    a = book.resolve_customer("priya@swiftship.au")
    b = book.resolve_customer("tom.barker@swiftshipgroup.com")
    assert a is not None and b is not None
    assert a.customer_id == b.customer_id == "CUST-0003"
    assert a.po_template is None


def test_shared_mailboxes_exist(book: CustomerBook) -> None:
    emails = {ct.email for c in book.customers for ct in c.contacts}
    assert "orders@harbourline.com.au" in emails
    assert "purchasing@orbitcomponents.com.au" in emails


def test_po_template_roundtrip(book: CustomerBook) -> None:
    rng = random.Random(7)
    templated = [c for c in book.customers if c.po_template]
    assert len(templated) == 5
    for customer in templated:
        ref = expand_po(customer.po_template, rng)
        assert po_regex(customer.po_template).fullmatch(ref), (customer.customer_id, ref)


def test_duplicate_domain_across_customers_is_rejected(book: CustomerBook) -> None:
    payload = book.model_dump()
    payload["customers"][1]["domains"].append(payload["customers"][0]["domains"][0])
    with pytest.raises(ValidationError, match="multiple customers"):
        CustomerBook.model_validate(payload)
