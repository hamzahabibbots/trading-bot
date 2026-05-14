"""
Input validators for the trading bot.
Provides validation for symbols, order sides, types, quantities, and prices.
"""

import logging
from typing import Optional

logger = logging.getLogger("trading_bot")

# Supported trading pairs on Binance Futures Testnet
VALID_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT",
    "XRPUSDT", "DOTUSDT", "SOLUSDT", "LTCUSDT", "AVAXUSDT",
    "LINKUSDT", "MATICUSDT", "UNIUSDT", "ATOMUSDT", "NEARUSDT",
}

VALID_SIDES = {"BUY", "SELL"}

VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}


class ValidationError(Exception):
    """Raised when user input fails validation."""
    pass


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise a trading pair symbol.

    Args:
        symbol: Trading pair (e.g. 'btcusdt' or 'BTCUSDT').

    Returns:
        Uppercase symbol string.

    Raises:
        ValidationError: If symbol is not recognised.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    if symbol not in VALID_SYMBOLS:
        logger.warning(
            f"Symbol '{symbol}' not in known list — proceeding anyway "
            "(testnet may support additional pairs)."
        )
    return symbol


def validate_side(side: str) -> str:
    """
    Validate the order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Uppercase side string.

    Raises:
        ValidationError: If side is invalid.
    """
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of: {', '.join(VALID_SIDES)}")
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate the order type.

    Args:
        order_type: 'MARKET', 'LIMIT', or 'STOP_LIMIT' (case-insensitive).

    Returns:
        Uppercase order type string.

    Raises:
        ValidationError: If order type is invalid.
    """
    order_type = order_type.strip().upper().replace("-", "_")
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of: {', '.join(VALID_ORDER_TYPES)}"
        )
    return order_type


def validate_quantity(quantity: float) -> float:
    """
    Validate order quantity.

    Args:
        quantity: The amount to trade.

    Returns:
        Validated quantity as float.

    Raises:
        ValidationError: If quantity is not positive.
    """
    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive, got {quantity}.")
    return quantity


def validate_price(price: Optional[float], order_type: str) -> Optional[float]:
    """
    Validate price — required for LIMIT and STOP_LIMIT orders.

    Args:
        price: The limit price (can be None for MARKET orders).
        order_type: The validated order type.

    Returns:
        Validated price or None.

    Raises:
        ValidationError: If price is missing for LIMIT/STOP_LIMIT or is non-positive.
    """
    if order_type in ("LIMIT", "STOP_LIMIT"):
        if price is None or price <= 0:
            raise ValidationError(
                f"Price is required and must be positive for {order_type} orders."
            )
    return price


def validate_stop_price(stop_price: Optional[float], order_type: str) -> Optional[float]:
    """
    Validate stop price — required for STOP_LIMIT orders.

    Args:
        stop_price: The trigger/stop price.
        order_type: The validated order type.

    Returns:
        Validated stop price or None.

    Raises:
        ValidationError: If stop price is missing for STOP_LIMIT orders.
    """
    if order_type == "STOP_LIMIT":
        if stop_price is None or stop_price <= 0:
            raise ValidationError(
                "Stop price is required and must be positive for STOP_LIMIT orders."
            )
    return stop_price


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> dict:
    """
    Run all validations and return a cleaned parameter dict.

    Returns:
        Dictionary with validated order parameters.

    Raises:
        ValidationError: On any validation failure.
    """
    validated = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, validate_order_type(order_type)),
        "stop_price": validate_stop_price(stop_price, validate_order_type(order_type)),
    }
    logger.debug(f"Validation passed: {validated}")
    return validated
