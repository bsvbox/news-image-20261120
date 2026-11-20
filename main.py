#!/usr/bin/env python3
"""The World in One Page - 20 November 2026.

Draws a one-page newspaper front page summing up the world's news of
Friday 20 November 2026 as a 1024x1024 PNG, pixel by pixel, using only
the Python standard library. No network access, fully deterministic:
two runs write byte-identical files.

News verified from real reporting on the morning of 20 Nov 2026
(BBC, Reuters, AP, Times of India, Euronews):
  - Trump, Xi and Putin hold their first three-way summit in Shenzhen.
  - UN court rules Myanmar committed genocide against the Rohingya.
  - Cyclone Akvan makes landfall in Odisha, India; mass evacuations.
  - Anthropic debuts on the stock market at a ~$1.5T valuation.
  - Tanker catches fire after hitting a mine east of the Strait of Hormuz.
  - GTA VI launches worldwide.
  - Voyager 1 reaches one light-day from Earth; its data flow stops.
  - Russian strikes damage the Austrian and Dutch embassies in Kyiv.
"""
import os
import struct
import zlib

W, H = 1024, 1024

# Palette
PAPER = (246, 241, 231)
INK = (26, 26, 26)
NAVY = (22, 35, 63)
NAVY_DARK = (16, 26, 48)
GOLD = (232, 184, 75)
WHITE = (255, 255, 255)
GRAY = (110, 105, 95)
CARD = (255, 255, 255)
BORDER = (216, 210, 196)
RED = (192, 57, 43)
TEAL = (14, 124, 123)
ORANGE = (230, 126, 34)
BLUE = (46, 111, 183)
GREEN = (46, 125, 50)
PURPLE = (123, 75, 148)
PINK = (232, 93, 117)


# ---------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, rgb, w, h):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(rgb[y * w * 3:(y + 1) * w * 3])
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += _chunk(b"IHDR", ihdr)
    data += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(data)


# ------------------------------------------------------------------- Canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.w), min(y + h, self.h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for a in range(t):
                for b in range(t):
                    self.set(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.set(xx, yy, c)
                else:
                    if abs(d2 - r * r) <= r:
                        self.set(xx, yy, c)

    def triangle(self, x0, y0, x1, y1, x2, y2, c):
        ymin, ymax = min(y0, y1, y2), max(y0, y1, y2)
        for yy in range(ymin, ymax + 1):
            xs = []
            for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)):
                if ay == by:
                    continue
                if min(ay, by) <= yy < max(ay, by):
                    xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
            if len(xs) >= 2:
                for xx in range(int(min(xs)), int(max(xs)) + 1):
                    self.set(xx, yy, c)


# -------------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 bits, written as strings of 0/1.
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
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
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
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
}


def text_width(s, scale):
    return len(s) * (5 * scale + scale)


def draw_text(cv, x, y, s, scale, color):
    s = s.upper()
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.fill_rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 5 * scale + scale
    return cx


def wrap_text(s, max_chars):
    words = s.split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------- Icons
def icon_scales(cv, x, y, w, h):
    """Scales of justice: pole, crossbar, two pans."""
    cx, top = x + w // 2, y + 8
    cv.line(cx, top, cx, top + 62, NAVY, 3)
    cv.line(cx - 34, top + 14, cx + 34, top + 14, NAVY, 3)
    cv.line(cx - 34, top + 14, cx - 34, top + 22, NAVY, 2)
    cv.line(cx + 34, top + 14, cx + 34, top + 22, NAVY, 2)
    cv.triangle(cx - 48, top + 22, cx - 20, top + 22, cx - 34, top + 44, GOLD)
    cv.triangle(cx + 20, top + 22, cx + 48, top + 22, cx + 34, top + 44, GOLD)
    cv.fill_rect(cx - 30, top + 66, 60, 5, NAVY)


def icon_cyclone(cv, x, y, w, h):
    """Spiral storm: concentric arcs plus rain slashes."""
    cx, cy = x + w // 2, y + 52
    for r, col in ((44, TEAL), (34, BLUE), (24, TEAL), (14, BLUE)):
        cv.circle(cx, cy, r, col, fill=False)
    cv.circle(cx, cy, 6, NAVY, fill=True)
    for dx in (-52, -38, 38, 52):
        cv.line(cx + dx, y + 84, cx + dx - 6, y + 100, BLUE, 2)


