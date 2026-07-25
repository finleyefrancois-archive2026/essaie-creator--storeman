import { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/tailwind.css';
import { Dashboard } from './components/Dashboard';
import { PreviewModal } from './components/PreviewModal';
import { ScanResults } from './components/ScanResults';
import { Settings } from './components/Settings';
import type { MovePlanItem } from '../utils/organizer';
import type { ScannedFile, ScanProgress, ScanSummary } from '../utils/scanner';

function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('theme') === 'dark');
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [keepDuplicates, setKeepDuplicates] = useState(true);
  const [summary, setSummary] = useState<ScanSummary | undefined>();
  const [plan, setPlan] = useState<MovePlanItem[]>([]);
  const [progress, setProgress] = useState<ScanProgress>({ phase: 'walking', message: 'Ready when you are.', scanned: 0 });
  const [previewOpen, setPreviewOpen] = useState(false);
  const [dataDir, setDataDir] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    window.storageHelper.getPortableDataDir().then(setDataDir);
    return window.storageHelper.onScanProgress(setProgress);
  }, []);

  const duplicateCount = summary?.duplicates.length ?? 0;
  const progressPercent = useMemo(() => {
    if (!progress.total) return progress.phase === 'complete' ? 100 : 0;
    return Math.round((progress.scanned / progress.total) * 100);
  }, [progress]);

  async function chooseSource() {
    const folder = await window.storageHelper.pickFolder();
    if (folder) {
      setSource(folder);
      if (!target) setTarget(`${folder} Organized`);
    }
  }

  async function chooseTarget() {
    const folder = await window.storageHelper.pickFolder();
    if (folder) setTarget(folder);
  }

  async function scan() {
    if (!source) return;
    setBusy(true);
    setPlan([]);
    setProgress({ phase: 'walking', message: 'Looking through your files...', scanned: 0 });
    try {
      const result = await window.storageHelper.scanFolder(source);
      setSummary(result);
      const nextPlan = await window.storageHelper.createPlan(result.files as ScannedFile[], target || `${source} Organized`, keepDuplicates);
      setPlan(nextPlan);
    } finally {
      setBusy(false);
    }
  }

  async function execute() {
    setBusy(true);
    try {
      const result = await window.storageHelper.executePlan(plan);
      setProgress({ phase: 'complete', message: `All done. Moved ${result.moved.length} files and skipped ${result.skipped.length}.`, scanned: plan.length, total: plan.length });
      setPreviewOpen(false);
    } finally {
      setBusy(false);
    }
  }

  async function undo() {
    setBusy(true);
    try {
      const result = await window.storageHelper.undoLastAction();
      setProgress({ phase: 'complete', message: `Undo finished. Restored ${result.moved.length} files.`, scanned: result.moved.length });
    } catch {
      setProgress({ phase: 'error', message: 'There is no recent action to undo yet.', scanned: 0 });
    } finally {
      setBusy(false);
    }
  }

  return <div className="min-h-screen bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-white">
    <main className="mx-auto max-w-7xl p-5">
      <Dashboard busy={busy} source={source} target={target} progress={progress} progressPercent={progressPercent} duplicateCount={duplicateCount} onPickSource={chooseSource} onPickTarget={chooseTarget} onScan={scan} onPreview={() => setPreviewOpen(true)} onUndo={undo} canPreview={plan.length > 0} />
      <Settings dark={dark} keepDuplicates={keepDuplicates} dataDir={dataDir} onDarkChange={setDark} onKeepDuplicatesChange={setKeepDuplicates} />
      <ScanResults summary={summary} plan={plan} />
    </main>
    <PreviewModal open={previewOpen} plan={plan} busy={busy} onClose={() => setPreviewOpen(false)} onConfirm={execute} />
  </div>;
}

createRoot(document.getElementById('root')!).render(<App />);
