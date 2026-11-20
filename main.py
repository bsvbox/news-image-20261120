#!/usr/bin/env python3
"""The World in One Page - 20 November 2026.

Draws a one-page newspaper front page summing up the world's news of
Friday 20 November 2026 as a 1024x1024 PNG, pixel by pixel, using only
the Python standard library. No network access, fully deterministic:
two runs write byte-identical files.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   (writes out/entry.png)
"""

import binascii
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 231)
NAVY = (22, 35, 63)
NAVY_DARK = (13, 22, 42)
GOLD = (217, 164, 65)
GOLD_LIGHT = (240, 196, 90)
WHITE = (255, 255, 255)
INK = (26, 26, 26)
GREY = (74, 68, 56)
BORDER = (201, 191, 169)
SKYLINE = (26, 26, 46)
RED_DARK = (122, 31, 31)
TEAL = (14, 90, 122)
GREEN = (30, 122, 52)
BURNT = (179, 84, 30)
PURPLE = (106, 31, 160)

# ---------------------------------------------------------------- canvas
canvas = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i] = color[0]
        canvas[i + 1] = color[1]
        canvas[i + 2] = color[2]


def fill_rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        canvas[i:i + len(row)] = row


def hline(x0, x1, y, color, thick=1):
    for t in range(thick):
        for x in range(x0, x1 + 1):
            set_px(x, y + t, color)


def vline(x, y0, y1, color, thick=1):
    for t in range(thick):
        for y in range(y0, y1 + 1):
            set_px(x + t, y, color)


