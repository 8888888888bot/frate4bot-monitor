// Конфигурация
let config = {
  pairs: ['BTC_USDT', 'ETH_USDT', 'SOL_USDT'],
  criticalLong: -0.001,
  criticalShort: 0.001,
  intervalSec: 90,
  history: {}
};

// DOM элементы
const statusEl = document.getElementById('status');
const pairsEl = document.getElementById('pairs');
const intervalSelect = document.getElementById('interval');
const intervalDisplay = document.getElementById('interval-display');
const longVal = document.getElementById('longVal');
const shortVal = document.getElementById('shortVal');
const newPairInput = document.getElementById('newPair');
const addPairBtn = document.getElementById('addPair');
const exportBtn = document.getElementById('exportBtn');

// Инициализация
function init() {
  loadConfig();
  renderUI();
  fetchData();
  setupEventListeners();
  startAutoRefresh();
  
  // Регистрация PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(console.warn);
  }
}

// Загрузка конфигурации
function loadConfig() {
  const saved = localStorage.getItem('frate4bot_config');
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      config = { ...config, ...parsed };
    } catch (e) {
      console.warn('Ошибка загрузки конфига', e);
    }
  }
  updateThresholdText();
  intervalSelect.value = config.intervalSec;
  intervalDisplay.textContent = config.intervalSec;
}

// Сохранение конфигурации
function saveConfig() {
  localStorage.setItem('frate4bot_config', JSON.stringify(config));
}

// Обработчики событий
function setupEventListeners() {
  // Интервал обновления
  intervalSelect.addEventListener('change', () => {
    config.intervalSec = Number(intervalSelect.value);
    intervalDisplay.textContent = config.intervalSec;
    saveConfig();
    resetAutoRefresh();
  });

  // Пороги
  document.getElementById('longPlus').addEventListener('click', () => { 
    config.criticalLong = Math.round((config.criticalLong + 0.0001) * 100000) / 100000;
    updateThresholdText(); 
    saveConfig(); 
  });
  document.getElementById('longMinus').addEventListener('click', () => { 
    config.criticalLong = Math.round((config.criticalLong - 0.0001) * 100000) / 100000;
    updateThresholdText(); 
    saveConfig(); 
  });
  document.getElementById('shortPlus').addEventListener('click', () => { 
    config.criticalShort = Math.round((config.criticalShort + 0.0001) * 100000) / 100000;
    updateThresholdText(); 
    saveConfig(); 
  });
  document.getElementById('shortMinus').addEventListener('click', () => { 
    config.criticalShort = Math.round((config.criticalShort - 0.0001) * 100000) / 100000;
    updateThresholdText(); 
    saveConfig(); 
  });

  // Управление парами
  addPairBtn.addEventListener('click', addNewPair);
  newPairInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addNewPair();
  });

  // Экспорт в CSV
  exportBtn.addEventListener('click', exportToCSV);

  // Кнопка обновления
  document.getElementById('refreshBtn')?.addEventListener('click', fetchData);
}

function updateThresholdText() {
  longVal.textContent = config.criticalLong.toFixed(5);
  shortVal.textContent = (config.criticalShort >= 0 ? '+' : '') + config.criticalShort.toFixed(5);
}

// Добавление новой пары
function addNewPair() {
  const pair = newPairInput.value.trim().toUpperCase();
  if (!pair || config.pairs.includes(pair)) {
    newPairInput.value = '';
    return;
  }
  if (!/^[A-Z0-9_]+$/.test(pair)) {
    alert('Неверный формат пары (пример: BTC_USDT)');
    return;
  }
  config.pairs.push(pair);
  newPairInput.value = '';
  saveConfig();
  fetchData();
}

// Удаление пары
function removePair(pair) {
  config.pairs = config.pairs.filter(p => p !== pair);
  delete config.history[pair];
  saveConfig();
  fetchData();
}

// Автообновление
let refreshTimer = null;
function startAutoRefresh() {
  refreshTimer = setInterval(fetchData, config.intervalSec * 1000);
}
function resetAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  startAutoRefresh();
}

