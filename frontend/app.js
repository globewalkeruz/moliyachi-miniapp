/* ═══════════════════════════════════════════════════════════
   MOLIYACHI — Frontend Application
   Telegram Mini App for personal finance management
═══════════════════════════════════════════════════════════ */

// ── Constants ────────────────────────────────────────────
const BASE_URL = window.location.origin;

const CATEGORIES = {
  expense: [
    { id: 'Oziq-ovqat',   emoji: '🛒', color: '#FF6B6B' },
    { id: 'Transport',    emoji: '🚌', color: '#4ECDC4' },
    { id: 'Kommunal',     emoji: '💡', color: '#FFB347' },
    { id: 'Kiyim',        emoji: '👕', color: '#98D8C8' },
    { id: "Sog'liq",      emoji: '💊', color: '#FF8FAB' },
    { id: "Ta'lim",       emoji: '📚', color: '#87CEEB' },
    { id: "Ko'ngilochar", emoji: '🎮', color: '#DDA0DD' },
    { id: 'Boshqa',       emoji: '💼', color: '#B0C4DE' },
  ],
  income: [
    { id: 'Maosh',        emoji: '💰', color: '#00C853' },
    { id: 'Freelance',    emoji: '💻', color: '#00BCD4' },
    { id: 'Biznes',       emoji: '🏪', color: '#FF9800' },
    { id: 'Investitsiya', emoji: '📈', color: '#9C27B0' },
    { id: 'Boshqa',       emoji: '💵', color: '#607D8B' },
  ],
};

const CHART_COLORS = [
  '#5C67F2','#8B5CF6','#FF6B6B','#4ECDC4',
  '#FFB347','#98D8C8','#FF8FAB','#87CEEB',
  '#DDA0DD','#00C853','#FF9800','#00BCD4',
];

const FLAG_MAP = { USD: '🇺🇸', EUR: '🇪🇺', RUB: '🇷🇺', CNY: '🇨🇳', GBP: '🇬🇧' };

// ── App State ─────────────────────────────────────────────
const state = {
  userId: 12345,         // fallback; replaced by Telegram user id
  currentSection: 'home',
  selectedExpenseCat: null,
  selectedIncomeCat: null,
  charts: { expense: null, income: null },
};

// ── Telegram WebApp init ──────────────────────────────────
const tg = window.Telegram?.WebApp;

function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();

  // Force dark native chrome so our gradient shows correctly
  try { tg.setBackgroundColor('#0f0c29'); } catch (_) {}
  try { tg.setHeaderColor('#0f0c29'); }    catch (_) {}

  const user = tg.initDataUnsafe?.user;
  if (user?.id) state.userId = user.id;
}

function haptic(type = 'light') {
  tg?.HapticFeedback?.impactOccurred?.(type);
}

// ── Utilities ─────────────────────────────────────────────
function fmt(amount) {
  return Math.round(Math.abs(amount)).toLocaleString('ru-RU');
}

function updateBalanceDOM(balance, income, expense) {
  const balEl = document.getElementById('balance-amount');
  const incEl = document.getElementById('home-income');
  const expEl = document.getElementById('home-expense');
  if (balEl) {
    const neg = balance < 0;
    balEl.innerHTML = `${neg ? '−' : ''}${fmt(balance)} <span>so'm</span>`;
    balEl.style.opacity = neg ? '0.85' : '1';
  }
  if (incEl) incEl.textContent = `+${fmt(income)} so'm`;
  if (expEl) expEl.textContent = `-${fmt(expense)} so'm`;
}

