import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const contractCases = [
  {
    path: '../src/app/news/page.tsx',
    schemaName: 'newsFilterSchema',
  },
  {
    path: '../src/app/daily-summary/page.tsx',
    schemaName: 'dailySummaryFormSchema',
  },
  {
    path: '../src/app/search/page.tsx',
    schemaName: 'searchQuestionSchema',
  },
];

test('news/daily-summary/search pages should adopt zod + react-hook-form primitives', async () => {
  for (const item of contractCases) {
    const fullPath = path.resolve(__dirname, item.path);
    const source = await readFile(fullPath, 'utf8');

    assert.equal(source.includes(item.schemaName), true, `missing schema ${item.schemaName} in ${item.path}`);
    assert.equal(source.includes('useForm'), true, `missing useForm in ${item.path}`);
    assert.equal(source.includes('zodResolver'), true, `missing zodResolver in ${item.path}`);
    assert.equal(source.includes('<FormField'), true, `missing FormField in ${item.path}`);
  }
});
