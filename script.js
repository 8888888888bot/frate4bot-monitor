// === Настройки ===
const PEPE_OFFICIAL = {
  ethereum: "0x6982508145454ce325ddbe47a25d4ec3d2311933",
  bsc: "0xb46584e0efde3092e04010a13f2eae62adb3b9f0",
  arbitrum: "0x25d887ce7a35172c62febfd67a1856f20faebb00"
};

let priceHistory = JSON.parse(localStorage.getItem("priceHistory") || "[]");

// === Функция обновления цены ===
async function fetchPrice() {
  try {
    const res = await fetch("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=PEPE_USDT");
    const data = await res.json();
    const ticker = data.find(t => t.currency_pair === "PEPE_USDT");
    if (ticker) {
      const price = parseFloat(ticker.last).toFixed(8);
      const change = parseFloat(ticker.percent_change).toFixed(2);
      const now = new Date().toLocaleTimeString();

      document.getElementById("price").textContent = `Цена: $${price}`;
      document.getElementById("change").textContent = `Изменение: ${change}%`;
      document.getElementById("last-update").textContent = `Обновлено: ${now}`;

      // Сохраняем в историю
      priceHistory.unshift({ price, change, time: new Date().toISOString() });
      if (priceHistory.length > 20) priceHistory = priceHistory.slice(0, 20);
      localStorage.setItem("priceHistory", JSON.stringify(priceHistory));
      updateHistoryDisplay();
    }
  } catch (e) {
    document.getElementById("price").textContent = "Ошибка загрузки";
  }
}

// === Валидация токена ===
function validateToken() {
  const network = document.getElementById("network-select").value;
  const input = document.getElementById("contract-input").value.trim().toLowerCase();
  const resultDiv = document.getElementById("validation-result");

  if (!input.startsWith("0x") || input.length !== 42) {
    resultDiv.innerHTML = "❌ Неверный формат адреса";
    resultDiv.style.backgroundColor = "#ffebee";
    return;
  }

  const official = PEPE_OFFICIAL[network];
  if (official && input === official.toLowerCase()) {
    resultDiv.innerHTML = "✅ <strong>Подтверждён</strong>: официальный контракт PEPE";
    resultDiv.style.backgroundColor = "#e8f5e9";
  } else {
    resultDiv.innerHTML = "⚠️ <strong>Подозрение на фейк</strong>: не совпадает с официальным";
    resultDiv.style.backgroundColor = "#fff3e0";
  }
}

// === Обновление истории ===
function updateHistoryDisplay() {
  const div = document.getElementById("history");
  if (priceHistory.length === 0) {
    div.innerHTML = "<em>История пуста</em>";
    return;
  }
  div.innerHTML = priceHistory.map(h => {
    const time = new Date(h.time).toLocaleTimeString();
    return `<div>${time} — $${h.price} (${h.change}%)</div>`;
  }).join("");
}

// === Запуск ===
fetchPrice();
setInterval(fetchPrice, 90000); // каждые 90 сек
updateHistoryDisplay();