function showToast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast${type ? ' ' + type : ''} show`;
  setTimeout(() => { el.className = 'toast'; }, 2500);
}

// ── Navigation ────────────────────────────────────────────
function navigateTo(section) {
  haptic('light');

  // Hide current, show next
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById(section)?.classList.add('active');

  // Update nav buttons
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.section === section);
  });

  state.currentSection = section;

  // Load section data
  if (section === 'home')   loadHome();
  if (section === 'report') loadReport();
}

// ── API helpers ───────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(BASE_URL + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ══════════════════════════════════════════════════════════
// HOME PAGE
// ══════════════════════════════════════════════════════════
async function loadHome() {
  await Promise.all([loadBalance(), loadCurrency(), loadRecentTransactions()]);
}

async function loadBalance() {
  try {
    const data = await apiFetch(`/api/balance/${state.userId}`);
    state.cachedBalance = data.balance      ?? 0;
    state.cachedIncome  = data.total_income  ?? 0;
    state.cachedExpense = data.total_expense ?? 0;
    updateBalanceDOM(state.cachedBalance, state.cachedIncome, state.cachedExpense);
  } catch {
    document.getElementById('balance-amount').innerHTML = '0 <span>so\'m</span>';
  }
}

async function loadCurrency() {
  const list = document.getElementById('currency-list');
  try {
    const data = await apiFetch('/api/currency');
    const rates = data.rates ?? {};

    if (rates.error || Object.keys(rates).length === 0) {
      list.innerHTML = `<p style="color:var(--tg-hint);font-size:13px;">Kurs ma'lumotlari mavjud emas</p>`;
      return;
    }

    const order = ['USD', 'EUR', 'RUB', 'CNY', 'GBP'];
    const sorted = order.filter(c => rates[c]);

    list.innerHTML = sorted.map(ccy => {
      const r = rates[ccy];
      const diff = parseFloat(r.diff ?? 0);
      const diffClass = diff > 0 ? 'diff-up' : diff < 0 ? 'diff-down' : 'diff-zero';
      const diffSign  = diff > 0 ? '+' : '';
      const flag = FLAG_MAP[ccy] ?? '🏳️';
      return `
        <div class="currency-item">
          <div class="currency-flag-name">
            <span class="currency-flag">${flag}</span>
            <div>
              <p class="currency-code">${ccy}</p>
              <p class="currency-name">${r.name}</p>
            </div>
          </div>
          <div class="currency-right">
            <p class="currency-rate">${fmt(r.rate)} so'm</p>
            <p class="currency-diff ${diffClass}">${diffSign}${diff.toFixed(2)}</p>
          </div>
        </div>`;
    }).join('');
  } catch {
    list.innerHTML = `<p style="color:var(--tg-hint);font-size:13px;">Kurs yuklanmadi</p>`;
  }
}

