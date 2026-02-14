import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const assetPagePath = path.resolve(__dirname, '../src/app/asset/[id]/page.tsx');

test('asset page should call profile endpoint only', async () => {
  const source = await readFile(assetPagePath, 'utf8');
  assert.equal(source.includes('/assets/${assetId}/profile'), true);
  assert.equal(source.includes('/assets/${assetId}/quote'), false);
  assert.equal(source.includes('/assets/${assetId}/series'), false);
});

test('asset page should not depend on legacy chart demo text or endpoint', async () => {
  const source = await readFile(assetPagePath, 'utf8');
  assert.equal(source.includes('/assets/${assetId}/chart'), false);
  assert.equal(source.includes('演示行情（非实时）'), false);
});
