import pytest

from order_desk.catalog import Catalog, load_catalog


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return load_catalog()


def test_loads_expected_shape(catalog: Catalog) -> None:
    assert catalog.company == "Meridian Packaging Supplies"
    assert len(catalog.products) == 23
    assert set(catalog.units) == {"each", "carton", "roll", "pallet", "pack"}


def test_sku_resolution_is_case_and_whitespace_insensitive(catalog: Catalog) -> None:
    assert catalog.resolve_sku("ctn-sm-001").sku == "CTN-SM-001"
    assert catalog.resolve_sku("  Shrink   Wrap ").sku == "FLM-HND-101"
    assert catalog.resolve_sku("Euro Pallet").sku == "PAL-EUR-602"
    assert catalog.resolve_sku("nonexistent widget") is None


def test_unit_resolution(catalog: Catalog) -> None:
    assert catalog.resolve_unit("ctns") == "carton"
    assert catalog.resolve_unit("Rolls") == "roll"
    assert catalog.resolve_unit("bag") == "pack"
    assert catalog.resolve_unit("carton") == "carton"
    assert catalog.resolve_unit("bunch") is None


def test_discontinued_sku_present_for_validation_cases(catalog: Catalog) -> None:
    steel = catalog.resolve_sku("steel strapping")
    assert steel is not None
    assert steel.sku == "STR-STL-703"
    assert steel.active is False
    assert all(p.active for p in catalog.active_products)


def test_pack_size_spot_checks(catalog: Catalog) -> None:
    assert catalog.resolve_sku("LBL-4X6-301").pack_size == 500
    assert catalog.resolve_sku("poly mailers").pack_size == 500
