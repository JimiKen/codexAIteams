from __future__ import annotations

import struct
from pathlib import Path


def _pixel(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    # Dark background with slight radial lift toward center.
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    dx = x - cx
    dy = y - cy
    dist = (dx * dx + dy * dy) ** 0.5
    t = max(0.0, min(1.0, 1.0 - dist / (size * 0.75)))

    r = int(14 + 22 * t)
    g = int(18 + 38 * t)
    b = int(22 + 48 * t)
    a = 255

    # Cyan ring.
    ring_r = size * 0.34
    ring_thickness = 2.2
    if abs(dist - ring_r) <= ring_thickness:
        r, g, b = 0, 204, 153

    # "C" shape cut on right to hint Codex.
    if abs(dist - ring_r) <= ring_thickness + 0.5 and x > int(size * 0.64):
        r, g, b = int(r * 0.5), int(g * 0.5), int(b * 0.5)

    # Center square for "AI Teams" feel.
    if size * 0.43 <= x <= size * 0.57 and size * 0.43 <= y <= size * 0.57:
        r, g, b = 46, 173, 255

    return r, g, b, a


def generate_icon(out_path: Path, size: int = 32) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Bottom-up BGRA for BMP/DIB in ICO payload.
    pixels = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            r, g, b, a = _pixel(x, y, size)
            pixels.extend((b, g, r, a))

    # 1-bit AND mask, fully opaque (all zero bits).
    mask_row_size = ((size + 31) // 32) * 4
    and_mask = bytes(mask_row_size * size)

    bi_size = 40
    bi_width = size
    bi_height = size * 2
    bi_planes = 1
    bi_bit_count = 32
    bi_compression = 0
    bi_size_image = len(pixels)
    bi_xppm = 0
    bi_yppm = 0
    bi_clr_used = 0
    bi_clr_important = 0

    bmp_header = struct.pack(
        "<IIIHHIIIIII",
        bi_size,
        bi_width,
        bi_height,
        bi_planes,
        bi_bit_count,
        bi_compression,
        bi_size_image,
        bi_xppm,
        bi_yppm,
        bi_clr_used,
        bi_clr_important,
    )

    image_data = bmp_header + pixels + and_mask

    # ICO header + single image directory.
    icon_dir = struct.pack("<HHH", 0, 1, 1)
    icon_entry = struct.pack(
        "<BBBBHHII",
        size if size < 256 else 0,
        size if size < 256 else 0,
        0,
        0,
        1,
        32,
        len(image_data),
        6 + 16,
    )

    out_path.write_bytes(icon_dir + icon_entry + image_data)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    generate_icon(project_root / "assets" / "app.ico")
