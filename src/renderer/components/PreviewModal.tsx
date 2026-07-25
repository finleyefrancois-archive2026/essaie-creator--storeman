import type { MovePlanItem } from '../../utils/organizer';

interface Props { open: boolean; plan: MovePlanItem[]; busy: boolean; onClose: () => void; onConfirm: () => void; }
export function PreviewModal({ open, plan, busy, onClose, onConfirm }: Props) {
  if (!open) return null;
  const moving = plan.filter((item) => item.action === 'move').length;
  const skipped = plan.length - moving;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
    <div className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-6 shadow-2xl dark:bg-slate-900">
      <h2 className="text-4xl font-black text-red-600">Check before moving files</h2><p className="mt-3 text-xl">We will move {moving} files and leave {skipped} duplicate files alone. Please review the list before continuing.</p>
      <div className="mt-5 max-h-96 space-y-2 overflow-auto rounded-2xl bg-slate-100 p-4 dark:bg-slate-800">{plan.slice(0, 300).map((item) => <div key={`${item.source}-${item.destination}`} className="border-b border-slate-300 py-2 dark:border-slate-700"><p className="break-all font-bold">{item.source}</p><p className="break-all text-green-700 dark:text-green-300">{item.action === 'move' ? `Move to ${item.destination}` : 'Skip exact copy'}</p></div>)}</div>
      <div className="mt-6 flex flex-wrap justify-end gap-3"><button className="min-h-[60px] rounded-2xl bg-slate-600 px-6 text-xl font-bold text-white" disabled={busy} onClick={onClose}>Go Back</button><button className="min-h-[60px] rounded-2xl bg-red-600 px-6 text-xl font-black text-white" disabled={busy} onClick={onConfirm}>Yes, Organize Files</button></div>
    </div>
  </div>;
}
