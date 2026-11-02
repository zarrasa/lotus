"""Генерирует icons/*.png: белый логотип на цветном скруглённом квадрате.

Глифы — Font Awesome Free 6.5.2 (иконки CC BY 4.0, шрифты SIL OFL 1.1).
Запуск: python tools/make_icons.py tools/fonts
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 128   # итоговый размер PNG (CTkImage сам уменьшит под экран)
SS = 4       # суперсэмплинг для гладких краёв

# id -> (шрифт, кодовая точка, цвет фона); None — только белый глиф на прозрачном фоне,
# Lotus сам кладёт его на стеклянный квадрат в цвете текущей темы (ui_render.themed_icon)
ICONS = {
    "youtube": ("fa-brands-400.ttf", 0xF167, "#E24B4A"),
    "discord": ("fa-brands-400.ttf", 0xF392, "#5865F2"),
    "telegram": ("fa-brands-400.ttf", 0xF2C6, "#2AABEE"),
    "steam": ("fa-brands-400.ttf", 0xF1B6, "#2A475E"),
    "meta": ("fa-brands-400.ttf", 0xF16D, "#D6336C"),    # Instagram
    "twitch": ("fa-brands-400.ttf", 0xF1E8, "#9146FF"),
    "games": ("fa-solid-900.ttf", 0xF05B, None),   # прицел
    "custom": ("fa-solid-900.ttf", 0xF0AC, None),  # глобус
}


def render(font_path: Path, code: int, color: str | None) -> Image.Image:
    s = SIZE * SS
    img = Image.new("RGBA", (s, s), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    if color:
        d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.24), fill=color)

    font = ImageFont.truetype(str(font_path), int(s * 0.56))
    ch = chr(code)
    l, t, r, b = d.textbbox((0, 0), ch, font=font)
    if r - l <= 0:
        raise ValueError(f"нет глифа U+{code:04X} в {font_path.name}")
    # центрируем по фактическим границам глифа, а не по метрикам шрифта
    d.text(((s - (r - l)) / 2 - l, (s - (b - t)) / 2 - t), ch, font=font, fill="white")
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main(font_dir: Path) -> None:
    out = Path(__file__).resolve().parent.parent / "icons"
    out.mkdir(exist_ok=True)
    for sid, (font, code, color) in ICONS.items():
        render(font_dir / font, code, color).save(out / f"{sid}.png")
        print("icons/" + sid + ".png")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
