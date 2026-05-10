"""
For each JPG in a folder (non-recursive, natural-sorted filename): take one vertical slice
whose width is 1/n of the reference width, then concatenate slices left-to-right.
Matches the user's OpenCV workflow; supports Unicode paths on Windows via imdecode/imencode.
"""
from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np

# JPEG output: OpenCV's default quality is visibly lossy — use highest practical setting here.
_JPEG_WRITE_QUALITY = 100  # 1–100; 100 minimizes subsampling/block artifacts (still JPEG, larger files)


def _natural_sort_key(filename: str) -> tuple[int | str, ...]:
    """Filename order friendly to bursts (IMG_9 before IMG_10)."""

    parts: list[int | str] = []
    for t in re.split(r"(\d+)", filename):
        if t == "":
            continue
        if t.isdigit():
            parts.append(int(t))
        else:
            parts.append(t.casefold())
    return tuple(parts)


def list_sorted_jpgs(folder: Path) -> list[Path]:
    out: list[Path] = []
    try:
        for p in folder.iterdir():
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".jpg", ".jpeg"}:
                continue
            out.append(p)
    except OSError:
        return []
    out.sort(key=lambda p: _natural_sort_key(p.name))
    return out


def _imread_bgr(path: Path) -> np.ndarray | None:
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _imwrite_bgr(path: Path, img: np.ndarray) -> bool:
    ext = path.suffix.lower() if path.suffix else ".jpg"
    if ext not in {".jpg", ".jpeg", ".bmp", ".png"}:
        ext = ".jpg"

    encode_params: list[int] = []
    if ext in {".jpg", ".jpeg"}:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), _JPEG_WRITE_QUALITY]

    ok, buf = cv2.imencode(ext, img, encode_params)
    if not ok:
        return False
    try:
        buf.tofile(str(path))
    except OSError:
        return False
    return True


def _resize_to_match(img: np.ndarray, w0: int, h0: int) -> np.ndarray:
    """INTER_AREA when purely shrinking preserves detail; Lanczos when enlarging."""
    sh, sw = img.shape[:2]
    if sw == w0 and sh == h0:
        return img
    purely_shrink = sw >= w0 and sh >= h0
    interp = cv2.INTER_AREA if purely_shrink else cv2.INTER_LANCZOS4
    return cv2.resize(img, (w0, h0), interpolation=interp)


def _resolve_output_path(
    input_folder: Path,
    output_dir: Path | None,
    output_name: str | None,
) -> Path:
    out_dir = input_folder if output_dir is None else output_dir
    name = ((output_name or "").strip() or "final_image.jpg")
    name = Path(name).name or "final_image.jpg"
    return out_dir.resolve() / name


def build_stitched_image(folder: Path) -> tuple[np.ndarray | None, str | None]:
    paths = list_sorted_jpgs(folder)
    n = len(paths)
    if n == 0:
        return None, "文件夹内没有 JPG/JPEG 文件。"

    images: list[np.ndarray] = []
    for p in paths:
        img = _imread_bgr(p)
        if img is None:
            return None, f"无法读取图片：\n{p}"
        images.append(img)

    first = images[0]
    h0, w0 = first.shape[:2]
    normed: list[np.ndarray] = [first]
    for img in images[1:]:
        normed.append(_resize_to_match(img, w0, h0))

    strips: list[np.ndarray] = []
    for k, img in enumerate(normed):
        start_x = int((k / n) * w0)
        end_x = int(((k + 1) / n) * w0)
        if end_x <= start_x:
            return None, "图片宽度过小，无法按张数切分竖条。"
        strips.append(img[:, start_x:end_x])

    final = cv2.hconcat(strips)
    return final, None


def write_final_image(
    folder: Path,
    output_dir: Path | None = None,
    output_name: str | None = None,
) -> tuple[Path | None, str | None]:
    img, err = build_stitched_image(folder)
    if err or img is None:
        return None, err
    out = _resolve_output_path(folder, output_dir, output_name)
    if not _imwrite_bgr(out, img):
        return None, f"无法写入文件：\n{out}"
    return out, None


def preview_lines(
    folder: Path,
    output_dir: Path | None = None,
    output_name: str | None = None,
) -> tuple[list[str], str | None]:
    paths = list_sorted_jpgs(folder)
    if not paths:
        return [], "文件夹内没有 JPG/JPEG 文件。"
    lines = [
        f"共 {len(paths)} 个文件（文件名自然排序，仅当前文件夹）：",
        f"JPEG 输出质量系数：{_JPEG_WRITE_QUALITY}/100（仅影响保存，缩放见插值算法）。",
        "",
    ]
    for p in paths:
        lines.append(p.name)
    lines.append("")
    lines.append(f"输出文件将保存为：{_resolve_output_path(folder, output_dir, output_name)}")
    return lines, None
