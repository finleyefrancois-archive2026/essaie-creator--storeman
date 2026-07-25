import { mkdir, rename, writeFile, readFile, access } from 'node:fs/promises';
import path from 'node:path';
import { ScannedFile } from './scanner.js';

export interface MovePlanItem {
  source: string;
  destination: string;
  action: 'move' | 'skip-duplicate';
  reason: string;
}

export interface ExecuteResult {
  moved: Array<{ source: string; destination: string }>;
  skipped: Array<{ source: string; reason: string }>;
  logPath: string;
}

export function portableDataDir(exeDir: string): string {
  return path.join(exeDir, 'data');
}

export function categoryDestination(targetRoot: string, file: ScannedFile): string {
  const year = Number.isFinite(file.modifiedAt) ? new Date(file.modifiedAt).getFullYear().toString() : 'Unknown Year';
  return path.join(targetRoot, file.category, year, file.name);
}

async function exists(filePath: string): Promise<boolean> {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

export async function uniquePath(destination: string): Promise<string> {
  if (!(await exists(destination))) return destination;
  const directory = path.dirname(destination);
  const extension = path.extname(destination);
  const base = path.basename(destination, extension);
  for (let index = 1; index < 10000; index += 1) {
    const candidate = path.join(directory, `${base}_${index}${extension}`);
    if (!(await exists(candidate))) return candidate;
  }
  throw new Error('We found too many files with the same name. Please choose a different folder.');
}

export function buildMovePlan(files: ScannedFile[], targetRoot: string, keepDuplicates: boolean): MovePlanItem[] {
  return files.map((file) => {
    if (file.duplicateOf && !keepDuplicates) {
      return { source: file.path, destination: file.path, action: 'skip-duplicate', reason: 'This is an exact copy of another file.' };
    }
    return { source: file.path, destination: categoryDestination(targetRoot, file), action: 'move', reason: 'Organize by file type and year.' };
  });
}

export async function executeMovePlan(plan: MovePlanItem[], dataDir: string): Promise<ExecuteResult> {
  await mkdir(dataDir, { recursive: true });
  const moved: ExecuteResult['moved'] = [];
  const skipped: ExecuteResult['skipped'] = [];

  for (const item of plan) {
    if (item.action === 'skip-duplicate') {
      skipped.push({ source: item.source, reason: item.reason });
      continue;
    }
    try {
      await mkdir(path.dirname(item.destination), { recursive: true });
      const destination = await uniquePath(item.destination);
      await rename(item.source, destination);
      moved.push({ source: item.source, destination });
    } catch (error) {
      const nodeError = error as NodeJS.ErrnoException;
      const reason = nodeError.code === 'ENAMETOOLONG'
        ? 'This file path is too long for Windows.'
        : nodeError.code === 'EACCES' || nodeError.code === 'EPERM'
          ? 'Windows denied permission. Try closing apps that use this file.'
          : nodeError.message || 'Could not move this file.';
      skipped.push({ source: item.source, reason });
    }
  }

  const logPath = path.join(dataDir, 'audit_log.json');
  await writeFile(logPath, JSON.stringify({ createdAt: new Date().toISOString(), moved, skipped }, null, 2), 'utf8');
  return { moved, skipped, logPath };
}

export async function undoLastAction(dataDir: string): Promise<ExecuteResult> {
  const logPath = path.join(dataDir, 'audit_log.json');
  const audit = JSON.parse(await readFile(logPath, 'utf8')) as ExecuteResult;
  const undoPlan = audit.moved.slice().reverse().map((move) => ({
    source: move.destination,
    destination: move.source,
    action: 'move' as const,
    reason: 'Undo last organization.'
  }));
  return executeMovePlan(undoPlan, dataDir);
}