// Запрос данных
async function fetchData() {
  statusEl.textContent = 'Загрузка данных с Gate.io…';
  statusEl.style.color = '#bbb';
  
  try {
    // Добавляем кэш-бустер для обхода CORS (необязательно, но надежнее)
    const res = await fetch('https://api.gateio.ws/api/v4/futures/usdt/tickers?' + Date.now());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    const data = await res.json();
    const map = {};
    
    for (const item of data) {
      if (config.pairs.includes(item.contract)) {
        map[item.contract] = item;
      }
    }
    
    renderData(map);
    statusEl.textContent = `Актуально • ${new Date().toLocaleTimeString()}`;
    statusEl.style.color = '#99cc00';
  } catch (e) {
    console.error('Ошибка загрузки:', e);
    statusEl.innerHTML = `❌ Ошибка: ${e.message || 'Неизвестная ошибка'}`;
    statusEl.style.color = '#ff4444';
  }
}

// Управление историей и трендом
function updateHistory(pair, fr) {
  if (!config.history[pair]) config.history[pair] = [];
  config.history[pair].push(fr);
  if (config.history[pair].length > 12) config.history[pair].shift();
}

function getTrend(pair) {
  const hist = config.history[pair] || [];
  if (hist.length < 3) return 'недостаточно данных';
  
  const last3 = hist.slice(-3);
  const diffs = [last3[1] - last3[0], last3[2] - last3[1]];
  
  if (diffs[0] > 0 && diffs[1] > 0) return '📈 растёт';
  if (diffs[0] < 0 && diffs[1] < 0) return '📉 падает';
  return '↔️ стабильно';
}

// Рендер данных
function renderData(data) {
  pairsEl.innerHTML = '';
  
  for (const pair of config.pairs) {
    const item = data[pair];
    if (!item) {
      renderPairCard(pair, null, 'Пара не найдена');
      continue;
    }
    
    const fr = parseFloat(item.funding_rate);
    updateHistory(pair, fr);
    const trend = getTrend(pair);
    
    // Определение цвета и эмодзи
    let emoji, label, color;
    if (fr <= config.criticalLong) {
      emoji = '🔻'; label = 'СИЛЬНЫЙ LONG (риск)'; color = 'red';
    } else if (fr < 0) {
      emoji = '⬇️'; label = 'СЛАБЫЙ LONG'; color = 'yellow';
    } else if (fr >= config.criticalShort) {
      emoji = '🔺'; label = 'СИЛЬНЫЙ SHORT (риск)'; color = 'blue';
    } else if (fr > 0) {
      emoji = '⬆️'; label = 'СЛАБЫЙ SHORT'; color = 'green';
    } else {
      emoji = '➖'; label = 'НЕЙТРАЛЬНО'; color = 'gray';
    }
    
    renderPairCard(pair, { fr, trend, emoji, label, color });
  }
}

function renderPairCard(pair, data, error) {
  const div = document.createElement('div');
  div.className = 'pair';
  
  if (error) {
    div.innerHTML = `
      <div class="pair-name">
        <span>${pair}</span>
        <button class="remove-pair" data-pair="${pair}">×</button>
      </div>
      <div class="rate" style="color: #ff4444;">${error}</div>
    `;
  } else {
    div.innerHTML = `
      <div class="pair-name">
        <span>${pair}</span>
        <button class="remove-pair" data-pair="${pair}">×</button>
      </div>
      <div class="rate">Ставка: <strong>${data.fr.toFixed(6)}</strong></div>
      <div class="trend">Тренд: ${data.trend}</div>
      <div class="label" style="color: var(--${data.color})">${data.emoji} ${data.label}</div>
    `;
  }
  
  // Добавляем обработчик удаления
  div.querySelector('.remove-pair').addEventListener('click', () => {
    removePair(pair);
  });
  
  pairsEl.appendChild(div);
}

// Экспорт в CSV
function exportToCSV() {
  let csv = 'Пара,Ставка,Тренд,Время\n';
  const now = new Date().toISOString();
  
  for (const pair of config.pairs) {
    const hist = config.history[pair] || [];
    if (hist.length === 0) continue;
    
    const lastFr = hist[hist.length - 1];
    const trend = getTrend(pair);
    csv += `"${pair}",${lastFr},"${trend}","${now}"\n`;
  }
  
  // Создаем и скачиваем файл
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `frate4bot_${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', init);
