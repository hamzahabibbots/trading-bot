"""
Order placement logic.
Bridges validated user input → Binance API calls, with result formatting.
"""

import logging
from typing import Any, Dict, Optional

from bot.client import BinanceClient, BinanceAPIError

logger = logging.getLogger("trading_bot")


class OrderResult:
    """Structured representation of an order response."""

    def __init__(self, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error

    @property
    def order_id(self) -> Optional[int]:
        return self.data.get("orderId")

    @property
    def status(self) -> Optional[str]:
        return self.data.get("status")

    @property
    def executed_qty(self) -> Optional[str]:
        return self.data.get("executedQty")

    @property
    def avg_price(self) -> Optional[str]:
        return self.data.get("avgPrice") or self.data.get("price")

    @property
    def symbol(self) -> Optional[str]:
        return self.data.get("symbol")

    @property
    def side(self) -> Optional[str]:
        return self.data.get("side")

    @property
    def order_type(self) -> Optional[str]:
        return self.data.get("type")

    @property
    def orig_qty(self) -> Optional[str]:
        return self.data.get("origQty")

    def summary(self) -> Dict[str, Any]:
        """Return a clean summary dict for display."""
        if self.success:
            return {
                "Order ID": self.order_id,
                "Symbol": self.symbol,
                "Side": self.side,
                "Type": self.order_type,
                "Status": self.status,
                "Original Qty": self.orig_qty,
                "Executed Qty": self.executed_qty,
                "Avg Price": self.avg_price,
            }
        return {"Error": self.error}


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
) -> OrderResult:
    """
    Place a MARKET order.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair (e.g. BTCUSDT).
        side: BUY or SELL.
        quantity: Amount to trade.

    Returns:
        OrderResult with success/failure details.
    """
    logger.info(f"Preparing MARKET order: {side} {quantity} {symbol}")

    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=str(quantity),
        )
        logger.info(f"MARKET order placed successfully: orderId={response.get('orderId')}")
        logger.debug(f"Full response: {response}")
        return OrderResult(success=True, data=response)

    except BinanceAPIError as e:
        logger.error(f"MARKET order failed: {e}")
        return OrderResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error placing MARKET order: {e}")
        return OrderResult(success=False, error=f"Unexpected error: {e}")


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Place a LIMIT order.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair (e.g. BTCUSDT).
        side: BUY or SELL.
        quantity: Amount to trade.
        price: Limit price.
        time_in_force: GTC (Good Till Cancel), IOC, or FOK.

    Returns:
        OrderResult with success/failure details.
    """
    logger.info(f"Preparing LIMIT order: {side} {quantity} {symbol} @ {price}")

    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            quantity=str(quantity),
            price=str(price),
            timeInForce=time_in_force,
        )
        logger.info(f"LIMIT order placed successfully: orderId={response.get('orderId')}")
        logger.debug(f"Full response: {response}")
        return OrderResult(success=True, data=response)

    except BinanceAPIError as e:
        logger.error(f"LIMIT order failed: {e}")
        return OrderResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error placing LIMIT order: {e}")
        return OrderResult(success=False, error=f"Unexpected error: {e}")


def place_stop_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Place a STOP_LIMIT (STOP) order.

    The order becomes a limit order once the stop_price is reached.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair (e.g. BTCUSDT).
        side: BUY or SELL.
        quantity: Amount to trade.
        price: Limit price (the price to execute at once triggered).
        stop_price: Trigger/stop price.
        time_in_force: GTC (Good Till Cancel), IOC, or FOK.

    Returns:
        OrderResult with success/failure details.
    """
    logger.info(
        f"Preparing STOP_LIMIT order: {side} {quantity} {symbol} "
        f"@ limit={price}, stop={stop_price}"
    )

    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            type="STOP",
            quantity=str(quantity),
            price=str(price),
            stopPrice=str(stop_price),
            timeInForce=time_in_force,
        )
        logger.info(f"STOP_LIMIT order placed successfully: orderId={response.get('orderId')}")
        logger.debug(f"Full response: {response}")
        return OrderResult(success=True, data=response)

    except BinanceAPIError as e:
        logger.error(f"STOP_LIMIT order failed: {e}")
        return OrderResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error placing STOP_LIMIT order: {e}")
        return OrderResult(success=False, error=f"Unexpected error: {e}")


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> OrderResult:
    """
    Unified order placement — dispatches to the correct handler based on order type.

    Args:
        client: Authenticated BinanceClient instance.
        symbol: Trading pair.
        side: BUY or SELL.
        order_type: MARKET, LIMIT, or STOP_LIMIT.
        quantity: Amount to trade.
        price: Limit price (required for LIMIT and STOP_LIMIT).
        stop_price: Stop/trigger price (required for STOP_LIMIT).

    Returns:
        OrderResult with success/failure details.
    """
    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)
    elif order_type == "LIMIT":
        return place_limit_order(client, symbol, side, quantity, price)
    elif order_type == "STOP_LIMIT":
        return place_stop_limit_order(client, symbol, side, quantity, price, stop_price)
    else:
        error_msg = f"Unsupported order type: {order_type}"
        logger.error(error_msg)
        return OrderResult(success=False, error=error_msg)
