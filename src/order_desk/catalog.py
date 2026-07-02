"""Product catalog: ground truth for validation rules and corpus generation."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources

from pydantic import BaseModel, Field, field_validator, model_validator

SKU_RE = re.compile(r"^[A-Z]{3}-[A-Z0-9]{2,3}-\d{3}$")


def normalize(text: str) -> str:
    """Lowercase, trim, and collapse internal whitespace."""
    return " ".join(text.split()).lower()


class Product(BaseModel):
    sku: str
    name: str
    aliases: list[str] = Field(min_length=1)
    category: str
    unit: str
    pack_size: int | None = Field(default=None, ge=2)
    moq: int = Field(ge=1)
    max_qty: int = Field(ge=1)
    unit_price_cents: int = Field(ge=1)
    active: bool = True

    @field_validator("sku")
    @classmethod
    def sku_matches_pattern(cls, v: str) -> str:
        if not SKU_RE.fullmatch(v):
            raise ValueError(f"SKU {v!r} does not match {SKU_RE.pattern}")
        return v

    @field_validator("aliases")
    @classmethod
    def aliases_are_normalized_and_unique(cls, v: list[str]) -> list[str]:
        for alias in v:
            if alias != normalize(alias):
                raise ValueError(f"alias {alias!r} must be lowercase and trimmed")
        if len(set(v)) != len(v):
            raise ValueError("duplicate alias within product")
        return v

    @model_validator(mode="after")
    def qty_range_is_sane(self) -> Product:
        if self.max_qty < self.moq:
            raise ValueError(f"{self.sku}: max_qty {self.max_qty} < moq {self.moq}")
        return self


class Catalog(BaseModel):
    version: int
    company: str
    units: dict[str, list[str]]
    products: list[Product]

    @model_validator(mode="after")
    def integrity(self) -> Catalog:
        # Unit terms (canonical + aliases) must be normalized and globally unique.
        seen_unit_terms: set[str] = set(self.units)
        for aliases in self.units.values():
            for alias in aliases:
                if alias != normalize(alias):
                    raise ValueError(f"unit alias {alias!r} must be lowercase and trimmed")
                if alias in seen_unit_terms:
                    raise ValueError(f"unit term {alias!r} is ambiguous")
                seen_unit_terms.add(alias)
        # SKUs unique; units known; product terms (name + aliases) globally unique
        # so that resolve_sku is deterministic.
        seen_skus: set[str] = set()
        seen_terms: set[str] = set()
        for product in self.products:
            if product.sku in seen_skus:
                raise ValueError(f"duplicate SKU {product.sku}")
            seen_skus.add(product.sku)
            if product.unit not in self.units:
                raise ValueError(f"{product.sku}: unknown unit {product.unit!r}")
            for term in (normalize(product.name), *product.aliases):
                if term in seen_terms:
                    raise ValueError(f"product term {term!r} is ambiguous")
                seen_terms.add(term)
        return self

    def resolve_sku(self, text: str) -> Product | None:
        """Exact match on SKU (case-insensitive) or on normalized name/alias."""
        upper = text.strip().upper()
        norm = normalize(text)
        for product in self.products:
            if product.sku == upper or normalize(product.name) == norm or norm in product.aliases:
                return product
        return None

    def resolve_unit(self, text: str) -> str | None:
        norm = normalize(text)
        for canonical, aliases in self.units.items():
            if norm == canonical or norm in aliases:
                return canonical
        return None

    @property
    def active_products(self) -> list[Product]:
        return [p for p in self.products if p.active]


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    payload = resources.files("order_desk.fixtures").joinpath("catalog.json").read_text()
    return Catalog.model_validate(json.loads(payload))
