import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const pageFiles = [
  '../src/app/page.tsx',
  '../src/app/news/page.tsx',
  '../src/app/daily-summary/page.tsx',
  '../src/app/search/page.tsx',
  '../src/app/events/page.tsx',
  '../src/app/asset/[id]/page.tsx',
];

test('non-research app pages should avoid slate hardcoded classes', async () => {
  for (const relativePath of pageFiles) {
    const fullPath = path.resolve(__dirname, relativePath);
    const source = await readFile(fullPath, 'utf8');
    assert.equal(
      source.includes('slate-'),
      false,
      `Found slate-* hardcoded class in ${relativePath}`,
    );
  }
});