async function loadRecentTransactions() {
  const container = document.getElementById('recent-transactions');
  try {
    const data = await apiFetch(`/api/transactions/${state.userId}?limit=5`);
    const txs = data.transactions ?? [];
    if (txs.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📋</span>
          <p>Hali tranzaksiyalar yo'q</p>
        </div>`;
      return;
    }
    container.innerHTML = txs.map(txHTML).join('');
  } catch {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">⚠️</span><p>Yuklanmadi</p></div>`;
  }
}

function txHTML(tx) {
  const cat = [...CATEGORIES.expense, ...CATEGORIES.income].find(c => c.id === tx.category);
  const emoji = cat?.emoji ?? (tx.type === 'income' ? '💵' : '💸');
  const sign  = tx.type === 'income' ? '+' : '-';
  const cls   = tx.type === 'income' ? 'income' : 'expense';
  const time  = tx.created_at ? tx.created_at.slice(11, 16) : '';
  const date  = tx.created_at ? tx.created_at.slice(0, 10) : '';
  return `
    <div class="tx-item">
      <div class="tx-emoji ${cls}-emoji">${emoji}</div>
      <div class="tx-info">
        <p class="tx-category">${tx.category}</p>
        <p class="tx-desc">${tx.description || (tx.type === 'income' ? 'Daromad' : 'Xarajat')}</p>
        <p class="tx-date">${date} ${time}</p>
      </div>
      <span class="tx-amount ${cls}-text">${sign}${fmt(tx.amount)} so'm</span>
    </div>`;
}

// Refresh button
document.getElementById('refresh-btn')?.addEventListener('click', () => {
  haptic('medium');
  loadHome();
});

// ══════════════════════════════════════════════════════════
// CATEGORY RENDERING
// ══════════════════════════════════════════════════════════
function renderCategories(type) {
  const cats = CATEGORIES[type];
  const gridId = `${type}-categories`;
  const grid = document.getElementById(gridId);
  if (!grid) return;

  grid.innerHTML = cats.map(c => `
    <button
      class="cat-btn"
      data-id="${c.id}"
      onclick="selectCategory('${type}', '${c.id}', this)"
    >
      <span class="cat-emoji">${c.emoji}</span>
      <span>${c.id}</span>
    </button>`
  ).join('');
}

function selectCategory(type, catId, btn) {
  haptic('light');
  const key = `selected${type.charAt(0).toUpperCase() + type.slice(1)}Cat`;
  state[key] = catId;

  const grid = document.getElementById(`${type}-categories`);
  grid.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
}

// ══════════════════════════════════════════════════════════
// SUBMIT TRANSACTION
// ══════════════════════════════════════════════════════════
async function submitTransaction(type) {
  haptic('medium');
  const amountInput = document.getElementById(`${type}-amount`);
  const descInput   = document.getElementById(`${type}-description`);
  const catKey      = `selected${type.charAt(0).toUpperCase() + type.slice(1)}Cat`;
  const category    = state[catKey];

  const amount = parseFloat(amountInput?.value);

  if (!amount || amount <= 0) {
    showToast("Iltimos, summa kiriting", 'error');
    haptic('error');
    return;
  }
  if (!category) {
    showToast("Iltimos, kategoriya tanlang", 'error');
    haptic('error');
    return;
  }

  const btn = document.querySelector(`.${type}-submit-btn`);
  btn.disabled = true;
  btn.textContent = 'Saqlanmoqda...';

  try {
    await apiFetch('/api/transaction', {
      method: 'POST',
      body: JSON.stringify({
        user_id: state.userId,
        amount,
        type,
        category,
        description: descInput?.value?.trim() || null,
      }),
    });

    haptic('success');
    const msg = type === 'income'
      ? "✅ Daromad muvaffaqiyatli qo'shildi!"
      : "✅ Xarajat muvaffaqiyatli qo'shildi!";
    showToast(msg, 'success');

    // Optimistic balance update — visible immediately, no wait for navigation
    const delta = type === 'income' ? amount : -amount;
    state.cachedBalance = (state.cachedBalance ?? 0) + delta;
    state.cachedIncome  = (state.cachedIncome  ?? 0) + (type === 'income'  ? amount : 0);
    state.cachedExpense = (state.cachedExpense ?? 0) + (type === 'expense' ? amount : 0);
    updateBalanceDOM(state.cachedBalance, state.cachedIncome, state.cachedExpense);

    // Reset form
    amountInput.value = '';
    if (descInput) descInput.value = '';
    state[catKey] = null;
    document.querySelectorAll(`#${type}-categories .cat-btn`).forEach(b => b.classList.remove('selected'));

    // Navigate home after brief delay (loadBalance will confirm with server)
    setTimeout(() => navigateTo('home'), 700);
  } catch (e) {
    haptic('error');
    showToast("Xato yuz berdi, qayta urinib ko'ring", 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = type === 'expense' ? '➖  Xarajat qo\'shish' : '➕  Daromad qo\'shish';
  }
}

// ══════════════════════════════════════════════════════════
// REPORT PAGE
// ══════════════════════════════════════════════════════════
async function loadReport() {
  try {
    const data = await apiFetch(`/api/report/${state.userId}`);
    renderReport(data);
  } catch {
    showToast("Hisobot yuklanmadi", 'error');
  }
}

function renderReport(data) {
  document.getElementById('report-month-badge').textContent = data.month_name ?? '';
  document.getElementById('report-income').textContent  = fmt(data.income_total ?? 0);
  document.getElementById('report-expense').textContent = fmt(data.expense_total ?? 0);

  const net = data.net ?? 0;
  const netEl = document.getElementById('report-net');
  const netCard = document.getElementById('rc-net-card');
  netEl.textContent = fmt(net);
  netCard.classList.toggle('positive', net >= 0);
  netCard.classList.toggle('negative', net < 0);

  renderPieChart('expense', data.expense_by_category ?? []);
  renderPieChart('income',  data.income_by_category ?? []);
  renderCategoryBreakdown(data);
}

function renderPieChart(type, items) {
  const blockId  = `${type}-chart-block`;
  const canvasId = `${type}-chart`;
  const block    = document.getElementById(blockId);

  if (!items.length) { block.style.display = 'none'; return; }
  block.style.display = '';

  const labels = items.map(i => i.category);
  const values = items.map(i => i.total);
  const colors = labels.map((_, idx) => CHART_COLORS[idx % CHART_COLORS.length]);

  if (state.charts[type]) { state.charts[type].destroy(); }

  const ctx = document.getElementById(canvasId).getContext('2d');
  state.charts[type] = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { size: 11, family: 'Inter', weight: '600' },
            padding: 10,
            boxWidth: 12,
            color: 'rgba(255, 255, 255, 0.7)',
          },
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${fmt(ctx.parsed)} so'm`,
          },
        },
      },
    },
  });
}

