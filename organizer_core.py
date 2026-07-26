"""Core file organization logic for Smart Organizer.

The module intentionally uses only the Python standard library so the app can be
bundled as a small, offline PyInstaller executable.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import os
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# Configure structured logging
logger = logging.getLogger(__name__)

# Named constants for maintainability
TIME_PROXIMITY_THRESHOLD_SECONDS = 60  # Files within 1 minute considered related
NAME_SIMILARITY_THRESHOLD = 0.35  # 35% character difference max for grouping
MAX_CONFLICT_RETRIES = 10000  # Max _N suffix attempts
HASH_CHUNK_SIZE = 1024 * 1024  # 1MB chunks for hashing
DEFAULT_MAX_WORKERS_MULTIPLIER = 4  # Multiplier for CPU count in thread pool

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


def sha256_file(path: Path, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """Calculate SHA-256 hash of a file in chunks.
    
    Args:
        path: Path to the file to hash
        chunk_size: Size of chunks to read (default 1MB)
        
    Returns:
        Hexadecimal string of SHA-256 hash
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file can't be read
        OSError: For other I/O errors
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_destination(destination: Path, max_retries: int = MAX_CONFLICT_RETRIES) -> Path:
    """Generate a unique destination path by appending _N suffix.
    
    Args:
        destination: Original destination path
        max_retries: Maximum number of suffix attempts
        
    Returns:
        A unique path that doesn't exist
        
    Raises:
        FileExistsError: If unable to generate unique name within max_retries
    """
    if not destination.exists():
        return destination
    stem, suffix = destination.stem, destination.suffix
    for index in range(1, max_retries + 1):
        candidate = destination.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Too many conflicting files for {destination} (tried {max_retries} variations)")


def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    """Calculate Levenshtein distance between two strings with optional early exit.
    
    Args:
        a: First string
        b: Second string
        max_distance: Optional maximum distance threshold for early exit optimization
        
    Returns:
        Number of single-character edits needed to change one word into the other
        
    Note:
        If max_distance is provided and the actual distance exceeds it, returns early
        with a value > max_distance for performance optimization.
    """
    if a == b:
        return 0
    
    # Early exit if length difference already exceeds max_distance
    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    
    if len(a) < len(b):
        a, b = b, a
    
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        
        # Early exit optimization: if minimum possible distance exceeds threshold
        if max_distance is not None and min(current) > max_distance:
            return max_distance + 1
            
        previous = current
    return previous[-1]


def suggested_groups(files: list[Path]) -> list[dict]:
    """Suggest logical groups of files based on time proximity and name similarity.
    
    Args:
        files: List of file paths to analyze
        
    Returns:
        List of group dictionaries with type and file members (max 20 groups)
    """
    groups: list[dict] = []
    by_time = sorted(files, key=lambda p: p.stat().st_mtime if p.exists() else 0)
    time_group: list[str] = []
    last_time = None
    
    # Group files by time proximity
    for path in by_time:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if last_time is None or abs(mtime - last_time) <= TIME_PROXIMITY_THRESHOLD_SECONDS:
            time_group.append(str(path))
        else:
            if len(time_group) > 1:
                groups.append({"type": "Time proximity", "files": time_group})
            time_group = [str(path)]
        last_time = mtime
    if len(time_group) > 1:
        groups.append({"type": "Time proximity", "files": time_group})

    # Group files by name similarity (limit to first 250 for performance)
    stems = [(p, p.stem.lower()) for p in files[:250]]
    used: set[str] = set()
    
    # Calculate max_distance threshold for levenshtein optimization
    max_name_len = max((len(stem) for _, stem in stems), default=0)
    max_distance_threshold = int(max_name_len * NAME_SIMILARITY_THRESHOLD)
    
    for path, stem in stems:
        if str(path) in used:
            continue
        matches = [str(path)]
        for other, other_stem in stems:
            if other == path or str(other) in used:
                continue
            max_len = max(len(stem), len(other_stem), 1)
            # Use optimized levenshtein with early exit
            distance = levenshtein(stem, other_stem, max_distance=int(max_len * NAME_SIMILARITY_THRESHOLD) + 1)
            if distance / max_len <= NAME_SIMILARITY_THRESHOLD:
                matches.append(str(other))
        if len(matches) > 1:
            used.update(matches)
            groups.append({"type": "Name similarity", "files": matches})
    return groups[:20]


def scan(source: Path, target: Path, conflict_mode: str = "rename", progress: ProgressCallback | None = None) -> ScanReport:
    """Scan source directory and generate organization plan.
    
    Args:
        source: Source directory to scan
        target: Target directory for organized files
        conflict_mode: How to handle conflicts ("rename" or "skip")
        progress: Optional callback for progress updates
        
    Returns:
        ScanReport with file plans, skipped files, and suggested groups
        
    Raises:
        FileNotFoundError: If source doesn't exist
        PermissionError: If source can't be read
        OSError: For other I/O errors
    """
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
            
            # Compute hash for duplicate detection
            digest = sha256_file(path)
            with lock:
                duplicate = digest in seen_hashes
                seen_hashes.setdefault(digest, path)
            
            return FilePlan(
                source=str(path),
                destination=str(destination),
                category=category,
                size=path.stat().st_size,
                duplicate=duplicate,
                conflict=conflict
            )
        except (PermissionError, FileNotFoundError, shutil.Error, OSError) as exc:
            logger.warning(f"Failed to inspect {path}: {exc}")
            return {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}

    # Use thread pool optimized for I/O-bound operations
    max_workers = min(64, (os.cpu_count() or 4) * DEFAULT_MAX_WORKERS_MULTIPLIER)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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


