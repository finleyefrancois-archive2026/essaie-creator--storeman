import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { opendir, stat } from 'node:fs/promises';
import path from 'node:path';

export type FileCategory = 'Photos' | 'Documents' | 'Videos' | 'Music' | 'Archives' | 'Other';

export interface ScannedFile {
  id: string;
  path: string;
  name: string;
  extension: string;
  size: number;
  createdAt: number;
  modifiedAt: number;
  category: FileCategory;
  hash: string;
  duplicateOf?: string;
  error?: string;
}

export interface ScanProgress {
  phase: 'walking' | 'hashing' | 'complete' | 'error';
  message: string;
  scanned: number;
  total?: number;
  file?: ScannedFile;
}

export interface ScanSummary {
  files: ScannedFile[];
  duplicates: ScannedFile[];
  skipped: Array<{ path: string; reason: string }>;
}

const CATEGORY_EXTENSIONS: Record<FileCategory, Set<string>> = {
  Photos: new Set(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tif', '.tiff', '.svg']),
  Documents: new Set(['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv']),
  Videos: new Set(['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.webm', '.m4v']),
  Music: new Set(['.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg']),
  Archives: new Set(['.zip', '.rar', '.7z', '.tar', '.gz']),
  Other: new Set()
};

export function categorizeFile(filePath: string): FileCategory {
  const extension = path.extname(filePath).toLowerCase();
  for (const [category, extensions] of Object.entries(CATEGORY_EXTENSIONS) as Array<[FileCategory, Set<string>]>) {
    if (extensions.has(extension)) return category;
  }
  return 'Other';
}

export function friendlyFsError(error: unknown): string {
  const nodeError = error as NodeJS.ErrnoException;
  if (nodeError.code === 'EACCES' || nodeError.code === 'EPERM') return 'Windows would not let us open this file. It may need permission.';
  if (nodeError.code === 'ENOENT') return 'The file disappeared before we could scan it.';
  if (nodeError.code === 'ENAMETOOLONG') return 'This path is too long for Windows to handle safely.';
  if (nodeError.code === 'EBUSY') return 'This file is open in another program, so we skipped it.';
  return nodeError.message || 'Something unexpected happened while reading this file.';
}

async function walkDirectory(root: string, skipped: ScanSummary['skipped'], onProgress?: (progress: ScanProgress) => void): Promise<string[]> {
  const found: string[] = [];
  const pending = [root];
  while (pending.length > 0) {
    const current = pending.pop()!;
    try {
      const dir = await opendir(current);
      for await (const entry of dir) {
        const fullPath = path.join(current, entry.name);
        if (entry.isDirectory()) {
          pending.push(fullPath);
        } else if (entry.isFile()) {
          found.push(fullPath);
          onProgress?.({ phase: 'walking', message: `Found ${found.length} files so far`, scanned: found.length });
        }
      }
    } catch (error) {
      skipped.push({ path: current, reason: friendlyFsError(error) });
      onProgress?.({ phase: 'error', message: friendlyFsError(error), scanned: found.length });
    }
  }
  return found;
}

export async function hashFile(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256');
    const stream = createReadStream(filePath);
    stream.on('error', reject);
    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

export async function scanFolder(root: string, onProgress?: (progress: ScanProgress) => void): Promise<ScanSummary> {
  const skipped: ScanSummary['skipped'] = [];
  const files: ScannedFile[] = [];
  const hashes = new Map<string, string>();
  const filePaths = await walkDirectory(root, skipped, onProgress);

  let scanned = 0;
  for (const filePath of filePaths) {
    try {
      const [metadata, hash] = await Promise.all([stat(filePath), hashFile(filePath)]);
      const duplicateOf = hashes.get(hash);
      if (!duplicateOf) hashes.set(hash, filePath);
      const file: ScannedFile = {
        id: hash + ':' + filePath,
        path: filePath,
        name: path.basename(filePath),
        extension: path.extname(filePath).toLowerCase(),
        size: metadata.size,
        createdAt: metadata.birthtimeMs,
        modifiedAt: metadata.mtimeMs,
        category: categorizeFile(filePath),
        hash,
        duplicateOf
      };
      files.push(file);
      scanned += 1;
      onProgress?.({ phase: 'hashing', message: `Checked ${scanned} of ${filePaths.length} files`, scanned, total: filePaths.length, file });
    } catch (error) {
      skipped.push({ path: filePath, reason: friendlyFsError(error) });
      scanned += 1;
      onProgress?.({ phase: 'error', message: friendlyFsError(error), scanned, total: filePaths.length });
    }
  }

  const duplicates = files.filter((file) => Boolean(file.duplicateOf));
  onProgress?.({ phase: 'complete', message: `Scan complete. ${duplicates.length} duplicate files found.`, scanned, total: filePaths.length });
  return { files, duplicates, skipped };
}
