export function isMainBoardCode(value) {
  const code = String(value || '').trim();
  return /^(?:60[0-5]\d{3}|000\d{3}|001\d{3}|002\d{3}|003\d{3})$/.test(code);
}

export function evaluateChecklist(gates) {
  const keys = ['marketGate', 'boardGate', 'stockGate', 'entryGate', 'riskGate'];
  const score = keys.reduce((total, key) => total + (gates[key] ? 1 : 0), 0);
  const action = gates.codeValid === false || !gates.marketGate || !gates.riskGate
    ? '禁止买入'
    : score === keys.length
      ? '允许买入'
      : score >= 3
        ? '等待确认'
        : '禁止买入';
  return { score, total: keys.length, action };
}

export function calculatePosition({ account, riskPercent, entry, stop, maxPositionPercent }) {
  const capital = Number(account) || 0;
  const risk = Number(riskPercent) || 0;
  const buy = Number(entry) || 0;
  const loss = Number(stop) || 0;
  const cap = Number(maxPositionPercent) || 0;
  const riskPerShare = buy - loss;
  if (capital <= 0 || risk <= 0 || buy <= 0 || loss <= 0 || riskPerShare <= 0 || cap <= 0) {
    return { shares: 0, positionValue: 0, positionPercent: 0, riskAmount: 0 };
  }
  const riskBudget = capital * risk / 100;
  const valueCap = capital * cap / 100;
  const rawShares = Math.min(riskBudget / riskPerShare, valueCap / buy);
  const shares = Math.floor(rawShares / 100) * 100;
  const positionValue = shares * buy;
  return {
    shares,
    positionValue: Math.round(positionValue * 100) / 100,
    positionPercent: Math.round(positionValue / capital * 10000) / 100,
    riskAmount: Math.round(shares * riskPerShare * 100) / 100,
  };
}
