"""Erzeugt icon.ico (blaue Kachel mit Uhr) – ohne externe Pakete."""
import math
import struct
import sys
import zlib

BLUE_TOP, BLUE_BOT = (0x6E, 0xA8, 0xFF), (0x3A, 0x6F, 0xE0)
SS = 4  # Supersampling für weiche Kanten


def inside(x, y):
    """Farbe (r,g,b,a) am Punkt x,y im Einheitsquadrat 0..1."""
    # abgerundete Kachel
    r, m = 0.22, 0.04
    cx, cy = min(max(x, m + r), 1 - m - r), min(max(y, m + r), 1 - m - r)
    if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
        return None
    dx, dy = x - 0.5, y - 0.5
    d = math.hypot(dx, dy)
    white = (255, 255, 255, 255)
    if 0.27 <= d <= 0.33:  # Zifferblatt-Ring
        return white
    # Zeiger: auf 10 nach 10 (Stundenzeiger nach oben links, Minutenzeiger nach oben rechts)
    for ang, length in ((-125, 0.17), (-55, 0.22)):
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        t = dx * ux + dy * uy
        if -0.02 <= t <= length and abs(dx * uy - dy * ux) <= 0.032:
            return white
    if d <= 0.045:
        return white
    k = y
    return tuple(int(BLUE_TOP[i] * (1 - k) + BLUE_BOT[i] * k) for i in range(3)) + (255,)


def render(size):
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(SS):
                for sx in range(SS):
                    c = inside((px + (sx + 0.5) / SS) / size, (py + (sy + 0.5) / SS) / size)
                    if c:
                        for i in range(3):
                            acc[i] += c[i] * c[3]
                        acc[3] += c[3]
            n = SS * SS
            a = acc[3] / n
            rgb = [int(acc[i] / acc[3]) if acc[3] else 0 for i in range(3)]
            row += bytes(rgb + [int(a)])
        rows.append(b"\x00" + bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main(out):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [render(s) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, img in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(img), offset)
        offset += len(img)
    with open(out, "wb") as f:
        f.write(header + entries + b"".join(images))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "icon.ico")
