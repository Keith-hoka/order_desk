"""Customer fixtures: sender identities, delivery addresses, PO reference formats."""

from __future__ import annotations

import json
import random
import re
from functools import lru_cache
from importlib import resources
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CUSTOMER_ID_RE = re.compile(r"^CUST-\d{4}$")
DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")
EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$")
PHONE_RE = re.compile(r"^\+61\d{9}$")
POSTCODE_RE = re.compile(r"^\d{4}$")
PO_TEMPLATE_RE = re.compile(r"^[A-Z0-9/#-]+$")
AU_STATES = frozenset({"NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"})


def expand_po(template: str, rng: random.Random) -> str:
    """Render a concrete PO reference from a template ('#' -> digit)."""
    return "".join(str(rng.randint(0, 9)) if ch == "#" else ch for ch in template)


def po_regex(template: str) -> re.Pattern[str]:
    """Derive the validation regex from the same template used for generation."""
    return re.compile("".join(r"\d" if ch == "#" else re.escape(ch) for ch in template))


class Address(BaseModel):
    label: str = Field(min_length=1)
    line1: str = Field(min_length=1)
    line2: str | None = None
    suburb: str = Field(min_length=1)
    state: str
    postcode: str

    @field_validator("state")
    @classmethod
    def state_is_australian(cls, v: str) -> str:
        if v not in AU_STATES:
            raise ValueError(f"unknown state {v!r}")
        return v

    @field_validator("postcode")
    @classmethod
    def postcode_is_four_digits(cls, v: str) -> str:
        if not POSTCODE_RE.fullmatch(v):
            raise ValueError(f"bad postcode {v!r}")
        return v


class Contact(BaseModel):
    name: str = Field(min_length=1)
    email: str
    role: str = Field(min_length=1)
    phone: str

    @field_validator("email")
    @classmethod
    def email_is_normalized(cls, v: str) -> str:
        if v != v.strip().lower() or not EMAIL_RE.fullmatch(v):
            raise ValueError(f"email {v!r} must be lowercase and well-formed")
        return v

    @field_validator("phone")
    @classmethod
    def phone_is_normalized_au(cls, v: str) -> str:
        if not PHONE_RE.fullmatch(v):
            raise ValueError(f"phone {v!r} must be +61 followed by 9 digits")
        return v


class Style(BaseModel):
    tone: Literal["formal", "casual", "terse"]
    signoff: str = Field(min_length=1)


class Customer(BaseModel):
    customer_id: str
    company: str = Field(min_length=1)
    domains: list[str] = Field(min_length=1)
    contacts: list[Contact] = Field(min_length=1)
    delivery_addresses: list[Address] = Field(min_length=1)
    po_template: str | None = None
    style: Style

    @field_validator("customer_id")
    @classmethod
    def id_matches_pattern(cls, v: str) -> str:
        if not CUSTOMER_ID_RE.fullmatch(v):
            raise ValueError(f"customer_id {v!r} does not match {CUSTOMER_ID_RE.pattern}")
        return v

    @field_validator("domains")
    @classmethod
    def domains_are_normalized_and_unique(cls, v: list[str]) -> list[str]:
        for domain in v:
            if domain != domain.strip().lower() or not DOMAIN_RE.fullmatch(domain):
                raise ValueError(f"domain {domain!r} must be lowercase and well-formed")
        if len(set(v)) != len(v):
            raise ValueError("duplicate domain within customer")
        return v

    @field_validator("po_template")
    @classmethod
    def po_template_is_expandable(cls, v: str | None) -> str | None:
        if v is not None and (not PO_TEMPLATE_RE.fullmatch(v) or "#" not in v):
            raise ValueError(f"po_template {v!r} must be [A-Z0-9/-] with at least one '#'")
        return v

    @model_validator(mode="after")
    def integrity(self) -> Customer:
        for contact in self.contacts:
            domain = contact.email.rsplit("@", 1)[1]
            if domain not in self.domains:
                raise ValueError(f"{contact.email}: domain not in customer domains")
        labels = [a.label for a in self.delivery_addresses]
        if len(set(labels)) != len(labels):
            raise ValueError(f"{self.customer_id}: duplicate address label")
        return self


class CustomerBook(BaseModel):
    version: int
    customers: list[Customer]

    @model_validator(mode="after")
    def integrity(self) -> CustomerBook:
        seen_ids: set[str] = set()
        seen_domains: set[str] = set()
        seen_emails: set[str] = set()
        for customer in self.customers:
            if customer.customer_id in seen_ids:
                raise ValueError(f"duplicate customer_id {customer.customer_id}")
            seen_ids.add(customer.customer_id)
            for domain in customer.domains:
                if domain in seen_domains:
                    raise ValueError(f"domain {domain!r} appears in multiple customers")
                seen_domains.add(domain)
            for contact in customer.contacts:
                if contact.email in seen_emails:
                    raise ValueError(f"email {contact.email!r} appears twice")
                seen_emails.add(contact.email)
        return self

    def resolve_customer(self, email: str) -> Customer | None:
        """Deterministic sender -> customer resolution via the address domain."""
        addr = email.strip().lower()
        if "@" not in addr:
            return None
        domain = addr.rsplit("@", 1)[1]
        for customer in self.customers:
            if domain in customer.domains:
                return customer
        return None


@lru_cache(maxsize=1)
def load_customers() -> CustomerBook:
    payload = resources.files("order_desk.fixtures").joinpath("customers.json").read_text()
    return CustomerBook.model_validate(json.loads(payload))
