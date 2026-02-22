import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const researchPagePath = path.resolve(__dirname, '../src/app/research/page.tsx');

test('research page should use shared response type and form schema', async () => {
  const source = await readFile(researchPagePath, 'utf8');
  assert.equal(source.includes('ResearchCompanyResponse'), true);
  assert.equal(source.includes('useForm'), true);
  assert.equal(source.includes('zodResolver'), true);
});

test('research page should include tabs, command, and chart building blocks', async () => {
  const source = await readFile(researchPagePath, 'utf8');
  assert.equal(source.includes('<Tabs '), true);
  assert.equal(source.includes('<Command'), true);
  assert.equal(source.includes('<ChartContainer'), true);
});