function renderCategoryBreakdown(data) {
  const container = document.getElementById('category-breakdown');
  const all = [
    ...(data.expense_by_category ?? []).map(i => ({ ...i, type: 'expense' })),
    ...(data.income_by_category  ?? []).map(i => ({ ...i, type: 'income'  })),
  ].sort((a, b) => b.total - a.total);

  if (!all.length) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📊</span>
        <p>Bu oyda ma'lumot yo'q</p>
      </div>`;
    return;
  }

  const maxVal = Math.max(...all.map(i => i.total));
  container.innerHTML = all.map(item => {
    const pct = maxVal > 0 ? (item.total / maxVal) * 100 : 0;
    const barCls = item.type === 'income' ? 'income-bar' : 'expense-bar';
    const typeCls = item.type === 'income' ? 'type-income' : 'type-expense';
    const typeLabel = item.type === 'income' ? 'Daromad' : 'Xarajat';
    return `
      <div class="cat-row">
        <span class="cat-row-type ${typeCls}">${typeLabel}</span>
        <div class="cat-bar-wrap">
          <div class="cat-bar-label">
            <span>${item.category}</span>
            <span>${fmt(item.total)} so'm</span>
          </div>
          <div class="cat-bar-track">
            <div class="cat-bar-fill ${barCls}" style="width:${pct.toFixed(1)}%"></div>
          </div>
        </div>
      </div>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════
// AI CHAT
// ══════════════════════════════════════════════════════════
function appendMessage(text, role) {
  const container = document.getElementById('chat-messages');
  const isAI = role === 'ai';
  const div = document.createElement('div');
  div.className = `chat-row ${isAI ? 'ai-row' : 'usr-row'}`;
  div.innerHTML = isAI
    ? `<div class="chat-avatar">🤖</div><div class="chat-bubble ai-bubble">${text}</div>`
    : `<div class="chat-bubble user-bubble">${text}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function showTypingIndicator() {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-row ai-row';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="chat-avatar">🤖</div>
    <div class="chat-bubble ai-bubble loading-bubble">
      <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  document.getElementById('typing-indicator')?.remove();
}

async function sendAIMessage() {
  const input = document.getElementById('ai-input');
  const msg = input.value.trim();
  if (!msg) return;

  haptic('light');
  input.value = '';
  appendMessage(msg, 'user');
  showTypingIndicator();

  // Hide quick question buttons once chat starts
  document.querySelector('.quick-questions').style.display = 'none';

  try {
    const data = await apiFetch('/api/ai-advice', {
      method: 'POST',
      body: JSON.stringify({ user_id: state.userId, message: msg }),
    });
    removeTypingIndicator();
    appendMessage(data.advice ?? "Kechirasiz, javob berilmadi.", 'ai');
    haptic('light');
  } catch {
    removeTypingIndicator();
    appendMessage("Kechirasiz, xato yuz berdi. Iltimos qayta urinib ko'ring.", 'ai');
  }
}

function sendQuickQuestion(q) {
  document.getElementById('ai-input').value = q;
  sendAIMessage();
}

// ══════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════
async function init() {
  initTelegram();

  // Render category grids once
  renderCategories('expense');
  renderCategories('income');

  // Load initial home data
  await loadHome();

  // Hide loading screen
  const loading = document.getElementById('loading-screen');
  loading.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', init);