def icon_chart(cv, x, y, w, h):
    """Rising bars and an arrow: a market debut."""
    base = y + 92
    for i, bh in enumerate((30, 48, 66, 88)):
        bx = x + 18 + i * 34
        cv.fill_rect(bx, base - bh, 22, bh, (TEAL, BLUE, GREEN, GOLD)[i])
    cv.line(x + 14, base - 96, x + 14, base + 4, INK, 2)
    cv.line(x + 14, base + 4, x + 150, base + 4, INK, 2)
    cv.line(x + 22, base - 30, x + 56, base - 52, GREEN, 3)
    cv.line(x + 56, base - 52, x + 92, base - 70, GREEN, 3)
    cv.line(x + 92, base - 70, x + 130, base - 92, GREEN, 3)
    cv.triangle(x + 130, base - 92, x + 116, base - 92, x + 130, base - 78, GREEN)


def icon_tanker(cv, x, y, w, h):
    """A tanker with containers, flames above, waves below."""
    hull_y = y + 62
    cv.triangle(x + 16, hull_y, x + 150, hull_y, x + 134, hull_y + 22, RED)
    cv.fill_rect(x + 16, hull_y, 134, 22, RED)
    for i, col in enumerate((BLUE, GOLD, TEAL, GREEN)):
        cv.fill_rect(x + 26 + i * 30, hull_y - 22, 24, 22, col)
    cv.fill_rect(x + 128, hull_y - 34, 18, 34, NAVY)
    for fx, fh in ((52, 26), (66, 38), (82, 24)):
        cv.triangle(x + fx, hull_y - 22, x + fx + 14, hull_y - 22,
                    x + fx + 7, hull_y - 22 - fh, ORANGE)
    for wy in (hull_y + 32, hull_y + 42):
        for wx in range(x + 10, x + 156, 24):
            cv.line(wx, wy, wx + 12, wy - 5, BLUE, 2)
            cv.line(wx + 12, wy - 5, wx + 24, wy, BLUE, 2)


def icon_controller(cv, x, y, w, h):
    """A game controller with a D-pad, buttons and a big VI."""
    cx, cy = x + w // 2, y + 52
    cv.fill_rect(cx - 62, cy - 26, 124, 52, NAVY_DARK)
    cv.circle(cx - 62, cy - 26, 12, NAVY_DARK)
    cv.circle(cx + 62, cy - 26, 12, NAVY_DARK)
    cv.circle(cx - 62, cy + 26, 12, NAVY_DARK)
    cv.circle(cx + 62, cy + 26, 12, NAVY_DARK)
    cv.fill_rect(cx - 48, cy - 6, 26, 12, GOLD)
    cv.fill_rect(cx - 39, cy - 15, 8, 30, GOLD)
    for bx, by, col in ((38, -14, RED), (50, -2, GREEN), (38, 10, BLUE), (26, -2, GOLD)):
        cv.circle(cx + bx, cy + by, 6, col)
    draw_text(cv, cx - 13, cy - 32, "VI", 3, WHITE)


def icon_voyager(cv, x, y, w, h):
    """A probe dish against the stars, signal arcs fading out."""
    cv.fill_rect(x + 8, y + 4, w - 16, 96, (11, 16, 38))
    for sx, sy in ((30, 18), (60, 34), (110, 14), (140, 40), (44, 66), (120, 70), (90, 26), (20, 44)):
        cv.set(x + sx, y + sy, WHITE)
        cv.set(x + sx + 1, y + sy, WHITE)
    cx, cy = x + w // 2, y + 58
    cv.line(cx - 26, cy + 30, cx, cy + 4, GOLD, 3)
    cv.line(cx + 26, cy + 30, cx, cy + 4, GOLD, 3)
    cv.circle(cx, cy, 16, GOLD, fill=False)
    cv.circle(cx, cy, 5, WHITE, fill=True)
    for r in (20, 30):
        cv.circle(cx + 46, cy - 30, r, GOLD, fill=False)


# ---------------------------------------------------------------------- Tiles
def draw_tile(cv, x, y, w, h, accent, icon, headline, sub):
    cv.fill_rect(x, y, w, h, CARD)
    cv.rect(x, y, w, h, BORDER, 1)
    cv.fill_rect(x, y, w, 8, accent)
    icon(cv, x + 8, y + 16, w - 16, 108)
    lines = wrap_text(headline, 24)
    ty = y + 132
    for ln in lines[:3]:
        draw_text(cv, x + 12, ty, ln, 2, INK)
        ty += 18
    draw_text(cv, x + 12, ty + 8, sub, 1, GRAY)


def draw_flag_us(cv, x, y):
    for i in range(7):
        cv.fill_rect(x, y + i * 5, 54, 5, RED if i % 2 == 0 else WHITE)
    cv.fill_rect(x, y, 24, 20, BLUE)
    for sy in (3, 9, 15):
        for sx in (4, 12, 20):
            cv.set(x + sx, y + sy, WHITE)


def draw_flag_cn(cv, x, y):
    cv.fill_rect(x, y, 54, 36, RED)
    cv.circle(x + 11, y + 10, 4, GOLD, fill=True)
    for sx, sy in ((26, 6), (32, 11), (32, 18), (26, 22)):
        cv.set(x + sx, y + sy, GOLD)
        cv.set(x + sx + 1, y + sy, GOLD)


