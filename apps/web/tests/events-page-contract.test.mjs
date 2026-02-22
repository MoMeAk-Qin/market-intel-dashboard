import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const eventsPagePath = path.resolve(__dirname, '../src/app/events/page.tsx');

test('events page should use zod schema with react-hook-form', async () => {
  const source = await readFile(eventsPagePath, 'utf8');
  assert.equal(source.includes('eventsFilterSchema'), true);
  assert.equal(source.includes('useForm'), true);
  assert.equal(source.includes('zodResolver'), true);
});

test('events page should use Form primitives for filter validation feedback', async () => {
  const source = await readFile(eventsPagePath, 'utf8');
  assert.equal(source.includes('<Form '), true);
  assert.equal(source.includes('<FormField'), true);
  assert.equal(source.includes('<FormMessage'), true);
});
