import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const correlationPagePath = path.resolve(__dirname, '../src/app/correlation/page.tsx');

test('correlation page should include preset tabs and window selector', async () => {
  const source = await readFile(correlationPagePath, 'utf8');
  assert.equal(source.includes('<Tabs '), true);
  assert.equal(source.includes('<Select'), true);
  assert.equal(source.includes('方案 A'), true);
  assert.equal(source.includes('window'), true);
});

test('correlation page should call matrix/heatmap/causal APIs', async () => {
  const source = await readFile(correlationPagePath, 'utf8');
  assert.equal(source.includes('getCorrelationMatrix'), true);
  assert.equal(source.includes('getTechHeatmap'), true);
  assert.equal(source.includes('analyzeCorrelation'), true);
  assert.equal(source.includes('<CorrelationMatrix'), true);
});
