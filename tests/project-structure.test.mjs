import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (file) => readFile(new URL(`../${file}`, import.meta.url), 'utf8');

test('electron-builder creates a single portable Windows executable', async () => {
  const config = await read('electron-builder.yml');
  assert.match(config, /target:\s*\n\s*- target: portable/);
  assert.match(config, /artifactName: GrandmaStorageHelper\.exe/);
});

test('portable data stays beside the executable', async () => {
  const main = await read('src/main/main.ts');
  const organizer = await read('src/utils/organizer.ts');
  assert.match(main, /path\.dirname\(process\.execPath\)/);
  assert.match(organizer, /path\.join\(exeDir, 'data'\)/);
});

test('scanner reports friendly Windows file errors', async () => {
  const scanner = await read('src/utils/scanner.ts');
  assert.match(scanner, /ENAMETOOLONG/);
  assert.match(scanner, /EACCES/);
  assert.match(scanner, /EPERM/);
});