def line(x0, y0, x1, y1, color, thick=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for a in range(thick):
            for b in range(thick):
                set_px(x + a, y + b, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def fill_circle(cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        for x in range(cx - dx, cx + dx + 1):
            set_px(x, cy + dy, color)


def circle_outline(cx, cy, r, color, thick=2):
    for a in range(360):
        rad = math.radians(a)
        for t in range(thick):
            set_px(int(cx + (r + t) * math.cos(rad)),
                   int(cy + (r + t) * math.sin(rad)), color)


def fill_triangle(x0, y0, x1, y1, x2, y2, color):
    ymin = min(y0, y1, y2)
    ymax = max(y0, y1, y2)
    for y in range(ymin, ymax + 1):
        xs = []
        for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2),
                                 (x2, y2, x0, y0)):
            if ay == by:
                continue
            if (y >= min(ay, by)) and (y < max(ay, by)):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        if len(xs) >= 2:
            for x in range(int(min(xs)), int(max(xs)) + 1):
                set_px(x, y, color)


def lerp(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, "1" = ink.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(x, y, text, scale, color):
    text = text.upper()
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(cx, y, text, scale, color):
    x = cx - text_width(text, scale) // 2
    draw_text(x, y, text, scale, color)


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns list of lines."""
    words = text.upper().split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- PNG writer
def chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", binascii.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += canvas[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- lead panel
def draw_flags():
    # Three small flags, top right of the sky: USA, China, Russia.
    fx, fy, fw, fh = 700, 122, 84, 30
    gap = 12
    # --- USA
    x = fx
    for s in range(7):
        fill_rect(x, fy + s * 4, fw, 4,
                  (178, 34, 52) if s % 2 == 0 else WHITE)
    fill_rect(x, fy, 34, 16, (60, 59, 110))
    for r in range(3):
        for c in range(4):
            fill_rect(x + 4 + c * 8, fy + 3 + r * 5, 2, 2, WHITE)
    # --- China
    x = fx + fw + gap
    fill_rect(x, fy, fw, fh, (222, 41, 16))
    fill_circle(x + 14, fy + 11, 5, GOLD_LIGHT)
    for sx, sy in ((34, 6), (42, 11), (40, 19), (32, 20)):
        fill_rect(x + sx, fy + sy, 3, 3, GOLD_LIGHT)
    # --- Russia
    x = fx + 2 * (fw + gap)
    fill_rect(x, fy, fw, 10, WHITE)
    fill_rect(x, fy + 10, fw, 10, (0, 57, 166))
    fill_rect(x, fy + 20, fw, 10, (213, 0, 50))


def draw_skyline():
    # Deterministic Shenzhen-style silhouette with lit windows.
    heights = [58, 84, 66, 96, 74, 110, 62, 88, 70, 102, 56, 92, 68, 78,
               104, 60, 86, 72, 98, 64, 80, 58, 90, 66]
    x = 8
    i = 0
    while x < W - 8 and i < len(heights):
        bw = 36 if i % 3 else 44
        bh = heights[i]
        top = 270 - bh
        fill_rect(x, top, bw, bh, SKYLINE)
        if i % 4 == 1:  # antenna
            vline(x + bw // 2, top - 14, top, SKYLINE, 3)
        for wy in range(top + 8, 266, 12):
            for wx in range(x + 5, x + bw - 5, 10):
                if (wx * 7 + wy * 13 + i * 5) % 4 == 0:
                    fill_rect(wx, wy, 3, 4, GOLD_LIGHT)
        x += bw + 4
        i += 1


def draw_lead():
    # Sunset sky gradient, orange -> red -> purple.
    top = (255, 154, 61)
    mid = (232, 74, 95)
    bot = (107, 58, 140)
    for y in range(108, 270):
        t = (y - 108) / 162.0
        if t < 0.5:
            c = lerp(top, mid, t * 2)
        else:
            c = lerp(mid, bot, (t - 0.5) * 2)
        fill_rect(0, y, W, 1, c)
    # Sun, low on the left.
    fill_circle(185, 205, 42, (255, 214, 90))
    fill_circle(185, 205, 32, (255, 232, 150))
    draw_flags()
    draw_skyline()
    # Navy ribbon with the lead headline.
    fill_rect(0, 270, W, 122, NAVY)
    fill_rect(0, 270, W, 3, GOLD)
    draw_text_centered(512, 284, "TRUMP, XI & PUTIN", 6, WHITE)
    draw_text_centered(512, 330, "MEET IN SHENZHEN", 6, GOLD)
    draw_text_centered(512, 374, "FIRST THREE-WAY SUMMIT ON NUCLEAR RISKS AND WAR",
                       2, (220, 220, 220))


# ---------------------------------------------------------------- card icons
def icon_scales(cx, top):
    # Scales of justice.
    c = NAVY
    vline(cx, top + 6, top + 78, c, 4)
    hline(cx - 52, cx + 52, top + 12, c, 4)
    fill_circle(cx, top + 6, 5, c)
    for s in (-1, 1):
        bx = cx + s * 52
        line(bx, top + 14, bx - 16, top + 44, c, 2)
        line(bx, top + 14, bx + 16, top + 44, c, 2)
        fill_triangle(bx - 18, top + 44, bx + 18, top + 44, bx, top + 62, c)
    hline(cx - 26, cx + 26, top + 80, c, 4)


def icon_cyclone(cx, top):
    c = TEAL
    for r, ox, oy in ((34, 0, 0), (25, 6, 4), (16, 10, 8), (8, 12, 12)):
        circle_outline(cx + ox, top + 36 + oy, r, c, 3)
    fill_circle(cx + 12, top + 48, 5, c)
    # Rain drops below the spiral.
    for dx in (-38, -12, 14, 38):
        fill_triangle(cx + dx - 5, top + 82, cx + dx + 5, top + 82,
                      cx + dx, top + 70, c)


def icon_chart(cx, top):
    c = GREEN
    bars = [26, 44, 62, 82]
    bx = cx - 58
    for h in bars:
        fill_rect(bx, top + 88 - h, 20, h, c)
        bx += 30
    line(cx - 62, top + 84, cx + 62, top + 6, (26, 26, 26), 4)
    fill_triangle(cx + 62, top + 6, cx + 40, top + 4, cx + 58, top + 24,
                  (26, 26, 26))


def icon_tanker(cx, top):
    c = BURNT
    # Hull and bow.
    fill_rect(cx - 62, top + 46, 104, 26, (40, 40, 40))
    fill_triangle(cx + 42, top + 46, cx + 70, top + 46, cx + 42, top + 72,
                  (40, 40, 40))
    fill_rect(cx - 52, top + 30, 18, 16, (40, 40, 40))
    fill_rect(cx - 30, top + 38, 60, 8, c)
    # Flame above the deck.
    fill_triangle(cx - 8, top + 30, cx + 12, top + 30, cx + 2, top + 2,
                  (255, 140, 0))
    fill_triangle(cx - 2, top + 30, cx + 8, top + 30, cx + 3, top + 14,
                  (255, 220, 60))
    # Waves.
    for wy in (top + 80, top + 90):
        for x in range(cx - 70, cx + 70, 14):
            line(x, wy, x + 7, wy - 5, TEAL, 3)
            line(x + 7, wy - 5, x + 14, wy, TEAL, 3)


def icon_controller(cx, top):
    c = PURPLE
    fill_rect(cx - 56, top + 18, 112, 44, c)
    fill_circle(cx - 56, top + 40, 22, c)
    fill_circle(cx + 56, top + 40, 22, c)
    fill_circle(cx - 34, top + 34, 7, WHITE)
    fill_circle(cx + 30, top + 28, 5, GOLD_LIGHT)
    fill_circle(cx + 42, top + 40, 5, WHITE)
    fill_circle(cx + 30, top + 50, 5, (255, 120, 120))
    draw_text_centered(cx, top + 66, "VI", 4, NAVY)


def icon_voyager(cx, top, x0, w):
    # Starfield panel with a deep-space probe.
    fill_rect(x0, top, w, 96, NAVY_DARK)
    for i in range(46):
        sx = x0 + 8 + (i * 53 + 17) % (w - 16)
        sy = top + 6 + (i * 37 + 11) % 84
        fill_rect(sx, sy, 2, 2, WHITE if i % 5 else GOLD_LIGHT)
    # Probe body, dish and antenna.
    fill_rect(cx - 8, top + 44, 34, 14, GOLD)
    fill_triangle(cx + 26, top + 38, cx + 26, top + 64, cx + 48, top + 51,
                  (200, 200, 210))
    line(cx - 8, top + 51, cx - 30, top + 62, GOLD_LIGHT, 3)
    fill_circle(cx - 32, top + 63, 4, GOLD_LIGHT)
    line(cx + 10, top + 44, cx + 22, top + 28, (200, 200, 210), 3)
    # No in-panel label: the headline below already says it, and text here
    # would collide with the antenna boom.


ICONS = {
    "scales": icon_scales,
    "cyclone": icon_cyclone,
    "chart": icon_chart,
    "tanker": icon_tanker,
    "controller": icon_controller,
}


def draw_card(x, y, accent, label, icon, headline, sub):
    w, h = 330, 280
    fill_rect(x, y, w, h, WHITE)
    # Border.
    hline(x, x + w - 1, y, BORDER, 2)
    hline(x, x + w - 1, y + h - 1, BORDER, 2)
    vline(x, y, y + h - 1, BORDER, 2)
    vline(x + w - 1, y, y + h - 1, BORDER, 2)
    # Accent label bar.
    fill_rect(x + 2, y + 2, w - 4, 22, accent)
    draw_text(x + 12, y + 7, label, 2, WHITE)
    # Icon.
    top = y + 30
    if icon == "voyager":
        icon_voyager(x + w // 2, top, x + 16, w - 32)
    else:
        ICONS[icon](x + w // 2, top)
    # Headline, up to two lines, scale 3.
    lines = wrap_text(headline, 3, w - 24)
    hy = y + 140
    for ln in lines[:2]:
        draw_text(x + 12, hy, ln, 3, INK)
        hy += 26
    # Sub-headline, up to two lines, scale 2.
    sub_lines = wrap_text(sub, 2, w - 24)
    sy = y + 196
    for ln in sub_lines[:2]:
        draw_text(x + 12, sy, ln, 2, GREY)
        sy += 17


# ---------------------------------------------------------------- page
def draw_page():
    fill_rect(0, 0, W, H, PAPER)
    # Masthead.
    fill_rect(0, 0, W, 104, NAVY)
    draw_text_centered(512, 20, "THE WORLD IN ONE PAGE", 5, WHITE)
    draw_text_centered(512, 64, "FRIDAY 20 NOVEMBER 2026", 3, GOLD)
    fill_rect(0, 104, W, 4, GOLD)
    draw_lead()
    # Six story cards, 2 rows x 3 columns.
    cards = [
        (RED_DARK, "WORLD", "scales",
         "MYANMAR GUILTY OF GENOCIDE",
         "UN COURT RULES ON THE ROHINGYA"),
        (TEAL, "INDIA", "cyclone",
         "CYCLONE AKVAN SLAMS INDIA",
         "ODISHA LANDFALL, MASS EVACUATIONS"),
        (GREEN, "MARKETS", "chart",
         "ANTHROPIC DEBUTS AT $1.5T",
         "AMONG THE WORLD'S MOST VALUABLE FIRMS"),
        (BURNT, "ENERGY", "tanker",
         "TANKER BURNS IN THE GULF",
         "MINE STRIKE EAST OF THE STRAIT OF HORMUZ"),
        (PURPLE, "GAMES", "controller",
         "GTA VI IS FINALLY OUT",
         "GAMERS QUEUE AS LAUNCH DAY ARRIVES"),
        (NAVY, "SPACE", "voyager",
         "VOYAGER 1 REACHES ONE LIGHT-DAY OUT",
         "ITS SIGNAL FALLS SILENT AT THE EDGE"),
    ]
    xs = (8, 346, 684)
    ys = (400, 688)
    for i, (accent, label, icon, headline, sub) in enumerate(cards):
        draw_card(xs[i % 3], ys[i // 3], accent, label, icon, headline, sub)
    # Also-today strip.
    fill_rect(8, 974, 1008, 22, NAVY)
    draw_text(16, 979, "ALSO TODAY: RUSSIAN STRIKES DAMAGE AUSTRIAN AND DUTCH EMBASSIES IN KYIV",
              2, WHITE)
    # Footer.
    draw_text_centered(512, 1004,
                       "COMPILED FROM BBC, REUTERS, AP AND TIMES OF INDIA - 20 NOVEMBER 2026",
                       2, GREY)


def main():
    draw_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} {W}x{H} {size} bytes")


if __name__ == "__main__":
    main()
