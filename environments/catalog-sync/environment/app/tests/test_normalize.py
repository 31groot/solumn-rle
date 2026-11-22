from decimal import Decimal

import pytest

from normalize import (InvalidPrice, UnknownCurrency, clean_title, convert, load_rates,
                       normalize_item, parse_price, to_minor)

RATES = load_rates({"INR": "1", "USD": "83.20", "EUR": "90.45", "GBP": "105.10"})


@pytest.mark.parametrize("text,expected", [
    ("1,299.00", Decimal("1299.00")),
    (" 24.50 ", Decimal("24.50")),
    ("$ 1,049.00", Decimal("1049.00")),
    ("4.5", Decimal("4.5")),
    ("2499", Decimal("2499")),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", ["call for price", "", "-3.00", "NaN", None])
def test_parse_price_rejects(text):
    with pytest.raises(InvalidPrice):
        parse_price(text)


def test_convert_to_inr():
    assert convert(Decimal("19.99"), "USD", RATES, "INR") == Decimal("1663.17")
    assert convert(Decimal("4.5"), "eur", RATES, "INR") == Decimal("407.03")
    assert convert(Decimal("996"), "INR", RATES, "INR") == Decimal("996.00")


def test_convert_unknown_currency():
    with pytest.raises(UnknownCurrency):
        convert(Decimal("1"), "JPY", RATES, "INR")


def test_minor_units_and_titles():
    assert to_minor(Decimal("1663.17")) == 166317
    assert clean_title("  Eco\tSticky   Notes ") == "Eco Sticky Notes"


def test_normalize_item_defaults_stock():
    row = normalize_item({"sku": "A", "title": "x", "price": "1.00", "currency": "GBP",
                          "updated_at": "2026-11-01T00:00:00Z"}, RATES, "INR")
    assert row == {"sku": "A", "title": "x", "price_minor": 10510, "currency": "INR",
                   "stock": 0, "updated_at": "2026-11-01T00:00:00Z"}
