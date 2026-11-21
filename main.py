#!/usr/bin/env python3
"""LUMARA — a travel poster for a place that does not exist.

Entry program for make.fun bounty the-poster-for-a-place-that-i-2-20261121-0539.
Writes one image to /output/entry.png (or $OUTPUT_PATH).

How it works (stdlib only, no network, fully deterministic):
  1. Loads scene.png — a flat vector-style poster scene painted fresh in the
     build session (golden-hour sun, turquoise sea, one lighthouse on a rocky
     island, birds). The scene carries no text at all.
  2. Resamples it to 1024x1024 with bilinear interpolation.
  3. Paints a deep-teal band across the top and renders the fictional place
     name "LUMARA" in it with a procedural geometric stroke font (no font
     files, no system fonts — every glyph is a list of line segments drawn
     by this program).
  4. Encodes a PNG (RGB, 8-bit) and writes it out.

Only the place name appears as text — no quotes, no ratings, no other copy.
No randomness, no clock, no environment-dependent input: two runs produce
byte-identical output.
"""

import math
import os
import struct
import sys
import zlib

W = H = 1024
BAND_H = 168                    # height of the top name band (px)
BAND = (13, 55, 66)             # deep teal
CREAM = (255, 243, 214)         # warm cream for the name
RULE_H = 3                      # divider rule under the band (px)

PLACE_NAME = "LUMARA"

# --- procedural stroke font -------------------------------------------------
# One glyph = list of segments on a 100 (wide) x 140 (tall) grid, y down.
# Only the letters of the place name are defined.
GLYPHS = {
    "L": [((8, 0), (8, 140)), ((8, 140), (92, 140))],
    "U": [((8, 0), (8, 112)), ((92, 0), (92, 112)),
          ((8, 112), (28, 140)), ((28, 140), (72, 140)),
          ((72, 140), (92, 112))],
    "M": [((8, 140), (8, 0)), ((8, 0), (50, 78)),
          ((50, 78), (92, 0)), ((92, 0), (92, 140))],
    "A": [((8, 140), (50, 0)), ((50, 0), (92, 140)),
          ((26, 96), (74, 96))],
    "R": [((8, 0), (8, 140)), ((8, 0), (64, 0)),
          ((64, 0), (86, 18)), ((86, 18), (86, 42)),
          ((86, 42), (64, 60)), ((64, 60), (8, 60)),
          ((46, 60), (92, 140))],
}
GLYPH_SCALE = 0.86              # grid units -> pixels
GLYPH_ADVANCE = 120             # px between letter origins
STROKE_R = 9                    # pen radius (px)


def _stamp_circle(buf, cx, cy, r, color):
    """Fill a disc of radius r centred at (cx, cy) into the RGB bytearray."""
    x0 = max(0, cx - r)
    x1 = min(W - 1, cx + r)
    y0 = max(0, cy - r)
    y1 = min(H - 1, cy + r)
    r2 = r * r
    cr, cg, cb = color
    for y in range(y0, y1 + 1):
        dy = y - cy
        dx = math.isqrt(max(0, r2 - dy * dy))
        row = y * W * 3
        xa = max(0, cx - dx)
        xb = min(W - 1, cx + dx)
        i = row + xa * 3
        for x in range(xa, xb + 1):
            buf[i] = cr
            buf[i + 1] = cg
            buf[i + 2] = cb
            i += 3


def draw_text(buf, text, x0, y0):
    """Render text with the stroke font; (x0, y0) is the top-left origin."""
    for k, ch in enumerate(text):
        segs = GLYPHS[ch]
        ox = x0 + k * GLYPH_ADVANCE
        for (x1, y1), (x2, y2) in segs:
            ax = ox + x1 * GLYPH_SCALE
            ay = y0 + y1 * GLYPH_SCALE
            bx = ox + x2 * GLYPH_SCALE
            by = y0 + y2 * GLYPH_SCALE
            length = math.hypot(bx - ax, by - ay)
            steps = max(1, int(length / 4.0) + 1)
            for s in range(steps + 1):
                t = s / steps
                _stamp_circle(buf, int(round(ax + (bx - ax) * t)),
                              int(round(ay + (by - ay) * t)), STROKE_R, CREAM)


# --- minimal PNG reader (8-bit, non-interlaced, colour types 2 and 6) -------
def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    pos = 8
    idat = bytearray()
    width = height = bitdepth = colortype = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, bitdepth, colortype, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk)
            if bitdepth != 8 or interlace != 0 or colortype not in (2, 6):
                raise ValueError("unsupported PNG: depth=%d type=%d interlace=%d"
                                 % (bitdepth, colortype, interlace))
        elif ctype == b"IDAT":
            idat += chunk
        elif ctype == b"IEND":
            break
        pos += 12 + length
    channels = 3 if colortype == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(width * height * 3)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        f = raw[p]
        p += 1
        row = bytearray(raw[p:p + stride])
        p += stride
        if f == 1:
            for i in range(channels, stride):
                row[i] = (row[i] + row[i - channels]) & 0xFF
        elif f == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                row[i] = (row[i] + _paeth(a, b, c)) & 0xFF
        elif f != 0:
            raise ValueError("unknown PNG filter %d" % f)
        for x in range(width):
            o = (y * width + x) * 3
            s = x * channels
            out[o] = row[s]
            out[o + 1] = row[s + 1]
            out[o + 2] = row[s + 2]
        prev = row
    return width, height, out


