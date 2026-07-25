import { contextBridge, ipcRenderer } from 'electron';
import type { ExecuteResult, MovePlanItem } from '../utils/organizer.js';
import type { ScannedFile, ScanProgress, ScanSummary } from '../utils/scanner.js';

const api = {
  pickFolder: () => ipcRenderer.invoke('dialog:pick-folder') as Promise<string | undefined>,
  scanFolder: (root: string) => ipcRenderer.invoke('scan:start', root) as Promise<ScanSummary>,
  createPlan: (files: ScannedFile[], targetRoot: string, keepDuplicates: boolean) => ipcRenderer.invoke('plan:create', files, targetRoot, keepDuplicates) as Promise<MovePlanItem[]>,
  executePlan: (plan?: MovePlanItem[]) => ipcRenderer.invoke('plan:execute', plan) as Promise<ExecuteResult>,
  undoLastAction: () => ipcRenderer.invoke('plan:undo') as Promise<ExecuteResult>,
  getPortableDataDir: () => ipcRenderer.invoke('app:portable-data-dir') as Promise<string>,
  onScanProgress: (callback: (progress: ScanProgress) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, progress: ScanProgress) => callback(progress);
    ipcRenderer.on('scan:progress', listener);
    return () => ipcRenderer.removeListener('scan:progress', listener);
  }
};

contextBridge.exposeInMainWorld('storageHelper', api);

export type StorageHelperApi = typeof api;
