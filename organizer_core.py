"""Core file organization logic for Smart Organizer.

The module intentionally uses only the Python standard library so the app can be
bundled as a small, offline PyInstaller executable.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

CATEGORY_MAP = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".svg"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm", ".m4v"},
    "Audio": {".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
}

@dataclass
class FilePlan:
    source: str
    destination: str
    category: str
    size: int
    duplicate: bool = False
    conflict: bool = False
    error: str | None = None

@dataclass
class ScanReport:
    files: list[FilePlan] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    groups: list[dict] = field(default_factory=list)

ProgressCallback = Callable[[dict], None]


def app_data_dir(app_name: str = "SmartOrganizer", portable: bool = True) -> Path:
    """Return a stable writable data directory outside PyInstaller's temp area."""
    if portable:
        base = Path(getattr(__import__("sys"), "executable", __file__)).resolve().parent
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / app_name
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / app_name
    base.mkdir(parents=True, exist_ok=True)
    return base


def category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    for category, suffixes in CATEGORY_MAP.items():
        if suffix in suffixes:
            return category
    return "Other"


def iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            candidate = Path(current) / name
            if candidate.is_file():
                yield candidate


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination
    stem, suffix = destination.stem, destination.suffix
    for index in range(1, 10000):
        candidate = destination.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Too many conflicting files for {destination}")


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def suggested_groups(files: list[Path]) -> list[dict]:
    groups: list[dict] = []
    by_time = sorted(files, key=lambda p: p.stat().st_mtime if p.exists() else 0)
    time_group: list[str] = []
    last_time = None
    for path in by_time:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if last_time is None or abs(mtime - last_time) <= 60:
            time_group.append(str(path))
        else:
            if len(time_group) > 1:
                groups.append({"type": "Time proximity", "files": time_group})
            time_group = [str(path)]
        last_time = mtime
    if len(time_group) > 1:
        groups.append({"type": "Time proximity", "files": time_group})

    stems = [(p, p.stem.lower()) for p in files[:250]]
    used: set[str] = set()
    for path, stem in stems:
        if str(path) in used:
            continue
        matches = [str(path)]
        for other, other_stem in stems:
            if other == path or str(other) in used:
                continue
            max_len = max(len(stem), len(other_stem), 1)
            if levenshtein(stem, other_stem) / max_len <= 0.35:
                matches.append(str(other))
        if len(matches) > 1:
            used.update(matches)
            groups.append({"type": "Name similarity", "files": matches})
    return groups[:20]


def scan(source: Path, target: Path, conflict_mode: str = "rename", progress: ProgressCallback | None = None) -> ScanReport:
    report = ScanReport()
    candidates = list(iter_files(source))
    seen_hashes: dict[str, Path] = {}
    lock = threading.Lock()

    def emit(event: dict) -> None:
        if progress:
            progress(event)

    def inspect(path: Path) -> FilePlan | dict:
        try:
            category = category_for(path)
            destination = target / category / path.name
            conflict = destination.exists()
            if conflict and conflict_mode == "rename":
                destination = unique_destination(destination)
            digest = sha256_file(path)
            with lock:
                duplicate = digest in seen_hashes
                seen_hashes.setdefault(digest, path)
            return FilePlan(str(path), str(destination), category, path.stat().st_size, duplicate, conflict)
        except (PermissionError, FileNotFoundError, shutil.Error, OSError) as exc:
            return {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 4) * 2)) as executor:
        futures = [executor.submit(inspect, path) for path in candidates]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            result = future.result()
            if isinstance(result, FilePlan):
                report.files.append(result)
                emit({"type": "file", "index": index, "total": len(candidates), "file": asdict(result)})
            else:
                report.skipped.append(result)
                emit({"type": "skipped", "index": index, "total": len(candidates), **result})
    report.groups = suggested_groups(candidates)
    emit({"type": "complete", "total": len(report.files), "skipped": len(report.skipped), "groups": report.groups})
    return report


def execute(plan: list[dict], skip_duplicates: bool = False) -> dict:
    moved: list[dict] = []
    skipped: list[dict] = []
    for item in plan:
        if skip_duplicates and item.get("duplicate"):
            skipped.append({"path": item.get("source"), "error": "Duplicate skipped by setting"})
            continue
        source = Path(item["source"])
        destination = Path(item["destination"])
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                destination = unique_destination(destination)
            shutil.move(str(source), str(destination))
            moved.append({"source": str(source), "destination": str(destination)})
        except (PermissionError, FileNotFoundError, shutil.Error, OSError) as exc:
            skipped.append({"path": str(source), "error": f"{type(exc).__name__}: {exc}"})
    return {"moved": moved, "skipped": skipped, "timestamp": time.time()}


def save_undo_log(data_dir: Path, result: dict) -> Path:
    path = data_dir / "last_undo.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path


def undo(data_dir: Path) -> dict:
    log = data_dir / "last_undo.json"
    if not log.exists():
        return {"restored": [], "skipped": [{"error": "No undo log found"}]}
    payload = json.loads(log.read_text(encoding="utf-8"))
    restored, skipped = [], []
    for item in reversed(payload.get("moved", [])):
        src = Path(item["destination"])
        dst = Path(item["source"])
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restored.append({"source": str(src), "destination": str(dst)})
        except (PermissionError, FileNotFoundError, shutil.Error, OSError) as exc:
            skipped.append({"path": str(src), "error": f"{type(exc).__name__}: {exc}"})
    return {"restored": restored, "skipped": skipped}
