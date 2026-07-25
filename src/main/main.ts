import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildMovePlan, executeMovePlan, portableDataDir, undoLastAction, MovePlanItem } from '../utils/organizer.js';
import { scanFolder, ScanProgress } from '../utils/scanner.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
let mainWindow: BrowserWindow | undefined;
let lastPlan: MovePlanItem[] = [];

function getExeDirectory(): string {
  return app.isPackaged ? path.dirname(process.execPath) : path.resolve(process.cwd());
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    title: "Grandma's Storage Helper",
    backgroundColor: '#f8fafc',
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  } else {
    mainWindow.loadURL('http://127.0.0.1:5173');
  }
}

app.whenReady().then(() => {
  app.setPath('userData', portableDataDir(getExeDirectory()));
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.handle('dialog:pick-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory'],
    title: 'Choose a folder'
  });
  return result.canceled ? undefined : result.filePaths[0];
});

ipcMain.handle('scan:start', async (_event, root: string) => {
  const sender = mainWindow?.webContents;
  const summary = await scanFolder(root, (progress: ScanProgress) => {
    sender?.send('scan:progress', progress);
  });
  return summary;
});

ipcMain.handle('plan:create', async (_event, files, targetRoot: string, keepDuplicates: boolean) => {
  lastPlan = buildMovePlan(files, targetRoot, keepDuplicates);
  return lastPlan;
});

ipcMain.handle('plan:execute', async (_event, plan: MovePlanItem[] | undefined) => {
  const dataDir = portableDataDir(getExeDirectory());
  return executeMovePlan(plan?.length ? plan : lastPlan, dataDir);
});

ipcMain.handle('plan:undo', async () => {
  const dataDir = portableDataDir(getExeDirectory());
  return undoLastAction(dataDir);
});

ipcMain.handle('app:portable-data-dir', async () => portableDataDir(getExeDirectory()));
