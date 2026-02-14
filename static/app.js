// ── Config ──────────────────────────────────────────────────────
const API = window.location.origin;

// ── Helpers ─────────────────────────────────────────────────────
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

async function api(path, opts = {}) {
  const resp = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || resp.statusText);
  }
  return resp.json();
}

function renderMd(text) {
  return marked.parse(text || "", { breaks: true });
}

function pnlColor(val) {
  if (val > 0) return "text-green-400";
  if (val < 0) return "text-red-400";
  return "text-gray-400";
}

function pnlSign(val) {
  if (val > 0) return `+${val.toFixed(2)}`;
  return val.toFixed(2);
}

function badgeFor(changePct) {
  if (changePct === null || changePct === undefined) return '<span class="badge badge-blue">N/A</span>';
  if (changePct > 0) return `<span class="badge badge-green">+${changePct.toFixed(2)}%</span>`;
  if (changePct < 0) return `<span class="badge badge-red">${changePct.toFixed(2)}%</span>`;
  return `<span class="badge badge-yellow">0.00%</span>`;
}

function toast(msg, isError = false) {
  const el = document.createElement("div");
  el.className = `fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg text-sm font-medium fade-in ${
    isError ? "bg-red-600/90 text-white" : "bg-green-600/90 text-white"
  }`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function getSymbolInput() {
  const val = $("#symbol-input").value.trim().toUpperCase();
  if (!val) { toast("Enter a symbol first", true); return null; }
  return val;
}


// ── Tabs ────────────────────────────────────────────────────────
$$(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".tab-btn").forEach((b) => b.classList.remove("tab-active"));
    btn.classList.add("tab-active");
    $$(".tab-panel").forEach((p) => p.classList.add("hidden"));
    $(`#tab-${btn.dataset.tab}`).classList.remove("hidden");
  });
});


// ── Health ──────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const h = await api("/health");
    const dot = h.status === "ok"
      ? '<span class="inline-block w-2.5 h-2.5 rounded-full bg-green-500 pulse-dot"></span>'
      : '<span class="inline-block w-2.5 h-2.5 rounded-full bg-yellow-500"></span>';
    $("#health-badge").innerHTML = `${dot} <span class="text-gray-400">${h.provider}/${h.model}</span>`;
  } catch {
    $("#health-badge").innerHTML = '<span class="inline-block w-2.5 h-2.5 rounded-full bg-red-500"></span> <span class="text-red-400">Disconnected</span>';
  }
}


// ── Watchlist ───────────────────────────────────────────────────
async function loadWatchlist() {
  try {
    const data = await api("/watchlist");
    const symbols = data.symbols || [];
    if (symbols.length === 0) {
      $("#watchlist-grid").innerHTML = '<div class="text-gray-500 text-sm col-span-full text-center py-8">Watchlist is empty. Add a symbol above.</div>';
      return;
    }
    // Fetch quotes in parallel
    const quotes = await Promise.allSettled(symbols.map((s) => api(`/quote/${s}`)));
    let html = "";
    quotes.forEach((q, i) => {
      if (q.status === "fulfilled") {
        const d = q.value;
        html += watchlistCard(d, symbols[i]);
      } else {
        html += watchlistCard(null, symbols[i]);
      }
    });
    $("#watchlist-grid").innerHTML = html;
  } catch (e) {
    $("#watchlist-grid").innerHTML = `<div class="text-red-400 text-sm col-span-full text-center py-8">${e.message}</div>`;
  }
}

function watchlistCard(d, symbol) {
  if (!d) {
    return `<div class="bg-surface-700 rounded-lg p-4">
      <div class="flex justify-between items-start">
        <span class="text-white font-semibold">${symbol}</span>
        <button onclick="removeWatchlist('${symbol}')" class="text-gray-600 hover:text-red-400 text-xs">Remove</button>
      </div>
      <p class="text-gray-500 text-sm mt-2">Failed to load</p>
    </div>`;
  }
  const price = d.price !== null ? `$${d.price.toFixed(2)}` : "N/A";
  return `<div class="bg-surface-700 rounded-lg p-4 hover:bg-surface-600 transition cursor-pointer" onclick="analyzeFromCard('${d.symbol}')">
    <div class="flex justify-between items-start">
      <div>
        <span class="text-white font-semibold">${d.symbol}</span>
        ${badgeFor(d.change_pct)}
      </div>
      <button onclick="event.stopPropagation();removeWatchlist('${d.symbol}')" class="text-gray-600 hover:text-red-400 text-xs">Remove</button>
    </div>
    <p class="text-white text-xl font-bold mt-2">${price}</p>
    <p class="text-gray-500 text-xs mt-1 truncate">${d.signal_summary || "No signals"}</p>
  </div>`;
}

