"""
Pair RAW and JPG trees: find orphan JPGs (no matching RAW) or orphan RAWs (no matching JPG).
"""
from __future__ import annotations

import os
from pathlib import Path

# Common camera RAW extensions (lowercase, without dot)
RAW_EXTENSIONS: frozenset[str] = frozenset(
    {
        "cr2",
        "cr3",
        "nef",
        "nrw",
        "arw",
        "srf",
        "sr2",
        "dng",
        "erf",
        "mef",
        "mos",
        "orf",
        "pef",
        "ptx",
        "pxn",
        "raf",
        "raw",
        "rw2",
        "rwl",
        "srw",
        "x3f",
        "3fr",
        "fff",
        "eip",
        "bay",
    }
)

JPG_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg"})


def _stems_with_raw_extensions(dir_path: Path) -> set[str]:
    """Lowercase stems of files in dir_path whose extension is a known RAW type."""
    stems: set[str] = set()
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                name = entry.name
                if "." not in name:
                    continue
                ext = name.rsplit(".", 1)[-1].lower()
                if ext in RAW_EXTENSIONS:
                    stems.add(name[: -len(ext) - 1].lower())
    except OSError:
        pass
    return stems


def _jpg_files_in_dir(dir_path: Path) -> list[Path]:
    out: list[Path] = []
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                name = entry.name
                if "." not in name:
                    continue
                ext = name.rsplit(".", 1)[-1].lower()
                if ext in JPG_EXTENSIONS:
                    out.append(Path(entry.path))
    except OSError:
        pass
    return out


def _raw_files_in_dir(dir_path: Path) -> list[Path]:
    out: list[Path] = []
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                name = entry.name
                if "." not in name:
                    continue
                ext = name.rsplit(".", 1)[-1].lower()
                if ext in RAW_EXTENSIONS:
                    out.append(Path(entry.path))
    except OSError:
        pass
    return out


def _stems_with_jpg_extensions(dir_path: Path) -> set[str]:
    """Lowercase stems of files in dir_path whose extension is JPG/JPEG."""
    stems: set[str] = set()
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                name = entry.name
                if "." not in name:
                    continue
                ext = name.rsplit(".", 1)[-1].lower()
                if ext in JPG_EXTENSIONS:
                    stems.add(name[: -len(ext) - 1].lower())
    except OSError:
        pass
    return stems


def find_orphan_jpgs(raw_root: Path, jpg_root: Path) -> list[Path]:
    """
    Walk jpg_root recursively. In each directory, a JPG is an orphan if no file
    in that same directory has the same basename (case-insensitive) and a RAW extension.
    RAW files are only scanned under raw_root (same walk pattern: every directory
    visited under jpg_root must exist conceptually under raw_root for pairing).

    Actually: user selects raw_root and jpg_root. For each directory D relative to
    jpg_root, we look at raw_dir = raw_root / rel where rel is path of D relative to jpg_root.
    If raw_dir doesn't exist, treat as no RAW stems in that folder (all JPGs there are orphans).

    This matches the case where RAW and JPG trees are parallel (same structure).
    """
    raw_root = raw_root.resolve()
    jpg_root = jpg_root.resolve()
    orphans: list[Path] = []

    for dirpath, _dirnames, _filenames in os.walk(jpg_root):
        jpg_dir = Path(dirpath)
        try:
            rel = jpg_dir.relative_to(jpg_root)
        except ValueError:
            continue
        raw_dir = raw_root / rel
        raw_stems = _stems_with_raw_extensions(raw_dir)

        for jpg_path in _jpg_files_in_dir(jpg_dir):
            stem = jpg_path.stem.lower()
            if stem not in raw_stems:
                orphans.append(jpg_path)

    orphans.sort(key=lambda p: str(p).lower())
    return orphans


def find_orphan_raws(raw_root: Path, jpg_root: Path) -> list[Path]:
    """
    Walk raw_root recursively. In each directory, a RAW is an orphan if no file
    in the parallel JPG directory (jpg_root / rel) has the same basename
    (case-insensitive) and a JPG/JPEG extension. If jpg_dir does not exist,
    treat as no JPG stems (all RAWs in that folder are orphans).
    """
    raw_root = raw_root.resolve()
    jpg_root = jpg_root.resolve()
    orphans: list[Path] = []

    for dirpath, _dirnames, _filenames in os.walk(raw_root):
        raw_dir = Path(dirpath)
        try:
            rel = raw_dir.relative_to(raw_root)
        except ValueError:
            continue
        jpg_dir = jpg_root / rel
        jpg_stems = _stems_with_jpg_extensions(jpg_dir)

        for raw_path in _raw_files_in_dir(raw_dir):
            stem = raw_path.stem.lower()
            if stem not in jpg_stems:
                orphans.append(raw_path)

    orphans.sort(key=lambda p: str(p).lower())
    return orphans


def delete_files(paths: list[Path]) -> tuple[int, list[str]]:
    """Move files to the system trash (Recycle Bin on Windows). Returns (success_count, error_messages)."""
    from send2trash import send2trash

    errors: list[str] = []
    ok = 0
    for p in paths:
        try:
            send2trash(str(p.resolve()))
            ok += 1
        except Exception as e:
            errors.append(f"{p}: {e}")
    return ok, errors
