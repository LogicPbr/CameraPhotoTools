"""
For each JPG in a folder (non-recursive, natural-sorted filename): composite by polar
angle — each frame fills one angular sector from the image geometric center (diagonals'
intersection; pixel ((W-1)/2, (H-1)/2) after aligning to reference size).

Same spatial pixel coords sample that frame (time-lapse "pie slice").
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from jpg_slice_concat import (
    _imread_bgr,
    _imwrite_bgr,
    _resize_to_match,
    _resolve_output_path,
    list_sorted_jpgs,
)


def build_radial_stitched_image(
    folder: Path,
    start_angle_deg: float = 0.0,
) -> tuple[np.ndarray | None, str | None]:
    """
    Apex fixed at geometric center ((w0-1)/2, (h0-1)/2) after resize.

    Frame k spans [start + k*360/n, start + (k+1)*360/n) modulo 360;
    Angle convention: 0° at top (-Y), increases clockwise (right 90°, down 180°, left 270°).
    """
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

    cx, cy = (w0 - 1) / 2.0, (h0 - 1) / 2.0

    stack = np.stack(normed, axis=0)
    n_ch = stack.shape[3]

    ys, xs = np.indices((h0, w0))
    dx = xs.astype(np.float64) - cx
    dy = ys.astype(np.float64) - cy
    # 0° = upward (-Y), angles increase clockwise on screen (matches "from top, sweep 360°").
    theta = np.degrees(np.arctan2(dx, -dy), dtype=np.float64)
    theta = np.mod(theta + 360.0, 360.0)

    start = float(np.mod(start_angle_deg, 360.0))
    rel = np.mod(theta - start + 360.0, 360.0)
    rel = np.minimum(rel, np.nextafter(360.0, 0.0))

    step_deg = 360.0 / float(n)
    k = np.floor(rel / step_deg).astype(np.int64)
    k = np.clip(k, 0, n - 1)

    kind = np.broadcast_to(k[np.newaxis, :, :, np.newaxis], (1, h0, w0, n_ch))
    out = np.take_along_axis(stack, kind, axis=0)[0]
    return np.ascontiguousarray(out), None


def write_final_image(
    folder: Path,
    output_dir: Path | None = None,
    output_name: str | None = None,
    *,
    start_angle_deg: float = 0.0,
) -> tuple[Path | None, str | None]:
    img, err = build_radial_stitched_image(folder, start_angle_deg=start_angle_deg)
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
    *,
    start_angle_deg: float = 0.0,
) -> tuple[list[str], str | None]:
    paths = list_sorted_jpgs(folder)
    if not paths:
        return [], "文件夹内没有 JPG/JPEG 文件。"
    img0 = _imread_bgr(paths[0])
    if img0 is None:
        return [], f"无法读取图片：\n{paths[0]}"
    h0, w0 = img0.shape[:2]
    n = len(paths)
    wedge = 360.0 / n
    cx_f, cy_f = (w0 - 1) / 2.0, (h0 - 1) / 2.0

    lines = [
        f"共 {n} 个文件（文件名自然排序，仅当前文件夹）：",
        f"圆心：固定为首张对齐后对角线中心（几何中心），约 ({cx_f:.1f}, {cy_f:.1f}) px",
        f"起始角：{start_angle_deg:g}°（正上为 0°，顺时针增大：右 90°、下 180°、左 270°）",
        (
            f"每张占 {wedge:g}°；第 k 张取角度 "
            f"[起始角 + k·{wedge:g}°, 起始角 + (k+1)·{wedge:g}°)（对 360° 取模）。"
        ),
        "（竖条拼接按列 x 切矩形条；径向按相对上述圆心的方位角切扇形。）",
        "",
    ]
    for p in paths:
        lines.append(p.name)
    lines.append("")
    lines.append(f"输出文件将保存为：{_resolve_output_path(folder, output_dir, output_name)}")
    return lines, None
