# 🤖 Binance Futures Testnet Trading Bot

A structured Python trading bot for placing orders on **Binance Futures Testnet (USDT-M)**. Supports Market, Limit, and Stop-Limit orders with a clean CLI interface, comprehensive logging, and robust error handling.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Market Orders** | Instant execution at current market price |
| **Limit Orders** | Execute at a specified price or better |
| **Stop-Limit Orders** *(Bonus)* | Conditional orders triggered at a stop price |
| **Interactive Mode** *(Bonus)* | Guided CLI with prompts, validation, and menus |
| **Rich CLI Output** | Beautiful terminal UI with color-coded tables |
| **Structured Logging** | All API requests/responses logged to file |
| **Input Validation** | Symbol, side, type, quantity, and price validation |
| **Account Balance** | Check testnet account balances |
| **Open Orders** | View all currently open orders |

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package init
│   ├── client.py            # Binance REST API client (HMAC signing)
│   ├── orders.py            # Order placement logic
│   ├── validators.py        # Input validation
│   └── logging_config.py    # Dual-handler logging setup
├── logs/                    # Auto-generated log files
├── cli.py                   # CLI entry point (Click + Rich)
├── .env                     # API credentials (git-ignored)
├── .env.example             # Template for credentials
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Setup

### Prerequisites

- Python 3.8+
- A Binance Futures Testnet account with API key and secret
  - Get one at: https://testnet.binancefuture.com/

### Installation

```bash
# 1. Clone or unzip the project
cd trading_bot

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env and add your API key and secret:
#   BINANCE_API_KEY=your_key
#   BINANCE_API_SECRET=your_secret
```

---

## 📖 Usage

### Test API Connectivity

```bash
python cli.py ping
```

### Check Account Balance

```bash
python cli.py balance
```

### View Open Orders

```bash
python cli.py orders
```

### Place a Market Order

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Place a Limit Order

```bash
python cli.py order \
  --symbol ETHUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.01 \
  --price 4000.00
```

### Place a Stop-Limit Order (Bonus)

```bash
python cli.py order \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_LIMIT \
  --quantity 0.001 \
  --price 99000.00 \
  --stop-price 99500.00
```

### Interactive Mode (Bonus)

```bash
python cli.py interactive
```

Launches a guided experience with prompts for each parameter, validation feedback, and confirmation before sending.

---

## 🖥️ CLI Reference

| Command | Description |
|---------|-------------|
| `cli.py ping` | Test API connectivity |
| `cli.py balance` | Show account balances |
| `cli.py orders` | List open orders |
| `cli.py order` | Place an order (with flags) |
| `cli.py interactive` | Interactive order placement |
| `cli.py --help` | Show all commands |
| `cli.py order --help` | Show order options |

### Order Flags

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--symbol` | `-s` | ✅ | Trading pair (e.g., BTCUSDT) |
| `--side` | `-d` | ✅ | BUY or SELL |
| `--type` | `-t` | ✅ | MARKET, LIMIT, or STOP_LIMIT |
| `--quantity` | `-q` | ✅ | Order quantity |
| `--price` | `-p` | For LIMIT/STOP_LIMIT | Limit price |
| `--stop-price` | `-sp` | For STOP_LIMIT | Stop/trigger price |

---

## 📝 Logging

All API interactions are logged to `logs/trading_bot_YYYYMMDD_HHMMSS.log` with:

- **DEBUG**: Full request/response bodies, signed query strings
- **INFO**: Order summaries, connection status
- **WARNING**: Unknown symbols, retries
- **ERROR**: API errors, validation failures, network issues

Console output shows INFO-level and above for clean UX.

---

## 🧪 Example Log Output

```
2026-05-14 23:45:12 | INFO     | trading_bot.setup_logging:55 | Logging initialized → logs/trading_bot_20260514_234512.log
2026-05-14 23:45:12 | INFO     | trading_bot.__init__:62 | BinanceClient initialised → https://testnet.binancefuture.com
2026-05-14 23:45:12 | INFO     | trading_bot.place_market_order:72 | Preparing MARKET order: BUY 0.001 BTCUSDT
2026-05-14 23:45:12 | DEBUG    | trading_bot._request:95 | → POST https://testnet.binancefuture.com/fapi/v1/order
2026-05-14 23:45:13 | DEBUG    | trading_bot._request:99 | ← HTTP 200 | 412 bytes
2026-05-14 23:45:13 | INFO     | trading_bot.place_market_order:82 | MARKET order placed successfully: orderId=123456789
```

---

## ⚠️ Assumptions

1. **Testnet only** — This bot is configured for Binance Futures Testnet. Do NOT use with real funds.
2. **USDT-M pairs** — All trading pairs are USDT-margined futures.
3. **No position management** — The bot places orders but does not manage positions or implement strategies.
4. **API rate limits** — No rate-limiting logic is implemented; the testnet is lenient.
5. **Symbol validation** — Common symbols are hard-coded for the interactive chooser, but any valid testnet symbol can be used via CLI flags.
6. **Quantity precision** — The bot sends quantities as-is. For production, you'd want to respect each symbol's step size from exchange info.

---

## 🛡️ Error Handling

The bot handles:

- **Invalid input** → `ValidationError` with clear messages
- **API errors** → `BinanceAPIError` with HTTP status, error code, and message
- **Network failures** → `ConnectionError`, `Timeout` caught and logged
- **Missing credentials** → Checked at startup with actionable error messages
- **Unexpected errors** → Caught with full stack trace in log file

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP REST API calls |
| `python-dotenv` | Load `.env` configuration |
| `click` | CLI argument parsing |
| `rich` | Beautiful terminal output (tables, panels, colors) |

---

## License

MIT — Use at your own risk. This is for educational/testnet purposes only.
