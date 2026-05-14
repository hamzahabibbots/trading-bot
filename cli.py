#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Supports both direct CLI arguments and an interactive menu mode.
Uses Click for argument parsing and Rich for beautiful terminal output.

Usage:
    # Direct mode
    python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

    # Interactive mode
    python cli.py interactive

    # Check account balance
    python cli.py balance

    # Ping API
    python cli.py ping
"""

import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, FloatPrompt
from rich import box

from bot.logging_config import setup_logging
from bot.client import BinanceClient, BinanceAPIError
from bot.orders import place_order, OrderResult
from bot.validators import validate_all, ValidationError

# ── Setup ──
load_dotenv()
console = Console()

# Resolve log directory relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
logger = setup_logging(log_dir=LOG_DIR)


def get_client() -> BinanceClient:
    """Create and return an authenticated BinanceClient from env vars."""
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

    if not api_key or api_key == "your_api_key_here":
        console.print("[bold red]✗ BINANCE_API_KEY not set.[/] Configure it in .env file.")
        sys.exit(1)
    if not api_secret or api_secret == "your_api_secret_here" or api_secret == "REPLACE_WITH_YOUR_API_SECRET":
        console.print("[bold red]✗ BINANCE_API_SECRET not set.[/] Configure it in .env file.")
        sys.exit(1)

    return BinanceClient(api_key, api_secret, base_url)


def print_banner():
    """Print the application banner."""
    banner = """
