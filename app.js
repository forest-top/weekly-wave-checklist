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

fields.forEach((id) => $(id).addEventListener('input', updateDecision));
checks.forEach((input) => input.addEventListener('change', updateDecision));
$('updateButton').addEventListener('click', updateDecision); $('resetButton').addEventListener('click', reset); $('exportButton').addEventListener('click', exportChecklist);
restore();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js');