def draw_flag_ru(cv, x, y):
    cv.fill_rect(x, y, 54, 12, WHITE)
    cv.fill_rect(x, y + 12, 54, 12, BLUE)
    cv.fill_rect(x, y + 24, 54, 12, RED)
    cv.rect(x, y, 54, 36, INK, 1)


# --------------------------------------------------------------------- Layout
def draw_masthead(cv):
    cv.fill_rect(0, 0, W, 104, NAVY)
    title = "THE WORLD IN ONE PAGE"
    tw = text_width(title, 5)
    draw_text(cv, (W - tw) // 2, 14, title, 5, WHITE)
    date = "FRIDAY 20 NOVEMBER 2026"
    dw = text_width(date, 2)
    draw_text(cv, (W - dw) // 2, 66, date, 2, GOLD)
    cv.fill_rect(0, 104, W, 4, GOLD)


def draw_lead(cv):
    x0, x1, y0, y1 = 8, 1016, 108, 392
    # Sunset sky: bands from orange through pink to purple.
    bands = [(255, 158, 79), (244, 120, 96), (232, 93, 117), (178, 84, 138), (123, 75, 148)]
    band_h = (270 - y0) // len(bands)
    for i, col in enumerate(bands):
        cv.fill_rect(x0, y0 + i * band_h, x1 - x0, band_h, col)
    # Sun.
    cv.circle(830, 176, 38, (255, 209, 102), fill=True)
    cv.circle(830, 176, 30, (255, 224, 138), fill=True)
    # Three flags, top right of the sky.
    draw_flag_us(cv, 690, 128)
    draw_flag_cn(cv, 762, 128)
    draw_flag_ru(cv, 834, 128)
    # Shenzhen skyline silhouette.
    heights = [58, 96, 74, 120, 66, 104, 82, 132, 70, 92, 60, 108, 78, 116, 64, 88]
    bx = x0
    for i, bh in enumerate(heights):
        bw = 62
        cv.fill_rect(bx, 270 - bh, bw, bh, NAVY_DARK)
        for wy in range(270 - bh + 10, 266, 16):
            for wx in range(bx + 8, bx + bw - 8, 14):
                if (wx + wy + i) % 3 == 0:
                    cv.fill_rect(wx, wy, 4, 5, GOLD)
        bx += bw
    # Headline band.
    cv.fill_rect(x0, 270, x1 - x0, y1 - 270, NAVY)
    draw_text(cv, 32, 284, "TRUMP, XI & PUTIN", 4, WHITE)
    draw_text(cv, 32, 320, "MEET IN SHENZHEN", 4, GOLD)
    draw_text(cv, 32, 362, "FIRST THREE-WAY SUMMIT ON NUCLEAR RISKS AND WAR", 2, WHITE)


def draw_page(cv):
    cv.fill_rect(0, 0, W, H, PAPER)
    draw_masthead(cv)
    draw_lead(cv)
    tiles = [
        (RED, icon_scales, "MYANMAR GUILTY OF GENOCIDE",
         "UN court rules on the Rohingya"),
        (TEAL, icon_cyclone, "CYCLONE AKVAN SLAMS INDIA",
         "Odisha landfall, mass evacuations"),
        (GREEN, icon_chart, "ANTHROPIC DEBUTS AT $1.5T",
         "Among the world's most valuable firms"),
        (ORANGE, icon_tanker, "TANKER BURNS IN THE GULF",
         "Mine strike east of the Strait of Hormuz"),
        (PURPLE, icon_controller, "GTA VI IS FINALLY OUT",
         "Gamers queue as launch day arrives"),
        (NAVY, icon_voyager, "VOYAGER 1 REACHES ONE LIGHT-DAY OUT",
         "Its signal falls silent at the edge"),
    ]
    xs = (8, 346, 684)
    ys = (400, 688)
    for i, (accent, icon, head, sub) in enumerate(tiles):
        draw_tile(cv, xs[i % 3], ys[i // 3], 330, 280, accent, icon, head, sub)
    also = "ALSO TODAY: RUSSIAN STRIKES DAMAGE AUSTRIAN AND DUTCH EMBASSIES IN KYIV"
    draw_text(cv, 8, 978, also, 1, INK)
    foot = "COMPILED FROM BBC, REUTERS, AP AND TIMES OF INDIA - 20 NOVEMBER 2026"
    fw = text_width(foot, 1)
    draw_text(cv, (W - fw) // 2, 1002, foot, 1, GRAY)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_page(cv)
    write_png(os.path.join(out_dir, "entry.png"), cv.px, W, H)


if __name__ == "__main__":
    main()