[bold cyan]╔══════════════════════════════════════════════════╗
║       🤖  Binance Futures Testnet Bot  🤖        ║
║                   v1.0.0                         ║
╚══════════════════════════════════════════════════╝[/]
    """
    console.print(banner)


def print_order_request(params: dict):
    """Print a formatted order request summary."""
    table = Table(
        title="📋 Order Request",
        box=box.ROUNDED,
        title_style="bold yellow",
        border_style="yellow",
    )
    table.add_column("Parameter", style="cyan", min_width=12)
    table.add_column("Value", style="white", min_width=20)

    table.add_row("Symbol", params["symbol"])
    table.add_row("Side", f"[green]{params['side']}[/]" if params["side"] == "BUY" else f"[red]{params['side']}[/]")
    table.add_row("Type", params["order_type"])
    table.add_row("Quantity", str(params["quantity"]))
    if params.get("price"):
        table.add_row("Price", str(params["price"]))
    if params.get("stop_price"):
        table.add_row("Stop Price", str(params["stop_price"]))

    console.print(table)


def print_order_result(result: OrderResult):
    """Print a formatted order result."""
    if result.success:
        summary = result.summary()
        table = Table(
            title="✅ Order Placed Successfully",
            box=box.DOUBLE_EDGE,
            title_style="bold green",
            border_style="green",
        )
        table.add_column("Field", style="cyan", min_width=14)
        table.add_column("Value", style="white", min_width=24)

        for key, value in summary.items():
            table.add_row(key, str(value) if value is not None else "—")

        console.print(table)
        console.print(f"\n[bold green]✓ Order {result.order_id} — Status: {result.status}[/]")
    else:
        console.print(Panel(
            f"[bold red]{result.error}[/]",
            title="❌ Order Failed",
            border_style="red",
            box=box.HEAVY,
        ))


# ──────────────────────────────────────────────
#  CLI Commands
# ──────────────────────────────────────────────

@click.group()
def cli():
    """🤖 Binance Futures Testnet Trading Bot"""
    pass


@cli.command()
@click.option("--symbol", "-s", required=True, help="Trading pair (e.g., BTCUSDT)")
@click.option("--side", "-d", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="Order side")
@click.option("--type", "-t", "order_type", required=True, type=click.Choice(["MARKET", "LIMIT", "STOP_LIMIT"], case_sensitive=False), help="Order type")
@click.option("--quantity", "-q", required=True, type=float, help="Order quantity")
@click.option("--price", "-p", type=float, default=None, help="Limit price (required for LIMIT/STOP_LIMIT)")
@click.option("--stop-price", "-sp", type=float, default=None, help="Stop price (required for STOP_LIMIT)")
def order(symbol: str, side: str, order_type: str, quantity: float, price: Optional[float], stop_price: Optional[float]):
    """Place an order on Binance Futures Testnet."""
    print_banner()

    try:
        # Validate inputs
        params = validate_all(symbol, side, order_type, quantity, price, stop_price)
        print_order_request(params)

        # Confirm
        if not Confirm.ask("\n[bold yellow]Proceed with this order?[/]", default=True):
            console.print("[dim]Order cancelled.[/]")
            return

        # Place order
        client = get_client()
        console.print("\n[dim]Sending order to Binance...[/]\n")
        result = place_order(
            client,
            params["symbol"],
            params["side"],
            params["order_type"],
            params["quantity"],
            params["price"],
            params["stop_price"],
        )
        print_order_result(result)

    except ValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        logger.error(f"Unhandled error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def interactive():
    """Launch interactive order placement mode."""
    print_banner()
    console.print("[bold cyan]Interactive Mode[/] — follow the prompts to place an order.\n")

    try:
        # Gather inputs interactively
        symbol = Prompt.ask(
            "[cyan]Symbol[/]",
            default="BTCUSDT",
            choices=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
        )

        side = Prompt.ask(
            "[cyan]Side[/]",
            choices=["BUY", "SELL"],
        )

        order_type = Prompt.ask(
            "[cyan]Order Type[/]",
            choices=["MARKET", "LIMIT", "STOP_LIMIT"],
            default="MARKET",
        )

        quantity = FloatPrompt.ask("[cyan]Quantity[/]")

        price = None
        stop_price = None
        if order_type in ("LIMIT", "STOP_LIMIT"):
            price = FloatPrompt.ask("[cyan]Limit Price[/]")
        if order_type == "STOP_LIMIT":
            stop_price = FloatPrompt.ask("[cyan]Stop Price[/]")

        # Validate
        params = validate_all(symbol, side, order_type, quantity, price, stop_price)
        print_order_request(params)

        if not Confirm.ask("\n[bold yellow]Proceed with this order?[/]", default=True):
            console.print("[dim]Order cancelled.[/]")
            return

        # Place
        client = get_client()
        console.print("\n[dim]Sending order to Binance...[/]\n")
        result = place_order(
            client,
            params["symbol"],
            params["side"],
            params["order_type"],
            params["quantity"],
            params["price"],
            params["stop_price"],
        )
        print_order_result(result)

    except ValidationError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")
        logger.error(f"Validation error: {e}")
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/]")
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        logger.error(f"Unhandled error: {e}", exc_info=True)


@cli.command()
def balance():
    """Check account balance on the testnet."""
    print_banner()
    console.print("[bold cyan]Fetching account balance...[/]\n")

    try:
        client = get_client()
        balances = client.get_balance()

        table = Table(
            title="💰 Account Balances",
            box=box.ROUNDED,
            title_style="bold green",
            border_style="green",
        )
        table.add_column("Asset", style="cyan", min_width=8)
        table.add_column("Balance", style="white", justify="right", min_width=16)
        table.add_column("Available", style="green", justify="right", min_width=16)

        for b in balances:
            bal = float(b.get("balance", 0))
            avail = float(b.get("availableBalance", 0))
            if bal > 0 or avail > 0:
                table.add_row(
                    b["asset"],
                    f"{bal:,.4f}",
                    f"{avail:,.4f}",
                )

        if table.row_count == 0:
            console.print("[yellow]No balances found (or all zero).[/]")
        else:
            console.print(table)

    except BinanceAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        logger.error(f"Balance check failed: {e}")
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        logger.error(f"Balance check error: {e}", exc_info=True)


@cli.command()
def ping():
    """Test API connectivity."""
    print_banner()
    client = get_client()
    if client.ping():
        console.print("[bold green]✓ API is reachable![/]")

        # Also show ticker price as a quick test
        try:
            ticker = client.get_ticker_price("BTCUSDT")
            console.print(f"[dim]BTCUSDT current price: ${float(ticker['price']):,.2f}[/]")
        except Exception:
            pass
    else:
        console.print("[bold red]✗ API is unreachable.[/]")
        sys.exit(1)


@cli.command()
def orders():
    """Show open orders."""
    print_banner()
    console.print("[bold cyan]Fetching open orders...[/]\n")

    try:
        client = get_client()
        open_orders = client.get_open_orders()

        if not open_orders:
            console.print("[yellow]No open orders found.[/]")
            return

        table = Table(
            title="📝 Open Orders",
            box=box.ROUNDED,
            title_style="bold blue",
            border_style="blue",
        )
        table.add_column("Order ID", style="cyan")
        table.add_column("Symbol", style="white")
        table.add_column("Side", style="white")
        table.add_column("Type", style="white")
        table.add_column("Qty", style="white", justify="right")
        table.add_column("Price", style="white", justify="right")
        table.add_column("Status", style="green")

        for o in open_orders:
            side_style = "green" if o["side"] == "BUY" else "red"
            table.add_row(
                str(o["orderId"]),
                o["symbol"],
                f"[{side_style}]{o['side']}[/{side_style}]",
                o["type"],
                o.get("origQty", "—"),
                o.get("price", "—"),
                o.get("status", "—"),
            )

        console.print(table)

    except BinanceAPIError as e:
        console.print(f"[bold red]API Error:[/] {e}")
        logger.error(f"Open orders check failed: {e}")
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        logger.error(f"Open orders error: {e}", exc_info=True)


if __name__ == "__main__":
    cli()