async function addWatchlist() {
  const sym = $("#watchlist-add-input").value.trim().toUpperCase();
  if (!sym) return;
  try {
    await api("/watchlist", { method: "POST", body: JSON.stringify({ symbol: sym }) });
    $("#watchlist-add-input").value = "";
    toast(`${sym} added to watchlist`);
    loadWatchlist();
  } catch (e) { toast(e.message, true); }
}

async function removeWatchlist(symbol) {
  try {
    await api(`/watchlist/${symbol}`, { method: "DELETE" });
    toast(`${symbol} removed`);
    loadWatchlist();
  } catch (e) { toast(e.message, true); }
}


// ── Quick Quote ─────────────────────────────────────────────────
async function doQuote() {
  const sym = getSymbolInput();
  if (!sym) return;
  $("#quote-result").classList.remove("hidden");
  $("#quote-body").innerHTML = '<div class="spinner"></div>';
  try {
    const d = await api(`/quote/${sym}`);
    const price = d.price !== null ? `$${d.price.toFixed(2)}` : "N/A";
    let techRows = "";
    if (d.technicals) {
      Object.entries(d.technicals).forEach(([k, v]) => {
        if (v !== null) techRows += `<tr><td class="pr-4 text-gray-500">${k}</td><td class="text-white">${typeof v === "number" ? v.toFixed(2) : v}</td></tr>`;
      });
    }
    let newsHtml = "";
    if (d.news && d.news.length) {
      newsHtml = d.news.slice(0, 5).map((n) =>
        `<a href="${n.link}" target="_blank" class="block hover:bg-white/5 rounded px-2 py-1.5 transition">
          <span class="text-gray-300 text-sm">${n.title}</span>
          <span class="text-gray-600 text-xs ml-2">${n.publisher}</span>
        </a>`
      ).join("");
    } else {
      newsHtml = '<p class="text-gray-500 text-sm">No recent news</p>';
    }

    $("#quote-body").innerHTML = `
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div>
          <p class="text-xs text-gray-500 uppercase">${d.symbol}</p>
          <p class="text-3xl font-bold text-white mt-1">${price}</p>
          <p class="mt-1">${badgeFor(d.change_pct)}</p>
          <p class="text-gray-500 text-xs mt-2">${d.signal_summary || ""}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase mb-2">Technicals</p>
          <table class="text-xs w-full">${techRows}</table>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase mb-2">News</p>
          <div class="space-y-0.5 max-h-48 overflow-y-auto">${newsHtml}</div>
        </div>
      </div>`;
  } catch (e) {
    $("#quote-body").innerHTML = `<p class="text-red-400">${e.message}</p>`;
  }
}


// ── Analysis ────────────────────────────────────────────────────
async function doAnalyze() {
  const sym = getSymbolInput();
  if (!sym) return;
  // Switch to analysis tab
  $$(".tab-btn").forEach((b) => b.classList.remove("tab-active"));
  document.querySelector('[data-tab="analysis"]').classList.add("tab-active");
  $$(".tab-panel").forEach((p) => p.classList.add("hidden"));
  $("#tab-analysis").classList.remove("hidden");

  $("#analysis-placeholder").classList.add("hidden");
  $("#analysis-result").classList.add("hidden");
  $("#analysis-loading").classList.remove("hidden");

  try {
    const d = await api(`/analyze/${sym}`);
    const price = d.price !== null ? `$${d.price.toFixed(2)}` : "N/A";

    let techHtml = "";
    if (d.technicals) {
      techHtml = Object.entries(d.technicals)
        .filter(([, v]) => v !== null)
        .map(([k, v]) => `<div class="bg-surface-700 rounded-lg p-3"><p class="text-xs text-gray-500">${k}</p><p class="text-white font-mono">${typeof v === "number" ? v.toFixed(2) : v}</p></div>`)
        .join("");
    }

    // Extract recommendation badge
    let recBadge = "";
    const rec = (d.ai_recommendation || "").toUpperCase();
    if (rec.includes("BUY")) recBadge = '<span class="badge badge-green text-sm">BUY</span>';
    else if (rec.includes("SELL")) recBadge = '<span class="badge badge-red text-sm">SELL</span>';
    else if (rec.includes("HOLD")) recBadge = '<span class="badge badge-yellow text-sm">HOLD</span>';

    $("#analysis-data").innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <div>
          <span class="text-white text-xl font-bold">${d.symbol}</span>
          <span class="text-2xl font-bold text-white ml-3">${price}</span>
          <span class="ml-2">${badgeFor(d.change_pct)}</span>
        </div>
        ${recBadge}
      </div>
      <p class="text-gray-500 text-sm mb-3">${d.signal_summary || ""}</p>
      <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">${techHtml}</div>`;

    $("#analysis-ai").innerHTML = renderMd(d.ai_analysis);
    $("#analysis-loading").classList.add("hidden");
    $("#analysis-result").classList.remove("hidden");
  } catch (e) {
    $("#analysis-loading").classList.add("hidden");
    $("#analysis-placeholder").classList.remove("hidden");
    toast(e.message, true);
  }
}

