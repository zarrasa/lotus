"""Из картинки-логотипа делает icons/lotus.png (прозрачные углы) и icons/lotus.ico.

Запуск: python tools/make_logo.py <исходная картинка>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# светящаяся рамка на исходнике 1254x1254 идёт по x 56..1192, y 59..1185, радиус ~290-330;
# режем чуть внутри неё, чтобы в углах не осталось тёмного фона
BOX = (59, 62, 1189, 1182)
RADIUS = 315


def main(src: Path) -> None:
    out = Path(__file__).resolve().parent.parent / "icons"
    im = Image.open(src).convert("RGBA")
    k = im.width / 1254
    box = tuple(int(v * k) for v in BOX)

    im = im.crop(box)
    # маска в 4x и уменьшение — гладкий край без «лесенки» и без размытия рамки
    ss = 4
    mask = Image.new("L", (im.width * ss, im.height * ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, mask.width - 1, mask.height - 1),
                                           radius=int(RADIUS * k * ss), fill=255)
    im.putalpha(mask.resize(im.size, Image.LANCZOS))
    im = im.resize((max(im.size),) * 2, Image.LANCZOS)  # ровный квадрат

    im.resize((512, 512), Image.LANCZOS).save(out / "lotus.png")
    im.save(out / "lotus.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                      (64, 64), (128, 128), (256, 256)])
    print("icons/lotus.png, icons/lotus.ico")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
