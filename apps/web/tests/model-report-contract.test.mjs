import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const homePagePath = path.resolve(__dirname, '../src/app/page.tsx');
const modelSelectorPath = path.resolve(__dirname, '../src/components/ModelSelector.tsx');
const reportBadgePath = path.resolve(__dirname, '../src/components/ReportBadge.tsx');

test('home page should mount model selector and report badge blocks', async () => {
  const source = await readFile(homePagePath, 'utf8');
  assert.equal(source.includes('<ModelSelector'), true);
  assert.equal(source.includes('<ReportBadge'), true);
});

test('model/report components should call stage10 APIs', async () => {
  const selectorSource = await readFile(modelSelectorPath, 'utf8');
  const badgeSource = await readFile(reportBadgePath, 'utf8');
  assert.equal(selectorSource.includes('getModelRegistry'), true);
  assert.equal(selectorSource.includes('selectModel'), true);
  assert.equal(badgeSource.includes('getLatestReport'), true);
  assert.equal(badgeSource.includes('generateDailyReport'), true);
});
