"""
Rename JPG/JPEG files in a single folder by regex replace on the filename (non-recursive).

Mirrors: Get-ChildItem *.jpg | ForEach-Object { Rename-Item after $_.Name -replace pattern, repl }
PowerShell uses regex; replacement uses Python rules (e.g. \\1 for groups, not $1).
"""
from __future__ import annotations

import re
from pathlib import Path

_JPG_SUFFIX = frozenset({".jpg", ".jpeg"})
_WIN_BAD = '<>:"/\\|?*\x00'


def plan_jpg_renames(
    target: Path,
    pattern: str,
    replacement: str,
) -> tuple[list[tuple[Path, str]], list[str]]:
    """
    Build rename plan for .jpg/.jpeg directly under target (not subfolders).
    Returns (list of (path, new_filename), error messages). Empty plan if fatal error.
    """
    errors: list[str] = []
    if not pattern.strip():
        return [], ["查找词不能为空。"]

    try:
        rx = re.compile(pattern)
    except re.error as e:
        return [], [f"查找词不是合法的正则表达式：{e}"]

    target = target.resolve()
    if not target.is_dir():
        return [], [f"目标目录不存在或不是文件夹：{target}"]

    plans: list[tuple[Path, str]] = []
    try:
        entries = sorted(target.iterdir(), key=lambda p: p.name.lower())
    except OSError as e:
        return [], [str(e)]

    for p in entries:
        if not p.is_file():
            continue
        if p.suffix.lower() not in _JPG_SUFFIX:
            continue
        old = p.name
        new = rx.sub(replacement, old)
        if new == old:
            continue
        if not new.strip():
            errors.append(f"{old}：替换结果为空，已跳过。")
            continue
        if any(c in new for c in _WIN_BAD):
            errors.append(f"{old}：新文件名含非法字符，已跳过：{new!r}")
            continue
        plans.append((p, new))

    lowered = [n.lower() for _, n in plans]
    if len(lowered) != len(set(lowered)):
        return [], ["多个文件将重命名为同一名字（忽略大小写），请调整查找/替换规则。"]

    sources = {p.resolve() for p, _ in plans}
    for p, new in plans:
        dest = p.with_name(new)
        if dest.exists() and dest.resolve() != p.resolve():
            if dest.resolve() not in sources:
                return [], [f"目标已存在其他文件：{new}（与 {p.name} 冲突）。"]

    if errors and not plans:
        return [], errors
    return plans, errors


def apply_jpg_renames(plans: list[tuple[Path, str]]) -> tuple[int, list[str]]:
    """Execute renames. Returns (success_count, error messages)."""
    ok = 0
    errs: list[str] = []
    for p, new_name in plans:
        dest = p.with_name(new_name)
        try:
            p.rename(dest)
            ok += 1
        except OSError as e:
            errs.append(f"{p}: {e}")
    return ok, errs