function analyzeFromCard(symbol) {
  $("#symbol-input").value = symbol;
  doAnalyze();
}


// ── Portfolio ───────────────────────────────────────────────────
async function loadPortfolio() {
  $("#pf-loading").classList.remove("hidden");
  $("#pf-ai-box").classList.add("hidden");
  try {
    const d = await api("/portfolio");
    if (!d.holdings || d.holdings.length === 0) {
      $("#pf-table-body").innerHTML = '<tr><td colspan="8" class="text-center text-gray-500 py-8">No holdings yet. Add one above.</td></tr>';
      $("#pf-totals").textContent = "";
    } else {
      let rows = "";
      d.holdings.forEach((h) => {
        rows += `<tr class="border-b border-white/5">
          <td class="py-2 pr-4 text-white font-medium">${h.symbol}</td>
          <td class="py-2 pr-4">${h.shares}</td>
          <td class="py-2 pr-4">$${h.avg_cost.toFixed(2)}</td>
          <td class="py-2 pr-4 text-white">$${h.current_price.toFixed(2)}</td>
          <td class="py-2 pr-4 text-white">$${h.value.toFixed(2)}</td>
          <td class="py-2 pr-4 ${pnlColor(h.daily_pnl)}">${pnlSign(h.daily_pnl)}</td>
          <td class="py-2 pr-4 ${pnlColor(h.unrealized_pnl)}">${pnlSign(h.unrealized_pnl)}</td>
          <td class="py-2"><button onclick="removeHolding('${h.symbol}')" class="text-gray-600 hover:text-red-400 text-xs">Remove</button></td>
        </tr>`;
      });
      $("#pf-table-body").innerHTML = rows;
      $("#pf-totals").innerHTML = `Total: <span class="text-white">$${d.total_value.toFixed(2)}</span> &nbsp; P&L: <span class="${pnlColor(d.daily_pnl)}">${pnlSign(d.daily_pnl)}</span>`;
    }
    if (d.ai_summary && d.ai_summary !== "Portfolio is empty. Add holdings with POST /portfolio.") {
      $("#pf-ai-summary").innerHTML = renderMd(d.ai_summary);
      $("#pf-ai-box").classList.remove("hidden");
    }
  } catch (e) {
    toast(e.message, true);
  }
  $("#pf-loading").classList.add("hidden");
}

async function addHolding() {
  const sym = $("#pf-symbol").value.trim().toUpperCase();
  const shares = parseFloat($("#pf-shares").value);
  const cost = parseFloat($("#pf-cost").value);
  if (!sym || !shares || !cost) { toast("Fill all fields", true); return; }
  try {
    await api("/portfolio", { method: "POST", body: JSON.stringify({ symbol: sym, shares, avg_cost: cost }) });
    $("#pf-symbol").value = "";
    $("#pf-shares").value = "";
    $("#pf-cost").value = "";
    toast(`${sym} added to portfolio`);
    loadPortfolio();
  } catch (e) { toast(e.message, true); }
}

async function removeHolding(symbol) {
  try {
    await api(`/portfolio/${symbol}`, { method: "DELETE" });
    toast(`${symbol} removed`);
    loadPortfolio();
  } catch (e) { toast(e.message, true); }
}


