"""
Flask API for Binance Futures Testnet Trading Bot.
Deployed as a Vercel serverless function.
"""

import os
import hashlib
import hmac
import time
import json
from urllib.parse import urlencode

from flask import Flask, request, jsonify, send_from_directory
import requests as http_requests

app = Flask(__name__, static_folder="../public", static_url_path="")

# ── Config ──
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BASE_URL = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")


def _sign(params: dict) -> dict:
    """Add timestamp and HMAC-SHA256 signature."""
    params["timestamp"] = int(time.time() * 1000)
    query_string = urlencode(params)
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    params["signature"] = signature
    return params


def _api_request(method: str, endpoint: str, params: dict = None, signed: bool = False):
    """Make a request to Binance Futures API."""
    url = f"{BASE_URL}{endpoint}"
    params = params or {}
    headers = {"X-MBX-APIKEY": API_KEY}

    if signed:
        params = _sign(params)

    try:
        if method == "GET":
            resp = http_requests.get(url, params=params, headers=headers, timeout=10)
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            resp = http_requests.post(url, data=params, headers=headers, timeout=10)

        data = resp.json() if resp.content else {}

        if resp.status_code >= 400:
            return {
                "success": False,
                "error": data.get("msg", resp.text),
                "code": data.get("code", -1),
            }, resp.status_code

        return {"success": True, "data": data}, 200

    except http_requests.ConnectionError:
        return {"success": False, "error": "Connection failed"}, 503
    except http_requests.Timeout:
        return {"success": False, "error": "Request timed out"}, 504
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


# ── Routes ──

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/ping")
def ping():
    result, status = _api_request("GET", "/fapi/v1/ping")
    if result["success"]:
        return jsonify({"success": True, "message": "API is reachable"})
    return jsonify(result), status


@app.route("/api/price")
def price():
    symbol = request.args.get("symbol", "BTCUSDT")
    result, status = _api_request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})
    return jsonify(result), status


@app.route("/api/prices")
def prices():
    """Get prices for multiple symbols."""
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    prices_data = []
    for sym in symbols:
        result, _ = _api_request("GET", "/fapi/v1/ticker/price", {"symbol": sym})
        if result["success"]:
            prices_data.append(result["data"])
    return jsonify({"success": True, "data": prices_data})


@app.route("/api/balance")
def balance():
    if not API_KEY or not API_SECRET:
        return jsonify({"success": False, "error": "API credentials not configured"}), 401
    result, status = _api_request("GET", "/fapi/v2/balance", signed=True)
    if result["success"]:
        # Filter non-zero balances
        filtered = [b for b in result["data"] if float(b.get("balance", 0)) > 0]
        return jsonify({"success": True, "data": filtered})
    return jsonify(result), status


@app.route("/api/order", methods=["POST"])
def place_order():
    if not API_KEY or not API_SECRET:
        return jsonify({"success": False, "error": "API credentials not configured"}), 401

    body = request.get_json(force=True)

    # Validate
    symbol = (body.get("symbol") or "").strip().upper()
    side = (body.get("side") or "").strip().upper()
    order_type = (body.get("type") or "").strip().upper()
    quantity = body.get("quantity")
    price = body.get("price")
    stop_price = body.get("stopPrice")

    errors = []
    if not symbol:
        errors.append("Symbol is required")
    if side not in ("BUY", "SELL"):
        errors.append("Side must be BUY or SELL")
    if order_type not in ("MARKET", "LIMIT", "STOP"):
        errors.append("Type must be MARKET, LIMIT, or STOP_LIMIT")
    if not quantity or float(quantity) <= 0:
        errors.append("Quantity must be positive")
    if order_type == "LIMIT" and (not price or float(price) <= 0):
        errors.append("Price is required for LIMIT orders")
    if order_type == "STOP":
        if not price or float(price) <= 0:
            errors.append("Price is required for STOP_LIMIT orders")
        if not stop_price or float(stop_price) <= 0:
            errors.append("Stop price is required for STOP_LIMIT orders")

    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    # Build params
    params = {
        "symbol": symbol,
        "side": side,
        "type": order_type if order_type != "STOP_LIMIT" else "STOP",
        "quantity": str(quantity),
    }

    if order_type in ("LIMIT", "STOP"):
        params["price"] = str(price)
        params["timeInForce"] = "GTC"
    if order_type == "STOP":
        params["stopPrice"] = str(stop_price)

    result, status = _api_request("POST", "/fapi/v1/order", params, signed=True)
    return jsonify(result), status


@app.route("/api/orders")
def open_orders():
    if not API_KEY or not API_SECRET:
        return jsonify({"success": False, "error": "API credentials not configured"}), 401
    symbol = request.args.get("symbol")
    params = {}
    if symbol:
        params["symbol"] = symbol
    result, status = _api_request("GET", "/fapi/v1/openOrders", params, signed=True)
    return jsonify(result), status


@app.route("/api/order/cancel", methods=["POST"])
def cancel_order():
    if not API_KEY or not API_SECRET:
        return jsonify({"success": False, "error": "API credentials not configured"}), 401
    body = request.get_json(force=True)
    params = {
        "symbol": body.get("symbol", ""),
        "orderId": body.get("orderId", ""),
    }
    result, status = _api_request("DELETE", "/fapi/v1/order", params, signed=True)
    return jsonify(result), status
