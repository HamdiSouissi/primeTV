#!/usr/bin/env python3
"""Génère les icônes PNG de la PWA PrimeTV (aucune dépendance externe).

Le script dessine, pixel par pixel, le logo de PrimeTV — un écran arrondi avec
un triangle « play » sur un dégradé indigo → violet — puis encode les images en
PNG (RGBA 8 bits) via `zlib`. Il produit :

    public/icons/icon-192.png          icône standard 192×192
    public/icons/icon-512.png          icône standard 512×512
    public/icons/maskable-512.png      icône « maskable » (zone sûre Android)
    public/icons/apple-touch-icon.png  icône iOS 180×180
    public/favicon.png                 favicon 32×32

Usage :
    python3 scripts/generate-icons.py
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "public"

# Couleurs de la charte (équivalent Tailwind brand-600 → accent-500)
BRAND = (79, 70, 229)     # #4f46e5
ACCENT = (168, 85, 247)   # #a855f7
NIGHT = (8, 12, 24)       # #080c18
WHITE = (255, 255, 255)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _rounded_rect_coverage(x: float, y: float, x0: float, y0: float, x1: float, y1: float, r: float) -> float:
    """Couverture anti-crénelée (0..1) d'un point dans un rectangle arrondi."""
    # Distance signée au rectangle arrondi centré
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    dx, dy = abs(x - cx) - hw, abs(y - cy) - hh
    outside = math.hypot(max(dx, 0.0), max(dy, 0.0))
    inside = min(max(dx, dy), 0.0)
    dist = outside + inside - r
    return min(max(0.5 - dist, 0.0), 1.0)


def _in_triangle(x: float, y: float, ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    def sign(px, py, qx, qy, rx, ry):
        return (px - rx) * (qy - ry) - (qx - rx) * (py - ry)

    d1 = sign(x, y, ax, ay, bx, by)
    d2 = sign(x, y, bx, by, cx, cy)
    d3 = sign(x, y, cx, cy, ax, ay)
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def render(size: int, *, maskable: bool = False) -> bytes:
    """Rend une icône RGBA de `size`×`size` et renvoie son PNG encodé."""
    # Zone sûre : pour l'icône maskable, le glyphe occupe 60 % du canevas.
    glyph_scale = 0.60 if maskable else 0.80
    cx = cy = size / 2

    screen_half_w = size * glyph_scale * 0.42
    screen_half_h = size * glyph_scale * 0.30
    radius = size * glyph_scale * 0.12
    bezel = max(2.0, size * 0.028)

    raw = bytearray()
    for y in range(size):
        raw.append(0)  # filtre PNG « None »
        py = y + 0.5
        for x in range(size):
            px = x + 0.5
            # Fond dégradé diagonal (du coin haut-gauche au coin bas-droit)
            t = min(max(((px / size) * 0.55 + (py / size) * 0.45), 0.0), 1.0)
            bg = _mix(BRAND, ACCENT, t)
            if not maskable:
                # Coins arrondis pour l'icône standard (iOS/desktop)
                cover = _rounded_rect_coverage(px, py, 0, 0, size, size, size * 0.22)
                bg = _mix(NIGHT, bg, cover)

            r, g, b = bg

            # Écran : bordure blanche + intérieur translucide
            outer = _rounded_rect_coverage(
                px, py, cx - screen_half_w, cy - screen_half_h, cx + screen_half_w, cy + screen_half_h, radius
            )
            inner = _rounded_rect_coverage(
                px,
                py,
                cx - screen_half_w + bezel,
                cy - screen_half_h + bezel,
                cx + screen_half_w - bezel,
                cy + screen_half_h - bezel,
                max(2.0, radius - bezel),
            )
            if outer > 0:
                r, g, b = (int(_lerp(r, WHITE[0], outer)), int(_lerp(g, WHITE[1], outer)), int(_lerp(b, WHITE[2], outer)))
            if inner > 0:
                r, g, b = (int(_lerp(r, NIGHT[0], inner * 0.85)), int(_lerp(g, NIGHT[1], inner * 0.85)), int(_lerp(b, NIGHT[2], inner * 0.85)))

            # Triangle « play » centré dans l'écran
            tri_w = screen_half_w * 0.42
            tri_h = screen_half_h * 0.62
            if _in_triangle(px, py, cx - tri_w * 0.55, cy - tri_h, cx - tri_w * 0.55, cy + tri_h, cx + tri_w * 1.1, cy):
                r, g, b = WHITE

            raw.extend((int(r), int(g), int(b), 255))
    return _png(size, size, bytes(raw))


def _png(width: int, height: int, raw: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", header),
            chunk(b"IDAT", zlib.compress(raw, 9)),
            chunk(b"IEND", b""),
        ]
    )


def main() -> None:
    icons = PUBLIC / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    targets = [
        (icons / "icon-192.png", 192, False),
        (icons / "icon-512.png", 512, False),
        (icons / "maskable-512.png", 512, True),
        (icons / "apple-touch-icon.png", 180, False),
        (PUBLIC / "favicon.png", 32, False),
    ]
    for path, size, maskable in targets:
        path.write_bytes(render(size, maskable=maskable))
        print(f"✓ {path.relative_to(PUBLIC.parent)} ({size}×{size}, {path.stat().st_size} octets)")


if __name__ == "__main__":
    main()