// ── Alerts ──────────────────────────────────────────────────────
async function loadAlerts() {
  try {
    const d = await api("/alerts");
    const alerts = d.alerts || [];
    if (alerts.length === 0) {
      $("#alerts-list").innerHTML = '<p class="text-gray-500 text-sm text-center py-4">No active alerts. Create one above.</p>';
      return;
    }
    let html = "";
    alerts.forEach((a) => {
      const icon = a.condition === "above" ? "&#8593;" : "&#8595;";
      const color = a.condition === "above" ? "text-green-400" : "text-red-400";
      html += `<div class="flex items-center justify-between bg-surface-700 rounded-lg px-4 py-3">
        <div>
          <span class="text-white font-medium">${a.symbol}</span>
          <span class="${color} ml-2">${icon} ${a.condition} $${a.price.toFixed(2)}</span>
        </div>
        <span class="badge ${a.active ? "badge-green" : "badge-red"}">${a.active ? "Active" : "Triggered"}</span>
      </div>`;
    });
    $("#alerts-list").innerHTML = html;
  } catch (e) {
    $("#alerts-list").innerHTML = `<p class="text-red-400 text-sm text-center py-4">${e.message}</p>`;
  }
}

async function createAlert() {
  const sym = $("#alert-symbol").value.trim().toUpperCase();
  const condition = $("#alert-condition").value;
  const price = parseFloat($("#alert-price").value);
  if (!sym || !price) { toast("Fill symbol and price", true); return; }
  try {
    await api("/alerts", { method: "POST", body: JSON.stringify({ symbol: sym, condition, price }) });
    $("#alert-symbol").value = "";
    $("#alert-price").value = "";
    toast(`Alert created: ${sym} ${condition} $${price}`);
    loadAlerts();
  } catch (e) { toast(e.message, true); }
}

async function checkAlerts() {
  try {
    const d = await api("/check-alerts", { method: "POST" });
    let html = `<p class="text-gray-300 text-sm">${d.message}</p>`;
    if (d.triggered && d.triggered.length) {
      html += '<div class="mt-3 space-y-2">';
      d.triggered.forEach((t) => {
        html += `<div class="bg-yellow-600/10 border border-yellow-500/20 rounded-lg px-4 py-3">
          <span class="text-white font-medium">${t.symbol}</span>
          <span class="text-yellow-400 ml-2">${t.condition} $${t.target_price} — now $${t.current_price}</span>
        </div>`;
      });
      html += "</div>";
    }
    $("#alert-check-result").classList.remove("hidden");
    $("#alert-check-body").innerHTML = html;
    loadAlerts();
  } catch (e) { toast(e.message, true); }
}


// ── Briefing ────────────────────────────────────────────────────
async function runBriefing() {
  $("#briefing-placeholder").classList.add("hidden");
  $("#briefing-result").classList.add("hidden");
  $("#briefing-loading").classList.remove("hidden");
  $("#briefing-btn").disabled = true;

  try {
    const d = await api("/briefing", { method: "POST" });
    // Data cards
    let cards = "";
    if (d.watchlist_data) {
      d.watchlist_data.forEach((s) => {
        const price = s.price !== null ? `$${s.price.toFixed(2)}` : "N/A";
        cards += `<div class="bg-surface-700 rounded-lg p-4">
          <div class="flex justify-between items-center">
            <span class="text-white font-semibold">${s.symbol}</span>
            ${badgeFor(s.change_pct)}
          </div>
          <p class="text-white text-xl font-bold mt-2">${price}</p>
          <p class="text-gray-500 text-xs mt-1">${s.signal_summary || ""}</p>
        </div>`;
      });
    }
    $("#briefing-cards").innerHTML = cards;
    $("#briefing-ai").innerHTML = renderMd(d.ai_summary);
    $("#briefing-loading").classList.add("hidden");
    $("#briefing-result").classList.remove("hidden");
  } catch (e) {
    $("#briefing-loading").classList.add("hidden");
    $("#briefing-placeholder").classList.remove("hidden");
    toast(e.message, true);
  }
  $("#briefing-btn").disabled = false;
}


// ── Keyboard shortcut ───────────────────────────────────────────
$("#symbol-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    if (e.shiftKey) doAnalyze();
    else doQuote();
  }
});

$("#watchlist-add-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") addWatchlist();
});


// ── Init ────────────────────────────────────────────────────────
checkHealth();
loadWatchlist();
loadAlerts();

// Refresh health every 30s
setInterval(checkHealth, 30000);