class RollbackException(Exception):
    """Exception raised when a move operation fails and rollback is needed."""
    pass


def validate_plan_item(item: Any, allowed_bases: list[Path] | None = None) -> tuple[bool, str]:
    """Validate a plan item structure and paths.
    
    Args:
        item: Plan item dictionary to validate
        allowed_bases: Optional list of allowed base directories for path validation
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Note:
        This function is also used by web_server.py for API input validation.
    """
    if not isinstance(item, dict):
        return False, "Plan item must be a dictionary"
    
    required_fields = {"source", "destination"}
    missing = required_fields - set(item.keys())
    if missing:
        return False, f"Missing required fields: {missing}"
    
    try:
        source = Path(item["source"])
        destination = Path(item["destination"])
    except (TypeError, ValueError) as exc:
        return False, f"Invalid path type: {exc}"
    
    # Validate paths are absolute
    if not source.is_absolute():
        return False, f"Source path must be absolute: {source}"
    if not destination.is_absolute():
        return False, f"Destination path must be absolute: {destination}"
    
    # Basic path traversal prevention (more comprehensive in web server context)
    try:
        source_resolved = source.resolve()
        dest_resolved = destination.resolve()
        
        # Block obvious traversal attempts
        if ".." in str(source) or ".." in str(destination):
            # Allow legitimate parent references only within safe boundaries
            home = Path.home()
            try:
                source_resolved.relative_to(home)
            except ValueError:
                return False, f"Source path outside allowed directories: {source}"
            try:
                dest_resolved.relative_to(home)
            except ValueError:
                return False, f"Destination path outside allowed directories: {destination}"
                
    except (OSError, ValueError) as exc:
        return False, f"Path resolution error: {exc}"
    
    return True, ""


def execute(plan: list[dict], skip_duplicates: bool = False) -> dict:
    """Execute file organization plan with transaction safety.
    
    Implements two-phase commit: first validates all moves are possible,
    then executes with automatic rollback on failure.
    
    Args:
        plan: List of file move operations from scan()
        skip_duplicates: If True, skip files marked as duplicates
        
    Returns:
        Dictionary with 'moved', 'skipped', and 'timestamp' keys
        
    Note:
        On failure, attempts to rollback all successfully moved files
        to their original locations.
    """
    moved: list[dict] = []
    skipped: list[dict] = []
    
    # Phase 1: Validate all moves are possible
    logger.info(f"Starting execute phase 1: validating {len(plan)} operations")
    for i, item in enumerate(plan):
        if skip_duplicates and item.get("duplicate"):
            skipped.append({"path": item.get("source"), "error": "Duplicate skipped by setting"})
            continue
            
        try:
            source = Path(item["source"])
            destination = Path(item["destination"])
            
            # Validate source exists
            if not source.exists():
                raise FileNotFoundError(f"Source file does not exist: {source}")
            
            # Validate source is readable
            if not os.access(source, os.R_OK):
                raise PermissionError(f"Cannot read source file: {source}")
            
            # Validate destination parent is writable
            dest_parent = destination.parent
            if not dest_parent.exists():
                # Check if we can create the parent directory
                try:
                    dest_parent.mkdir(parents=True, exist_ok=True)
                except (PermissionError, OSError) as exc:
                    raise PermissionError(f"Cannot create destination directory: {dest_parent}") from exc
            elif not os.access(dest_parent, os.W_OK):
                raise PermissionError(f"Cannot write to destination directory: {dest_parent}")
                
        except (PermissionError, FileNotFoundError, OSError) as exc:
            logger.error(f"Validation failed for item {i}: {exc}")
            skipped.append({"path": item.get("source"), "error": f"Validation: {type(exc).__name__}: {exc}"})
            # Continue validation to find all errors upfront
    
    # Filter out already-skipped items from plan
    valid_plan = [
        item for item in plan 
        if not (skip_duplicates and item.get("duplicate"))
        and not any(s["path"] == item.get("source") for s in skipped)
    ]
    
    # Phase 2: Execute moves with rollback support
    logger.info(f"Starting execute phase 2: moving {len(valid_plan)} files")
    try:
        for item in valid_plan:
            source = Path(item["source"])
            destination = Path(item["destination"])
            
            # Ensure destination parent exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle existing destination
            if destination.exists():
                destination = unique_destination(destination)
            
            # Perform the move
            shutil.move(str(source), str(destination))
            moved.append({"source": str(source), "destination": str(destination)})
            logger.debug(f"Moved: {source} -> {destination}")
            
    except (PermissionError, FileNotFoundError, shutil.Error, OSError) as exc:
        logger.error(f"Move failed: {exc}. Initiating rollback of {len(moved)} files...")
        
        # Auto-rollback: move files back to original locations
        rollback_failures = []
        for moved_item in reversed(moved):
            src = Path(moved_item["destination"])
            dst = Path(moved_item["source"])
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                logger.info(f"Rolled back: {src} -> {dst}")
            except (PermissionError, FileNotFoundError, shutil.Error, OSError) as rollback_exc:
                logger.error(f"Rollback failed for {src}: {rollback_exc}")
                rollback_failures.append({
                    "path": str(src),
                    "error": f"Rollback failed: {type(rollback_exc).__name__}: {rollback_exc}"
                })
        
        # Add rollback failures to skipped
        skipped.extend(rollback_failures)
        
        # Return with error indication
        return {
            "moved": [],
            "skipped": skipped,
            "timestamp": time.time(),
            "error": f"Operation failed and rolled back: {type(exc).__name__}: {exc}",
            "partial": len(moved) > 0
        }
    
    logger.info(f"Execute completed: {len(moved)} moved, {len(skipped)} skipped")
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
