"""
Telegram Bot interface for Binance Futures Testnet Trading Bot.
Provides inline keyboard menus for placing orders, checking balance, and viewing prices.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot.client import BinanceClient, BinanceAPIError
from bot.orders import place_order
from bot.logging_config import setup_logging

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
logger = setup_logging(log_dir=LOG_DIR)

# ── Conversation states ──
SYMBOL, SIDE, TYPE, QUANTITY, PRICE, STOP_PRICE, CONFIRM = range(7)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]


def get_client() -> BinanceClient:
    return BinanceClient(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        base_url=os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com"),
    )


# ── /start ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Binance Futures Testnet Bot*\n\n"
        "Commands:\n"
        "  /trade — Place a new order\n"
        "  /balance — Check account balance\n"
        "  /prices — View live prices\n"
        "  /orders — View open orders\n"
        "  /ping — Test API connection\n"
        "  /help — Show this message",
        parse_mode="Markdown",
    )


# ── /ping ──
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = get_client()
    if client.ping():
        try:
            ticker = client.get_ticker_price("BTCUSDT")
            price = float(ticker["price"])
            await update.message.reply_text(f"✅ API connected\nBTCUSDT: `${price:,.2f}`", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("✅ API connected")
    else:
        await update.message.reply_text("❌ API unreachable")


# ── /balance ──
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        client = get_client()
        balances = client.get_balance()
        lines = ["💰 *Account Balances*\n"]
        for b in balances:
            bal = float(b.get("balance", 0))
            avail = float(b.get("availableBalance", 0))
            if bal > 0:
                lines.append(f"  `{b['asset']:>6}` — Balance: `{bal:,.4f}` / Avail: `{avail:,.4f}`")
        if len(lines) == 1:
            lines.append("  No balances found")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except BinanceAPIError as e:
        await update.message.reply_text(f"❌ API Error: {e.message}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /prices ──
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        client = get_client()
        lines = ["📊 *Live Prices*\n"]
        for sym in SYMBOLS:
            try:
                t = client.get_ticker_price(sym)
                p = float(t["price"])
                lines.append(f"  `{sym:>10}` — `${p:>12,.2f}`")
            except Exception:
                lines.append(f"  `{sym:>10}` — unavailable")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /orders ──
async def open_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        client = get_client()
        orders_list = client.get_open_orders()
        if not orders_list:
            await update.message.reply_text("📝 No open orders")
            return
        lines = ["📝 *Open Orders*\n"]
        for o in orders_list[:10]:
            side_emoji = "🟢" if o["side"] == "BUY" else "🔴"
            lines.append(
                f"  {side_emoji} `{o['symbol']}` {o['side']} {o['type']} "
                f"qty:`{o.get('origQty', '?')}` @ `{o.get('price', 'MKT')}`\n"
                f"     ID: `{o['orderId']}`"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except BinanceAPIError as e:
        await update.message.reply_text(f"❌ API Error: {e.message}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ═══════════════════════════════════════
#  /trade — Conversation Flow
# ═══════════════════════════════════════

async def trade_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Choose symbol."""
    keyboard = [[InlineKeyboardButton(s, callback_data=f"sym_{s}")] for s in SYMBOLS[:3]]
    keyboard.append([InlineKeyboardButton(s, callback_data=f"sym_{s}") for s in SYMBOLS[3:]])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    await update.message.reply_text(
        "📋 *New Order — Step 1/5*\nSelect symbol:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return SYMBOL


async def symbol_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Choose side."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Order cancelled.")
        return ConversationHandler.END

    context.user_data["symbol"] = query.data.replace("sym_", "")

    keyboard = [
        [InlineKeyboardButton("🟢 BUY / Long", callback_data="side_BUY"),
         InlineKeyboardButton("🔴 SELL / Short", callback_data="side_SELL")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await query.edit_message_text(
        f"📋 *New Order — Step 2/5*\n"
        f"Symbol: `{context.user_data['symbol']}`\n\nSelect side:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return SIDE


async def side_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Choose order type."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Order cancelled.")
        return ConversationHandler.END

    context.user_data["side"] = query.data.replace("side_", "")

    keyboard = [
        [InlineKeyboardButton("⚡ Market", callback_data="type_MARKET"),
         InlineKeyboardButton("📌 Limit", callback_data="type_LIMIT")],
        [InlineKeyboardButton("🛑 Stop-Limit", callback_data="type_STOP_LIMIT")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    side_emoji = "🟢" if context.user_data["side"] == "BUY" else "🔴"
    await query.edit_message_text(
        f"📋 *New Order — Step 3/5*\n"
        f"Symbol: `{context.user_data['symbol']}`\n"
        f"Side: {side_emoji} `{context.user_data['side']}`\n\nSelect order type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return TYPE


async def type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 4: Enter quantity."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Order cancelled.")
        return ConversationHandler.END

    context.user_data["order_type"] = query.data.replace("type_", "")

    await query.edit_message_text(
        f"📋 *New Order — Step 4*\n"
        f"Symbol: `{context.user_data['symbol']}`\n"
        f"Side: `{context.user_data['side']}`\n"
        f"Type: `{context.user_data['order_type']}`\n\n"
        f"Enter quantity (e.g. `0.001`):",
        parse_mode="Markdown",
    )
    return QUANTITY


async def quantity_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity input, then ask price if needed."""
    try:
        qty = float(update.message.text.strip())
        if qty <= 0:
            raise ValueError
        context.user_data["quantity"] = qty
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity. Enter a positive number:")
        return QUANTITY

    order_type = context.user_data["order_type"]
    if order_type in ("LIMIT", "STOP_LIMIT"):
        await update.message.reply_text(
            f"Enter limit price (USDT):",
            parse_mode="Markdown",
        )
        return PRICE
    else:
        # Market order — skip to confirm
        context.user_data["price"] = None
        context.user_data["stop_price"] = None
        return await show_confirmation(update, context)


async def price_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle price input."""
    try:
        price = float(update.message.text.strip())
        if price <= 0:
            raise ValueError
        context.user_data["price"] = price
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Enter a positive number:")
        return PRICE

    if context.user_data["order_type"] == "STOP_LIMIT":
        await update.message.reply_text("Enter stop/trigger price (USDT):")
        return STOP_PRICE
    else:
        context.user_data["stop_price"] = None
        return await show_confirmation(update, context)


async def stop_price_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stop price input."""
    try:
        sp = float(update.message.text.strip())
        if sp <= 0:
            raise ValueError
        context.user_data["stop_price"] = sp
    except ValueError:
        await update.message.reply_text("❌ Invalid stop price. Enter a positive number:")
        return STOP_PRICE

    return await show_confirmation(update, context)


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show order summary and confirm."""
    d = context.user_data
    side_emoji = "🟢" if d["side"] == "BUY" else "🔴"

    text = (
        f"📋 *Order Summary*\n\n"
        f"  Symbol: `{d['symbol']}`\n"
        f"  Side: {side_emoji} `{d['side']}`\n"
        f"  Type: `{d['order_type']}`\n"
        f"  Quantity: `{d['quantity']}`\n"
    )
    if d.get("price"):
        text += f"  Price: `${d['price']:,.2f}`\n"
    if d.get("stop_price"):
        text += f"  Stop Price: `${d['stop_price']:,.2f}`\n"
    text += "\nConfirm this order?"

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")],
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute or cancel the order."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("Order cancelled.")
        return ConversationHandler.END

    d = context.user_data
    await query.edit_message_text("⏳ Placing order...")

    try:
        client = get_client()
        ot = d["order_type"]
        if ot == "STOP_LIMIT":
            ot = "STOP_LIMIT"

        result = place_order(
            client,
            symbol=d["symbol"],
            side=d["side"],
            order_type=ot,
            quantity=d["quantity"],
            price=d.get("price"),
            stop_price=d.get("stop_price"),
        )

        if result.success:
            s = result.summary()
            text = (
                f"✅ *Order Placed Successfully*\n\n"
                f"  Order ID: `{s.get('Order ID')}`\n"
                f"  Symbol: `{s.get('Symbol')}`\n"
                f"  Side: `{s.get('Side')}`\n"
                f"  Type: `{s.get('Type')}`\n"
                f"  Status: `{s.get('Status')}`\n"
                f"  Quantity: `{s.get('Original Qty')}`\n"
                f"  Executed: `{s.get('Executed Qty')}`\n"
                f"  Avg Price: `{s.get('Avg Price')}`"
            )
        else:
            text = f"❌ *Order Failed*\n\n`{result.error}`"

        await query.edit_message_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Order error: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Error: {e}")

    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    await update.message.reply_text("Order cancelled.")
    return ConversationHandler.END


# ── Main ──
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
        return

    app = Application.builder().token(token).build()

    # Conversation handler for /trade
    trade_conv = ConversationHandler(
        entry_points=[CommandHandler("trade", trade_start)],
        states={
            SYMBOL: [CallbackQueryHandler(symbol_chosen)],
            SIDE: [CallbackQueryHandler(side_chosen)],
            TYPE: [CallbackQueryHandler(type_chosen)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity_entered)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_entered)],
            STOP_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, stop_price_entered)],
            CONFIRM: [CallbackQueryHandler(confirm_order)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    app.add_handler(trade_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("prices", prices))
    app.add_handler(CommandHandler("orders", open_orders))

    logger.info("Telegram bot starting...")
    print("🤖 Telegram bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