# --- resample (bilinear, deterministic) --------------------------------------
def resample_bilinear(src_w, src_h, src, dst_w, dst_h):
    dst = bytearray(dst_w * dst_h * 3)
    # Precompute per-column source positions and weights.
    col = []
    for dx in range(dst_w):
        sx = (dx + 0.5) * src_w / dst_w - 0.5
        x0 = int(math.floor(sx))
        x0 = max(0, min(src_w - 2, x0))
        fx = sx - x0
        col.append((x0, fx))
    for dy in range(dst_h):
        sy = (dy + 0.5) * src_h / dst_h - 0.5
        y0 = int(math.floor(sy))
        y0 = max(0, min(src_h - 2, y0))
        fy = sy - y0
        r0 = y0 * src_w * 3
        r1 = (y0 + 1) * src_w * 3
        out_row = dy * dst_w * 3
        for dx in range(dst_w):
            x0, fx = col[dx]
            i00 = r0 + x0 * 3
            i10 = i00 + 3
            i01 = r1 + x0 * 3
            i11 = i01 + 3
            w00 = (1 - fx) * (1 - fy)
            w10 = fx * (1 - fy)
            w01 = (1 - fx) * fy
            w11 = fx * fy
            o = out_row + dx * 3
            dst[o] = int(src[i00] * w00 + src[i10] * w10 +
                         src[i01] * w01 + src[i11] * w11 + 0.5)
            dst[o + 1] = int(src[i00 + 1] * w00 + src[i10 + 1] * w10 +
                             src[i01 + 1] * w01 + src[i11 + 1] * w11 + 0.5)
            dst[o + 2] = int(src[i00 + 2] * w00 + src[i10 + 2] * w10 +
                             src[i01 + 2] * w01 + src[i11 + 2] * w11 + 0.5)
    return dst


# --- minimal PNG writer (RGB 8-bit; per-row filter None vs Up) ---------------
_ABS = bytes((b if b < 128 else 256 - b) for b in range(256))
_ABS_TABLE = bytes.maketrans(bytes(range(256)), _ABS)


def _row_score(raw_row):
    return sum(raw_row.translate(_ABS_TABLE))


def write_png(path, width, height, rgb):
    stride = width * 3
    raw = bytearray()
    prev = bytes(stride)
    for y in range(height):
        row = bytes(rgb[y * stride:(y + 1) * stride])
        up = bytes((row[i] - prev[i]) & 0xFF for i in range(stride))
        if y == 0 or _row_score(row) <= _row_score(up):
            raw.append(0)
            raw += row
            prev = row
        else:
            raw.append(2)
            raw += up
            prev = row
    comp = zlib.compress(bytes(raw), 9)

    def chunk(ctype, data):
        c = struct.pack(">I", len(data)) + ctype + data
        return c + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


# --- main --------------------------------------------------------------------
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    scene_path = os.path.join(here, "scene.png")
    sw, sh, scene = read_png(scene_path)
    buf = resample_bilinear(sw, sh, scene, W, H)

    # Top band + divider rule.
    for y in range(BAND_H):
        row = y * W * 3
        for x in range(W):
            i = row + x * 3
            buf[i] = BAND[0]
            buf[i + 1] = BAND[1]
            buf[i + 2] = BAND[2]
    for y in range(BAND_H, BAND_H + RULE_H):
        row = y * W * 3
        for x in range(W):
            i = row + x * 3
            buf[i] = CREAM[0]
            buf[i + 1] = CREAM[1]
            buf[i + 2] = CREAM[2]

    # Place name, centred in the band. Two small rules flank it.
    text_w = (len(PLACE_NAME) - 1) * GLYPH_ADVANCE + int(100 * GLYPH_SCALE)
    tx = (W - text_w) // 2
    ty = (BAND_H - int(140 * GLYPH_SCALE)) // 2
    draw_text(buf, PLACE_NAME, tx, ty)
    mid_y = BAND_H // 2
    for x in range(56, tx - 28):
        for dy in range(-2, 3):
            i = ((mid_y + dy) * W + x) * 3
            buf[i] = CREAM[0]
            buf[i + 1] = CREAM[1]
            buf[i + 2] = CREAM[2]
    for x in range(tx + text_w + 28, W - 56):
        for dy in range(-2, 3):
            i = ((mid_y + dy) * W + x) * 3
            buf[i] = CREAM[0]
            buf[i + 1] = CREAM[1]
            buf[i + 2] = CREAM[2]

    out_path = os.environ.get("OUTPUT_PATH", "/output/entry.png")
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    n = write_png(out_path, W, H, buf)
    print("wrote %s (%d bytes, %dx%d)" % (out_path, n, W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
