// ── State ──
let currentSide = "BUY";
let currentType = "MARKET";

// ── Helpers ──
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const fmt = (n, d = 2) => Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const now = () => new Date().toLocaleTimeString("en-US", { hour12: false }).slice(0, 8);

function log(msg, type = "info") {
    const el = $("#activityLog");
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="time">${now()}</span><span class="msg">${msg}</span>`;
    el.prepend(entry);
    if (el.children.length > 50) el.lastChild.remove();
}

async function api(path, opts = {}) {
    const resp = await fetch(path, opts);
    return resp.json();
}

// ── Prices ──
async function loadPrices() {
    try {
        const res = await api("/api/prices");
        if (!res.success) return;
        const items = $$(".ticker-item");
        res.data.forEach((p, i) => {
            if (items[i]) {
                items[i].querySelector(".ticker-price").textContent = "$" + fmt(p.price);
                items[i].classList.remove("skeleton");
            }
        });
    } catch (e) { /* silent */ }
}

// ── Connection ──
async function checkConnection() {
    try {
        const res = await api("/api/ping");
        if (res.success) {
            $("#connectionStatus").className = "status-dot connected";
            $("#connectionText").textContent = "Connected";
            log("Connected to Binance Futures Testnet", "success");
            return true;
        }
    } catch (e) { /* fall through */ }
    $("#connectionStatus").className = "status-dot disconnected";
    $("#connectionText").textContent = "Disconnected";
    log("Failed to connect to API", "error");
    return false;
}

// ── Balance ──
async function loadBalance() {
    try {
        const res = await api("/api/balance");
        const el = $("#balanceContent");
        if (!res.success) {
            el.innerHTML = `<div class="balance-skeleton">${res.error}</div>`;
            return;
        }
        if (!res.data.length) {
            el.innerHTML = `<div class="balance-skeleton">No balances</div>`;
            return;
        }
        el.innerHTML = res.data.map(b => `
            <div class="balance-row">
                <span class="balance-asset">${b.asset}</span>
                <span class="balance-amount">${fmt(b.balance, 4)}</span>
            </div>
        `).join("");
    } catch (e) {
        $("#balanceContent").innerHTML = `<div class="balance-skeleton">Error loading</div>`;
    }
}

// ── Open Orders ──
async function loadOpenOrders() {
    try {
        const res = await api("/api/orders");
        const el = $("#openOrdersContent");
        if (!res.success) {
            el.innerHTML = `<p class="muted">${res.error}</p>`;
            return;
        }
        if (!res.data || !res.data.length) {
            el.innerHTML = `<p class="muted">No open orders</p>`;
            return;
        }
        el.innerHTML = res.data.map(o => `
            <div class="order-row">
                <span>${o.symbol}</span>
                <span class="side-tag ${o.side.toLowerCase()}">${o.side}</span>
                <span>${o.type}</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:11px">${o.origQty}</span>
                <button class="cancel-btn" onclick="cancelOrder('${o.symbol}',${o.orderId})">Cancel</button>
            </div>
        `).join("");
    } catch (e) {
        $("#openOrdersContent").innerHTML = `<p class="muted">Error loading</p>`;
    }
}

// ── Cancel Order ──
async function cancelOrder(symbol, orderId) {
    log(`Cancelling order ${orderId}...`, "warn");
    try {
        const res = await api("/api/order/cancel", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, orderId }),
        });
        if (res.success) {
            log(`Order ${orderId} cancelled`, "success");
        } else {
            log(`Cancel failed: ${res.error}`, "error");
        }
        loadOpenOrders();
    } catch (e) {
        log(`Cancel error: ${e.message}`, "error");
    }
}

// ── Side Toggle ──
$$(".side-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        $$(".side-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentSide = btn.dataset.side;
        const sub = $("#submitBtn");
        const txt = $("#submitText");
        if (currentSide === "BUY") {
            sub.className = "submit-btn buy-bg";
            txt.textContent = `Place BUY Order`;
        } else {
            sub.className = "submit-btn sell-bg";
            txt.textContent = `Place SELL Order`;
        }
    });
});

// ── Type Tabs ──
$$(".type-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        $$(".type-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentType = btn.dataset.type;
        $("#priceGroup").style.display = (currentType === "LIMIT" || currentType === "STOP") ? "block" : "none";
        $("#stopPriceGroup").style.display = currentType === "STOP" ? "block" : "none";
    });
});

// ── Submit Order ──
$("#orderForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#submitBtn");
    const spinner = $("#submitSpinner");
    const txt = $("#submitText");

    const symbol = $("#symbol").value;
    const quantity = $("#quantity").value;
    const price = $("#price").value;
    const stopPrice = $("#stopPrice").value;

    if (!quantity || Number(quantity) <= 0) {
        log("Quantity must be positive", "error");
        return;
    }
    if ((currentType === "LIMIT" || currentType === "STOP") && (!price || Number(price) <= 0)) {
        log("Price is required for this order type", "error");
        return;
    }
    if (currentType === "STOP" && (!stopPrice || Number(stopPrice) <= 0)) {
        log("Stop price is required for Stop-Limit orders", "error");
        return;
    }

    btn.disabled = true;
    spinner.style.display = "block";
    txt.textContent = "Placing...";

    const payload = { symbol, side: currentSide, type: currentType, quantity };
    if (price) payload.price = price;
    if (stopPrice) payload.stopPrice = stopPrice;

    log(`${currentSide} ${currentType} ${quantity} ${symbol}${price ? " @ $" + price : ""}`, "info");

    try {
        const res = await api("/api/order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const card = $("#resultCard");
        const content = $("#resultContent");
        const title = $("#resultTitle");
        card.style.display = "block";

        if (res.success) {
            const d = res.data;
            card.className = "card result-card success";
            title.textContent = "✅ Order Placed";
            content.innerHTML = `
                <table class="result-table">
                    <tr><td>Order ID</td><td>${d.orderId}</td></tr>
                    <tr><td>Symbol</td><td>${d.symbol}</td></tr>
                    <tr><td>Side</td><td>${d.side}</td></tr>
                    <tr><td>Type</td><td>${d.type}</td></tr>
                    <tr><td>Status</td><td>${d.status}</td></tr>
                    <tr><td>Quantity</td><td>${d.origQty}</td></tr>
                    <tr><td>Executed</td><td>${d.executedQty}</td></tr>
                    <tr><td>Price</td><td>${d.price || "Market"}</td></tr>
                </table>
                <div class="result-success-msg">✓ Order ${d.orderId} — ${d.status}</div>
            `;
            log(`Order placed: #${d.orderId} ${d.status}`, "success");
            loadBalance();
            loadOpenOrders();
        } else {
            card.className = "card result-card error";
            title.textContent = "❌ Order Failed";
            content.innerHTML = `<div class="result-error">${res.error}</div>`;
            log(`Order failed: ${res.error}`, "error");
        }
    } catch (e) {
        log(`Network error: ${e.message}`, "error");
    } finally {
        btn.disabled = false;
        spinner.style.display = "none";
        txt.textContent = `Place ${currentSide} Order`;
    }
});

// ── Init ──
(async () => {
    await checkConnection();
    loadPrices();
    loadBalance();
    loadOpenOrders();
    setInterval(loadPrices, 10000);
})();
