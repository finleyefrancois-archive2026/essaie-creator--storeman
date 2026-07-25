import type { ScanProgress } from '../../utils/scanner';

interface Props { busy: boolean; source: string; target: string; progress: ScanProgress; progressPercent: number; duplicateCount: number; canPreview: boolean; onPickSource: () => void; onPickTarget: () => void; onScan: () => void; onPreview: () => void; onUndo: () => void; }
export function Dashboard(props: Props) {
  return <section className="rounded-3xl bg-white p-6 shadow-xl dark:bg-slate-900">
    <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
      <div><h1 className="text-4xl font-black md:text-6xl">Grandma's Storage Helper</h1><p className="mt-3 text-xl text-slate-600 dark:text-slate-300">Clean up files safely. Nothing moves until you approve it.</p></div>
      <div className="grid gap-3"><button className="min-h-[64px] rounded-2xl bg-blue-600 px-8 text-2xl font-black text-white disabled:opacity-50" disabled={busy} onClick={props.onScan}>Scan My Computer</button><button className="min-h-[64px] rounded-2xl bg-green-600 px-8 text-2xl font-black text-white disabled:opacity-50" disabled={!props.canPreview || busy} onClick={props.onPreview}>Organize Files</button></div>
    </div>
    <div className="mt-6 grid gap-4 md:grid-cols-2"><button className="rounded-2xl border-2 border-dashed border-blue-400 p-5 text-left" onClick={props.onPickSource}><span className="block text-lg font-bold">Folder to clean</span><span className="break-all text-slate-600 dark:text-slate-300">{props.source || 'Click to choose a folder'}</span></button><button className="rounded-2xl border-2 border-dashed border-green-400 p-5 text-left" onClick={props.onPickTarget}><span className="block text-lg font-bold">Where organized files go</span><span className="break-all text-slate-600 dark:text-slate-300">{props.target || 'Click to choose, or we will suggest one'}</span></button></div>
    <div className="mt-6"><div className="h-8 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"><div className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all" style={{ width: `${props.progressPercent}%` }} /></div><p className="mt-3 text-lg font-semibold">{props.progress.message}</p><p className="text-slate-600 dark:text-slate-300">Duplicate files found: {props.duplicateCount}</p></div>
    <button className="mt-5 min-h-[60px] rounded-2xl bg-slate-700 px-6 text-xl font-bold text-white" disabled={busy} onClick={props.onUndo}>Undo Last Action</button>
  </section>;
}
