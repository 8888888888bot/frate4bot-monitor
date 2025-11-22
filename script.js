// === БЕЛЫЙ СПИСОК ОФИЦИАЛЬНЫХ КОНТРАКТОВ ===
const OFFICIAL_TOKENS = {
  PEPE: {
    ethereum: "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    bsc: "0xb46584e0efde3092e04010a13f2eae62adb3b9f0",
    arbitrum: "0x25d887ce7a35172c62febfd67a1856f20faebb00"
  }
};

// === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
let lastPrice = null;
let priceHistory = JSON.parse(localStorage.getItem("priceHistory") || "[]");
let anomalyLog = JSON.parse(localStorage.getItem("anomalyLog") || "[]");

// === ФУНКЦИЯ ЗАПРОСА ДАННЫХ ===
async function fetchPepeData() {
  try {
    const res = await fetch("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=PEPE_USDT");
    const data = await res.json();
    const ticker = data.find(t => t.currency_pair === "PEPE_USDT");
    
    if (!ticker) return;

    const price = parseFloat(ticker.last);
    const change = parseFloat(ticker.percent_change);
    const baseVolume = parseFloat(ticker.base_volume); // USDT volume
    const quoteVolume = parseFloat(ticker.quote_volume); // PEPE volume

    // === Анализ на аномалии ===
    let alerts = [];

    // 1. Резкий рост цены
    if (change > 15) {
      alerts.push("🟥 Памп >15%: возможна накачка!");
    } else if (change < -15) {
      alerts.push("🟥 Дамп >15%: ликвидационный каскад?");
    }

    // 2. Отслеживание изменения от предыдущего значения (для внутридневной волатильности)
    if (lastPrice) {
      const diff = ((price - lastPrice) / lastPrice) * 100;
      if (Math.abs(diff) > 10 && Math.abs(change) < 5) {
        alerts.push("🟨 Аномальное движение: не совпадает с 24h-change");
      }
    }

    // 3. Низкий объём при росте
    if (change > 10 && baseVolume < 100000) {
      alerts.push("🟨 Низкий объём при росте — слабый памп");
    }

    // Обновляем lastPrice
    lastPrice = price;

    // === Обновление интерфейса ===
    document.getElementById("price").textContent = `Цена: $${price.toFixed(8)}`;
    document.getElementById("change").textContent = `Изменение за 24ч: ${change.toFixed(2)}%`;
    document.getElementById("volume").textContent = `Объём (USDT): ${baseVolume.toLocaleString()}`;
    
    const now = new Date().toLocaleTimeString();
    document.getElementById("last-update").textContent = `Обновлено: ${now}`;

    // === Алерт-панель ===
    const alertDiv = document.getElementById("alerts");
    if (alerts.length > 0) {
      alertDiv.innerHTML = alerts.map(a => `<div>${a}</div>`).join("");
      alertDiv.style.display = "block";
      
      // Сохраняем в лог аномалий
      const anomaly = {
        time: new Date().toISOString(),
        price: price,
        change: change,
        alerts: alerts
      };
      anomalyLog.unshift(anomaly);
      if (anomalyLog.length > 20) anomalyLog = anomalyLog.slice(0, 20);
      localStorage.setItem("anomalyLog", JSON.stringify(anomalyLog));
      updateAnomalyLog();
    } else {
      alertDiv.style.display = "none";
    }

    // === История цен ===
    priceHistory.unshift({ price, change, volume: baseVolume, time: new Date().toISOString() });
    if (priceHistory.length > 50) priceHistory = priceHistory.slice(0, 50);
    localStorage.setItem("priceHistory", JSON.stringify(priceHistory));
    updateHistoryDisplay();

  } catch (e) {
    console.error("Ошибка загрузки:", e);
    document.getElementById("price").textContent = "Ошибка загрузки";
  }
}

// === Валидация контракта ===
function validateToken() {
  const network = document.getElementById("network-select").value;
  const input = document.getElementById("contract-input").value.trim().toLowerCase();
  const resultDiv = document.getElementById("validation-result");

  if (!input || !input.startsWith("0x") || input.length !== 42) {
    resultDiv.innerHTML = "❌ Неверный формат адреса";
    resultDiv.className = "result-fake";
    return;
  }

  const official = OFFICIAL_TOKENS.PEPE[network];
  if (official && input === official.toLowerCase()) {
    resultDiv.innerHTML = "✅ Официальный контракт PEPE";
    resultDiv.className = "result-official";
  } else {
    resultDiv.innerHTML = "⚠️ Подозрение на фейк или неподтверждённую сеть";
    resultDiv.className = "result-fake";
  }
}

// === Обновление истории цен ===
function updateHistoryDisplay() {
  const div = document.getElementById("history");
  if (priceHistory.length === 0) {
    div.innerHTML = "<em>История пуста</em>";
    return;
  }
  div.innerHTML = priceHistory.slice(0, 10).map(h => {
    const time = new Date(h.time).toLocaleTimeString();
    return `<div>${time} — $${h.price.toFixed(8)} (${h.change.toFixed(2)}%)</div>`;
  }).join("");
}

// === Обновление лога аномалий ===
function updateAnomalyLog() {
  const div = document.getElementById("anomaly-log");
  if (anomalyLog.length === 0) {
    div.innerHTML = "<em>Аномалий не обнаружено</em>";
    return;
  }
  div.innerHTML = anomalyLog.slice(0, 5).map(a => {
    const time = new Date(a.time).toLocaleTimeString();
    return `<div><strong>${time}</strong> — ${a.alerts.join("; ")}</div>`;
  }).join("");
}

// === ИНИЦИАЛИЗАЦИЯ ===
fetchPepeData();
setInterval(fetchPepeData, 60000); // каждую минуту

// Восстановление данных
updateHistoryDisplay();
updateAnomalyLog();
