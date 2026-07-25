interface Props { dark: boolean; keepDuplicates: boolean; dataDir: string; onDarkChange: (value: boolean) => void; onKeepDuplicatesChange: (value: boolean) => void; }
export function Settings({ dark, keepDuplicates, dataDir, onDarkChange, onKeepDuplicatesChange }: Props) {
  return <section className="mt-5 grid gap-4 rounded-3xl bg-white p-6 shadow-xl dark:bg-slate-900 md:grid-cols-3">
    <label className="flex items-center gap-3 text-lg font-bold"><input className="h-7 w-7" type="checkbox" checked={dark} onChange={(event) => onDarkChange(event.currentTarget.checked)} /> Dark mode</label>
    <label className="flex items-center gap-3 text-lg font-bold"><input className="h-7 w-7" type="checkbox" checked={keepDuplicates} onChange={(event) => onKeepDuplicatesChange(event.currentTarget.checked)} /> Keep exact copies</label>
    <div><p className="font-bold">Portable log folder</p><p className="break-all text-sm text-slate-600 dark:text-slate-300">{dataDir || 'Loading...'}</p></div>
  </section>;
}
