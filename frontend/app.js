const POLL_INTERVAL_MS = 30000;
const statusEl = document.getElementById("status");
const containerEl = document.getElementById("signals-container");

async function checkStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.connected) {
      statusEl.textContent = `Connected · account ${data.account ?? "?"} · ${data.server ?? ""}`;
      statusEl.className = "status ok";
    } else {
      statusEl.textContent = `Not connected: ${data.error}`;
      statusEl.className = "status error";
    }
  } catch (e) {
    statusEl.textContent = "Backend unreachable";
    statusEl.className = "status error";
  }
}

function renderSignals(results) {
  containerEl.innerHTML = "";
  const symbols = Object.keys(results);

  if (symbols.length === 0) {
    containerEl.innerHTML = '<p class="empty">No signals yet. Keep watching.</p>';
    return;
  }

  for (const symbol of symbols) {
    const block = document.createElement("div");
    block.className = "symbol-block";

    const heading = document.createElement("h2");
    heading.textContent = symbol;
    block.appendChild(heading);

    const signals = results[symbol].signals || [];

    if (signals.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No active setups.";
      block.appendChild(empty);
    } else {
      for (const sig of signals) {
        const card = document.createElement("div");
        card.className = `signal-card ${sig.direction}`;
        card.innerHTML = `
          <div class="direction">${sig.direction} ${sig.symbol} (${sig.timeframe})</div>
          <div class="prices">
            <span>Entry <strong>${sig.entry}</strong></span>
            <span>SL <strong>${sig.stop_loss}</strong></span>
            <span>TP <strong>${sig.take_profit}</strong></span>
          </div>
          <div class="reason">${sig.reason}</div>
          <div class="time">Confirmed ${sig.confirmation_time}</div>
        `;
        block.appendChild(card);
      }
    }

    containerEl.appendChild(block);
  }
}

async function fetchSignals() {
  try {
    const res = await fetch("/api/signals");
    const data = await res.json();
    renderSignals(data.results || {});
  } catch (e) {
    containerEl.innerHTML = '<p class="empty">Could not load signals.</p>';
  }
}

async function tick() {
  await checkStatus();
  await fetchSignals();
}

tick();
setInterval(tick, POLL_INTERVAL_MS);
