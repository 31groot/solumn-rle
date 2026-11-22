"""Turn raw feed records into store rows: prices in the store currency, clean titles."""
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
_SYMBOLS = re.compile(r"[\s$€£₹,]")


class UnknownCurrency(ValueError):
    """No exchange rate for the record's currency."""


class InvalidPrice(ValueError):
    """The price text is not a non-negative decimal amount."""


def parse_price(text):
    """'1,299.00', ' 24.50 ', '$ 1,049.00', '4.5' -> Decimal. Raises InvalidPrice."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        text = str(text)
    if not isinstance(text, str):
        raise InvalidPrice(repr(text))
    cleaned = _SYMBOLS.sub("", text)
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise InvalidPrice(repr(text)) from None
    if not value.is_finite() or value < 0:
        raise InvalidPrice(repr(text))
    return value


def load_rates(raw_rates):
    """{'USD': '83.20', ...} -> {'USD': Decimal('83.20'), ...} with upper-case codes."""
    rates = {}
    for code, value in raw_rates.items():
        rate = Decimal(str(value))
        if rate <= 0:
            raise ValueError(f"fx rate for {code} must be positive")
        rates[code.upper()] = rate
    return rates


def convert(amount, currency, rates, target):
    """Convert ``amount`` in ``currency`` to ``target``, rounded half-up to 0.01."""
    src, dst = currency.upper(), target.upper()
    if src not in rates:
        raise UnknownCurrency(src)
    if dst not in rates:
        raise UnknownCurrency(dst)
    if src == dst:
        return amount.quantize(CENT, ROUND_HALF_UP)
    return (amount * rates[src] / rates[dst]).quantize(CENT, ROUND_HALF_UP)


def to_minor(amount):
    """Decimal('1299.50') -> 129950 (paise/cents)."""
    return int((amount.quantize(CENT, ROUND_HALF_UP) * 100).to_integral_value())


def clean_title(title):
    return " ".join(str(title).split())


def normalize_item(raw, rates, target):
    """Feed product record -> store row. Raises InvalidPrice / UnknownCurrency / KeyError."""
    price = convert(parse_price(raw["price"]), str(raw["currency"]), rates, target)
    stock = raw.get("stock")
    return {
        "sku": raw["sku"],
        "title": clean_title(raw["title"]),
        "price_minor": to_minor(price),
        "currency": target.upper(),
        "stock": int(stock) if stock is not None else 0,
        "updated_at": raw["updated_at"],
    }
