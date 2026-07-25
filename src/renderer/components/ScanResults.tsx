import type { MovePlanItem } from '../../utils/organizer';
import type { ScanSummary } from '../../utils/scanner';

interface Props { summary?: ScanSummary; plan: MovePlanItem[]; }
export function ScanResults({ summary, plan }: Props) {
  if (!summary) return <section className="mt-5 rounded-3xl bg-white p-6 shadow-xl dark:bg-slate-900"><h2 className="text-3xl font-black">Preview</h2><p className="text-lg text-slate-600 dark:text-slate-300">Choose a folder and scan to see a plain-English preview here.</p></section>;
  return <section className="mt-5 grid gap-5 lg:grid-cols-2">
    <article className="rounded-3xl bg-white p-6 shadow-xl dark:bg-slate-900"><h2 className="text-3xl font-black">Before → After</h2><div className="mt-4 max-h-96 space-y-3 overflow-auto pr-2">{plan.slice(0, 200).map((item) => <div key={`${item.source}-${item.destination}`} className="rounded-2xl bg-slate-100 p-4 dark:bg-slate-800"><p className="break-all font-bold">{item.source}</p><p className="break-all text-green-700 dark:text-green-300">→ {item.action === 'move' ? item.destination : 'Leave this exact copy alone'}</p><p className="text-sm text-slate-600 dark:text-slate-300">{item.reason}</p></div>)}</div></article>
    <article className="rounded-3xl bg-white p-6 shadow-xl dark:bg-slate-900"><h2 className="text-3xl font-black">What we found</h2><div className="mt-4 grid grid-cols-3 gap-3 text-center"><div className="rounded-2xl bg-blue-100 p-4 text-blue-900"><p className="text-3xl font-black">{summary.files.length}</p><p>Files</p></div><div className="rounded-2xl bg-amber-100 p-4 text-amber-900"><p className="text-3xl font-black">{summary.duplicates.length}</p><p>Copies</p></div><div className="rounded-2xl bg-red-100 p-4 text-red-900"><p className="text-3xl font-black">{summary.skipped.length}</p><p>Skipped</p></div></div><h3 className="mt-6 text-2xl font-bold">Skipped files</h3><ul className="mt-3 max-h-60 overflow-auto text-slate-700 dark:text-slate-300">{summary.skipped.length ? summary.skipped.map((item) => <li key={`${item.path}-${item.reason}`} className="mb-2 break-all">{item.path}: {item.reason}</li>) : <li>No skipped files. Great!</li>}</ul></article>
  </section>;
}
