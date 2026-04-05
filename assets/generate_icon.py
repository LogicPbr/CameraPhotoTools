"""
Write CameraPhotoTools.ico. Prefers Pillow (multi-resolution); falls back to stdlib PNG-in-ICO.
Run: python assets/generate_icon.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

OUT_ICO = Path(__file__).resolve().parent / "CameraPhotoTools.ico"
ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

# Slate / cyan / indigo — lens + RAW/JPG stacks (same palette as SVG)
BG = (15, 23, 42, 255)
FACE = (30, 41, 59, 255)
ACCENT = (56, 189, 248, 255)
RING = (125, 211, 252, 255)
LENS = (99, 102, 241, 255)
STACK_A = (99, 102, 241, 220)
STACK_B = (244, 114, 182, 200)


def _render_rgba(size: int) -> bytes:
    """Top-down RGBA row-major bytes for PNG."""
    w = h = size
    buf = bytearray(w * h * 4)

    def put(x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        if 0 <= x < w and 0 <= y < h:
            i = (y * w + x) * 4
            buf[i : i + 4] = bytes(rgba)

    m = max(1, int(size * 0.055))
    r_card = int(size * 0.21)
    inner = m + max(1, size // 48)
    r_inner = max(1, r_card - 2)

    def in_round_rect(px: int, py: int, x0: int, y0: int, x1: int, y1: int, r: int) -> bool:
        if px < x0 or px >= x1 or py < y0 or py >= y1:
            return False
        if px < x0 + r and py < y0 + r:
            return (px - (x0 + r)) ** 2 + (py - (y0 + r)) ** 2 <= r * r
        if px >= x1 - r and py < y0 + r:
            return (px - (x1 - r - 1)) ** 2 + (py - (y0 + r)) ** 2 <= r * r
        if px < x0 + r and py >= y1 - r:
            return (px - (x0 + r)) ** 2 + (py - (y1 - r - 1)) ** 2 <= r * r
        if px >= x1 - r and py >= y1 - r:
            return (px - (x1 - r - 1)) ** 2 + (py - (y1 - r - 1)) ** 2 <= r * r
        return True

    for y in range(h):
        for x in range(w):
            if in_round_rect(x, y, m, m, size - m, size - m, r_card):
                put(x, y, BG)
            if in_round_rect(x, y, inner, inner, size - inner, size - inner, r_inner):
                put(x, y, FACE)

    cx, cy = w // 2, int(h * 0.46)
    ro = max(3, int(size * 0.26))
    ri = max(2, int(size * 0.14))
    for y in range(h):
        for x in range(w):
            dx, dy = x - cx, y - cy
            d2 = dx * dx + dy * dy
            if d2 <= ri * ri:
                put(x, y, LENS)
            elif d2 <= ro * ro:
                put(x, y, RING)

    if size >= 24:
        hx, hy = cx - ri // 2, cy - ri // 2 - max(1, size // 32)
        for y in range(h):
            for x in range(w):
                if (x - hx) ** 2 / max(1, (ri // 4) ** 2) + (y - hy) ** 2 / max(1, (ri // 5) ** 2) <= 1:
                    put(x, y, (255, 255, 255, 100))

    if size >= 48:
        bx = int(size * 0.58)
        by = int(size * 0.58)
        rw, rh = int(size * 0.22), int(size * 0.16)
        rr = max(2, size // 32)
        for y in range(by, by + rh):
            for x in range(bx, bx + rw):
                if in_round_rect(x, y, bx, by, bx + rw, by + rh, rr):
                    put(x, y, STACK_A)
        bx2, by2 = bx + rw // 5, by - rh // 4
        for y in range(by2, by2 + rh):
            for x in range(bx2, bx2 + rw):
                if in_round_rect(x, y, bx2, by2, bx2 + rw, by2 + rh, rr):
                    put(x, y, STACK_B)

    return bytes(buf)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _build_png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"".join(
        b"\x00" + rgba[y * width * 4 : (y + 1) * width * 4] for y in range(height)
    )
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 9)) + _png_chunk(b"IEND", b"")


def _build_ico_png_embed(png: bytes, w: int, h: int) -> bytes:
    wb = 0 if w >= 256 else w
    hb = 0 if h >= 256 else h
    header = struct.pack("<HHH", 0, 1, 1)
    # PNG payload: planes and bitcount must be 0 per ICO spec
    entry = struct.pack("<BBBBHHII", wb, hb, 0, 0, 0, 0, len(png), 6 + 16)
    return header + entry + png


def _write_with_pillow() -> None:
    from PIL import Image, ImageDraw

    def draw_icon(size: int) -> Image.Image:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        m = max(1, int(size * 0.055))
        r_card = int(size * 0.21)
        d.rounded_rectangle([m, m, size - m, size - m], radius=r_card, fill=BG)
        inner = m + max(1, size // 48)
        d.rounded_rectangle(
            [inner, inner, size - inner, size - inner],
            radius=max(1, r_card - 2),
            fill=FACE,
            outline=ACCENT,
            width=max(1, size // 64),
        )
        cx, cy = size // 2, int(size * 0.46)
        ro = max(3, int(size * 0.26))
        ri = max(2, int(size * 0.14))
        d.ellipse(
            [cx - ro, cy - ro, cx + ro, cy + ro],
            outline=RING,
            width=max(1, size // 48),
        )
        d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=LENS)
        if size >= 24:
            hx, hy = cx - ri // 2, cy - ri // 2 - max(1, size // 32)
            d.ellipse(
                [hx - ri // 4, hy - ri // 5, hx + ri // 5, hy + ri // 6],
                fill=(255, 255, 255, 100),
            )
        if size >= 48:
            bx = int(size * 0.58)
            by = int(size * 0.58)
            rw, rh = int(size * 0.22), int(size * 0.16)
            rr = max(2, size // 32)
            d.rounded_rectangle([bx, by, bx + rw, by + rh], radius=rr, fill=STACK_A)
            d.rounded_rectangle(
                [bx + rw // 5, by - rh // 4, bx + rw + rw // 5, by + rh - rh // 4],
                radius=rr,
                fill=STACK_B,
            )
        return img

    master = draw_icon(256)
    master.save(OUT_ICO, format="ICO", sizes=ICO_SIZES)


def _write_stdlib_fallback() -> None:
    rgba = _render_rgba(256)
    png = _build_png_rgba(256, 256, rgba)
    OUT_ICO.write_bytes(_build_ico_png_embed(png, 256, 256))


def main() -> None:
    try:
        _write_with_pillow()
        print(f"Wrote {OUT_ICO} (Pillow, multi-size)")
    except ImportError:
        _write_stdlib_fallback()
        print(f"Wrote {OUT_ICO} (stdlib PNG-in-ICO, no Pillow)")
    except Exception as e:
        print(f"Pillow failed ({e!r}); using stdlib fallback.")
        _write_stdlib_fallback()
        print(f"Wrote {OUT_ICO} (stdlib PNG-in-ICO)")


if __name__ == "__main__":
    main()
