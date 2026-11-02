"""Логотипы цветных тем: исходный тёмный логотип (icons/lotus.png), перекрашенный в цвет темы.
Голубое свечение и линии логотипа поворачиваются по оттенку, тёмное стекло не трогается.

Запуск: python tools/make_themes.py
"""

import colorsys
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from themes import THEMES  # noqa: E402

ICONS = Path(__file__).resolve().parent.parent / "icons"
SRC_HUE = colorsys.rgb_to_hsv(79 / 255, 168 / 255, 232 / 255)[0]   # голубой исходного логотипа


def recolor(img: Image.Image, accent: tuple) -> Image.Image:
    th, ts, _ = colorsys.rgb_to_hsv(*(c / 255 for c in accent))
    shift = th - SRC_HUE
    out = []
    for r, g, b, a in img.get_flattened_data():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.08:   # цветные пиксели (свечение, линии); серо-белые оставляем
            h = (h + shift) % 1.0
            s = min(1.0, s * (0.7 + 0.6 * ts))
        r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
        out.append((int(r2 * 255), int(g2 * 255), int(b2 * 255), a))
    res = Image.new("RGBA", img.size)
    res.putdata(out)
    return res


def main() -> None:
    src = Image.open(ICONS / "lotus.png").convert("RGBA")
    for t in THEMES:
        if t.logo == "lotus":
            continue
        logo = recolor(src, t.accent)
        logo.save(ICONS / f"{t.logo}.png")
        logo.save(ICONS / f"{t.logo}.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                                  (64, 64), (128, 128), (256, 256)])
        print(f"icons/{t.logo}.png")


if __name__ == "__main__":
    main()
