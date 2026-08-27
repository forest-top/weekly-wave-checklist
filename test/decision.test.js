import test from 'node:test';
import assert from 'node:assert/strict';
import { calculatePosition, evaluateChecklist, isMainBoardCode } from '../src/decision.js';

test('accepts only Shanghai and Shenzhen main-board codes', () => {
  assert.equal(isMainBoardCode('600000'), true);
  assert.equal(isMainBoardCode('000001'), true);
  assert.equal(isMainBoardCode('001979'), true);
  assert.equal(isMainBoardCode('300750'), false);
  assert.equal(isMainBoardCode('688981'), false);
  assert.equal(isMainBoardCode('830799'), false);
});

test('does not block a buy decision when the market reference is disabled', () => {
  const result = evaluateChecklist({
    marketGate: false,
    boardGate: true,
    stockGate: true,
    entryGate: true,
    riskGate: true,
  });
  assert.equal(result.action, '允许买入');
  assert.equal(result.score, 4);
  assert.equal(result.total, 4);
});

test('blocks a non-main-board code even when every checklist gate passes', () => {
  const result = evaluateChecklist({
    codeValid: false,
    marketGate: true,
    boardGate: true,
    stockGate: true,
    entryGate: true,
    riskGate: true,
  });
  assert.equal(result.action, '禁止买入');
});

test('calculates shares from account risk and caps the position', () => {
  assert.deepEqual(calculatePosition({
    account: 100000,
    riskPercent: 0.5,
    entry: 20,
    stop: 18,
    maxPositionPercent: 15,
  }), {
    shares: 200,
    positionValue: 4000,
    positionPercent: 4,
    riskAmount: 400,
  });
});
