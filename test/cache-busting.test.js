import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('loads the app and decision module with a cache-busting version', () => {
  const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const app = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(index, /src="app\.js\?v=6"/);
  assert.match(app, /from '\.\/src\/decision\.js\?v=6'/);
});
