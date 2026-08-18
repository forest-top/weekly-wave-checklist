import { calculatePosition, evaluateChecklist, isMainBoardCode } from './src/decision.js';

const storageKey = 'weekly-wave-checklist-v2';
const fields = ['checkDate', 'stockCode', 'stockName', 'dataDate', 'account', 'riskPercent', 'entry', 'stop', 'maxPosition'];
const checks = [...document.querySelectorAll('input[type="checkbox"]')];
const $ = (id) => document.getElementById(id);

function today() { return new Date().toISOString().slice(0, 10); }
function readState() {
  try { return JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch { return {}; }
}
function saveState() {
  const state = Object.fromEntries(fields.map((id) => [id, $(id).value]));
  state.checks = checks.map((input) => input.checked);
  localStorage.setItem(storageKey, JSON.stringify(state));
}
function groupPassed(name) {
  const group = checks.filter((input) => input.dataset.gate === name);
  return group.length > 0 && group.every((input) => input.checked);
}
function updateGate(name) {
  const passed = groupPassed(name);
  const element = $(`${name}Gate`);
  element.textContent = passed ? '通过' : '未完成';
  element.style.color = passed ? 'var(--teal)' : 'var(--muted)';
  return passed;
}
function money(value) { return `¥${Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`; }
function updatePosition() {
  const result = calculatePosition({
    account: $('account').value,
    riskPercent: $('riskPercent').value,
    entry: $('entry').value,
    stop: $('stop').value,
    maxPositionPercent: $('maxPosition').value,
  });
  $('shares').textContent = `${result.shares.toLocaleString('zh-CN')} 股`;
  $('positionPercent').textContent = `${result.positionPercent}%`;
  $('riskAmount').textContent = money(result.riskAmount);
}
function updateDecision() {
  const codeValid = isMainBoardCode($('stockCode').value);
  $('codeNote').textContent = codeValid ? '主板代码有效。请继续完成所有条件。' : '只接受沪深主板：60、000、001、002、003 开头。';
  $('codeNote').style.color = codeValid ? 'var(--teal)' : 'var(--muted)';
  const gates = {
    codeValid, marketGate: updateGate('market'), boardGate: updateGate('board'), stockGate: updateGate('stock'),
    entryGate: updateGate('entry'), riskGate: updateGate('risk'),
  };
  const result = evaluateChecklist(gates);
  const label = $('actionLabel');
  label.textContent = result.action;
  $('scoreLabel').textContent = `${result.score} / ${result.total}`;
  $('scoreBar').style.width = `${result.score / result.total * 100}%`;
  const card = document.querySelector('.decision-card');
  card.classList.remove('status-ok', 'status-wait', 'status-stop');
  card.classList.add(result.action === '允许买入' ? 'status-ok' : result.action === '等待确认' ? 'status-wait' : 'status-stop');
  $('reasonLabel').textContent = !codeValid ? '股票代码不是沪深主板，禁止进入买入清单。' : result.action === '允许买入' ? '全部条件通过，可按计算仓位执行。' : result.action === '等待确认' ? '还有条件未完成，只能观察。' : '大盘或风控未通过，禁止买入。';
  saveState(); updatePosition();
}
function restore() {
  const state = readState();
  $('checkDate').value = state.checkDate || today();
  $('dataDate').value = state.dataDate || '';
  fields.slice(1).forEach((id) => { if (state[id] !== undefined) $(id).value = state[id]; });
  (state.checks || []).forEach((value, index) => { if (checks[index]) checks[index].checked = value; });
  updateDecision();
}
function reset() {
  localStorage.removeItem(storageKey);
  document.querySelectorAll('input').forEach((input) => { if (input.type === 'checkbox') input.checked = false; else input.value = ''; });
  $('checkDate').value = today(); $('riskPercent').value = '0.5'; $('maxPosition').value = '15'; updateDecision();
}
function exportChecklist() {
  updateDecision();
  const state = readState();
  const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), ...state }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `主板周线三浪-${state.stockCode || '未命名'}-${state.checkDate || today()}.json`; link.click(); URL.revokeObjectURL(url);
}

function stars(count) { return '★'.repeat(count) + '☆'.repeat(5 - count); }
function candidateCard(candidate) {
  const card = document.createElement('article'); card.className = 'candidate';
  const top = document.createElement('div'); top.className = 'candidate-top';
  const title = document.createElement('h3'); title.textContent = candidate.name;
  const code = document.createElement('code'); code.textContent = candidate.code;
  const titleWrap = document.createElement('div'); titleWrap.append(title, code);
  const rating = document.createElement('span'); rating.className = 'stars'; rating.textContent = stars(candidate.stars);
  top.append(titleWrap, rating);
  const action = document.createElement('p'); action.className = 'candidate-action'; action.textContent = candidate.action;
  const reasons = document.createElement('p'); reasons.className = 'candidate-reasons'; reasons.textContent = (candidate.reasons || []).slice(0, 3).join('；');
  const metrics = document.createElement('div'); metrics.className = 'candidate-metrics';
  metrics.textContent = `收盘 ${candidate.price} · PB ${candidate.pb} · 乖离 ${candidate.bias}% · 保护线 ${candidate.stop_3pct}`;
  card.append(top, action, reasons, metrics); return card;
}

async function loadAutoResults() {
  try {
    const response = await fetch(`./data/latest.json?t=${Date.now()}`, { cache: 'no-store' });
    const data = await response.json();
    const list = $('candidateList'); list.replaceChildren();
    if (data.status !== 'ok') { $('autoMessage').textContent = data.message || '尚未生成扫描结果。'; return; }
    $('autoUpdated').textContent = data.data_date || '已更新';
    $('autoRule').textContent = data.soft_rule || $('autoRule').textContent;
    const market = data.market || {};
    $('autoMarket').textContent = `上证 ${market.close ?? '-'} · MA55 ${market.ma55 ?? '-'} · 5日斜率 ${market.ma55_slope_5d_pct ?? '-'}% · ${market.gate ? '大盘闸门通过' : '大盘闸门未通过，禁止买入'}`;
    const complete = data.complete_matches || [];
    $('completeBox').hidden = complete.length === 0; $('completeCount').textContent = complete.length ? `${complete.length} 只技术条件全部通过` : '';
    const recommendations = (data.candidates || []).filter((item) => item.stars >= 3).slice(0, 12);
    recommendations.forEach((candidate) => list.append(candidateCard(candidate)));
    $('autoMessage').textContent = recommendations.length ? `${data.universe} 只流动性主板股票已扫描。${data.proxy_note || ''}` : `${data.universe} 只流动性主板股票已扫描，当前没有达到 3 星的候选。${data.proxy_note || ''}`;
  } catch {
    $('autoMarket').textContent = '自动结果暂不可读取，请稍后刷新或在 GitHub 手动运行筛选。';
  }
}

fields.forEach((id) => $(id).addEventListener('input', updateDecision));
checks.forEach((input) => input.addEventListener('change', updateDecision));
$('updateButton').addEventListener('click', updateDecision); $('resetButton').addEventListener('click', reset); $('exportButton').addEventListener('click', exportChecklist);
restore();
loadAutoResults();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js');
