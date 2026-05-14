"""
Binance Futures Testnet REST API client.
Handles authentication (HMAC-SHA256 signing), request construction, and error handling.
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot")


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, status_code: int, code: int, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message} (HTTP {status_code})")


class BinanceClient:
    """
    Low-level REST client for Binance Futures Testnet.

    Handles:
      - HMAC-SHA256 request signing
      - Automatic timestamp injection
      - Structured error handling & logging
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str):
        """
        Initialise the Binance client.

        Args:
            api_key: Binance API key.
            api_secret: Binance API secret (used for HMAC signing).
            base_url: Testnet base URL (e.g. https://testnet.binancefuture.com).
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })

        logger.info(f"BinanceClient initialised → {self.base_url}")
        logger.debug(f"API Key: {self.api_key[:8]}...{self.api_key[-4:]}")

    # ──────────────────────────────────────────────
    #  Signing
    # ──────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add timestamp and HMAC-SHA256 signature to request params.
        """
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        logger.debug(f"Signed query: {query_string}&signature={signature[:16]}...")
        return params

    # ──────────────────────────────────────────────
    #  HTTP helpers
    # ──────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a request to the Binance Futures API.

        Args:
            method: HTTP method ('GET', 'POST', 'DELETE').
            endpoint: API path (e.g. '/fapi/v1/order').
            params: Query/body parameters.
            signed: Whether to sign the request.

        Returns:
            Parsed JSON response.

        Raises:
            BinanceAPIError: On API-level errors.
            requests.RequestException: On network-level errors.
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug(f"→ {method} {url}")
        logger.debug(f"  Params: { {k: v for k, v in params.items() if k != 'signature'} }")

        try:
            response = self.session.request(method, url, params=params if method == "GET" else None, data=params if method != "GET" else None)
            logger.debug(f"← HTTP {response.status_code} | {len(response.content)} bytes")
            logger.debug(f"  Response: {response.text[:500]}")

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    raise BinanceAPIError(
                        status_code=response.status_code,
                        code=error_data.get("code", -1),
                        message=error_data.get("msg", response.text),
                    )
                except ValueError:
                    raise BinanceAPIError(
                        status_code=response.status_code,
                        code=-1,
                        message=response.text,
                    )

            return response.json()

        except requests.ConnectionError as e:
            logger.error(f"Connection failed: {e}")
            raise
        except requests.Timeout as e:
            logger.error(f"Request timed out: {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            raise

    # ──────────────────────────────────────────────
    #  Public endpoints
    # ──────────────────────────────────────────────

    def ping(self) -> bool:
        """Test API connectivity."""
        try:
            self._request("GET", "/fapi/v1/ping")
            logger.info("API ping successful ✓")
            return True
        except Exception as e:
            logger.error(f"API ping failed: {e}")
            return False

    def get_server_time(self) -> int:
        """Get server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price for a symbol."""
        return self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange trading rules and symbol information."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    # ──────────────────────────────────────────────
    #  Account endpoints (signed)
    # ──────────────────────────────────────────────

    def get_account_info(self) -> Dict[str, Any]:
        """Get current account information."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_balance(self) -> list:
        """Get account balances."""
        return self._request("GET", "/fapi/v2/balance", signed=True)

    # ──────────────────────────────────────────────
    #  Order endpoints (signed)
    # ──────────────────────────────────────────────

    def place_order(self, **params) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures.

        Keyword Args:
            symbol: Trading pair (e.g. BTCUSDT).
            side: BUY or SELL.
            type: MARKET, LIMIT, STOP, etc.
            quantity: Order quantity.
            price: Limit price (optional for MARKET).
            stopPrice: Stop/trigger price (for STOP orders).
            timeInForce: GTC, IOC, FOK (default GTC for LIMIT).
            Additional params as per Binance docs.

        Returns:
            Order response dictionary.
        """
        logger.info(f"Placing order: {params}")
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query an existing order."""
        return self._request(
            "GET", "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an active order."""
        return self._request(
            "DELETE", "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
