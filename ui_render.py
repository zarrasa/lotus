"""Отрисовка «стеклянного» интерфейса в стиле логотипа: градиенты, рамки, свечение.

Обычные виджеты tkinter не умеют градиенты и glow, поэтому фон и плитки рисуются
в PIL и выводятся на Canvas. Все размеры — в логических пикселях, умножаются на scale.
"""

import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from themes import NIGHT, Theme

T: Theme = NIGHT                # текущая расцветка (themes.py)
GLOW_PAD = 10                   # запас вокруг плитки под свечение


def set_theme(theme: Theme) -> None:
    """Сменить расцветку: все закэшированные плитки рисуются заново."""
    global T
    T = theme
    _glass.cache_clear()
    _ring.cache_clear()
    comet.cache_clear()


def _vgradient(w: int, h: int, top, bottom) -> Image.Image:
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        col.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return col.resize((w, h))


def _mix(a, b, t: float):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))




def background(w: int, h: int, s: float) -> Image.Image:
    W, H = int(w * s), int(h * s)
    img = _vgradient(W, H, T.bg_top, T.bg_bottom).convert("RGBA")

    # Слои под размытие создаются в своём цвете с нулевой альфой, а не прозрачно-чёрными:
    # иначе размытие подмешивает чёрный и свечение получается грязным.
    # диагональный блик, как отражение на стекле логотипа
    sheen = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    ImageDraw.Draw(sheen).ellipse((-W * 0.6, -H * 0.55, W * 1.1, H * 0.35),
                                  fill=(255, 255, 255, 10 if T.dark else 60))
    img.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(30 * s)))
    # Широкого свечения внизу больше нет: на тёмном фоне его плавный спад рисовался
    # заметными «ступеньками», а шум против них оказался неприятен глазу.
    return img


SS = 3  # плашки рисуются в 3x и уменьшаются — так края рамки сглажены


def _halo(size, box, R, width, blur, color, strength):
    g = Image.new("RGBA", size, (*color, 0))
    ImageDraw.Draw(g).rounded_rectangle(box, radius=R, outline=(*color, 255), width=int(width))
    g = g.filter(ImageFilter.GaussianBlur(blur))
    g.putalpha(g.getchannel("A").point(lambda v: min(255, int(v * strength))))
    return g


@lru_cache(maxsize=1024)
def _glass(w: int, h: int, s: float, glow: float, radius: int) -> Image.Image:
    """Стеклянная плашка с рамкой; glow 0..~1.4 — сила голубой обводки."""
    P0, W0, H0 = int(GLOW_PAD * s), int(w * s), int(h * s)   # итоговые размеры
    k = s * SS
    P, W, H = P0 * SS, W0 * SS, H0 * SS
    R = int(radius * k)
    img = Image.new("RGBA", (W + 2 * P, H + 2 * P), (0, 0, 0, 0))
    box = (P, P, P + W - 1, P + H - 1)

    if glow > 0:
        # мягкое свечение + яркая узкая кайма, как неон на логотипе; компактно — ореол
        # держится у самой рамки и не растекается на соседние плитки
        img.alpha_composite(_halo(img.size, box, R, 3 * k, 3 * k, T.accent, 1.5 * glow))
        img.alpha_composite(_halo(img.size, box, R, 1.5 * k, 0.8 * k, T.accent_light, 0.9 * glow))

    # тело: вертикальный градиент, чуть прозрачный
    body = _vgradient(W, H, _mix(T.body_top, T.accent, 0.06 * min(glow, 1)), T.body_bottom).convert("RGBA")
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), radius=R, fill=T.body_alpha)
    body.putalpha(mask)

    # блик в верхней половине
    sheen = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    ImageDraw.Draw(sheen).ellipse((-W * 0.3, -H * 1.1, W * 1.2, H * 0.55), fill=(255, 255, 255, T.sheen))
    sheen = sheen.filter(ImageFilter.GaussianBlur(6 * k))
    sheen.putalpha(Image.composite(sheen.getchannel("A"), Image.new("L", (W, H), 0), mask))
    body.alpha_composite(sheen)
    img.alpha_composite(body, (P, P))

    # рамка: серая → голубая по мере glow
    d = ImageDraw.Draw(img)
    t = min(glow, 1.0)
    edge = _mix(T.edge_off, T.accent_light if T.dark else T.accent, t)
    d.rounded_rectangle(box, radius=R, outline=(*edge, 255),
                        width=max(SS, round((1 + 0.6 * t) * k)))
    # тонкая светлая линия по верхнему краю — «толщина стекла»
    o = int(1.5 * k)
    hl = (255, 255, 255, 45 if T.dark else 170)
    d.arc((P + o, P + o, P + 2 * R - o, P + 2 * R - o), 180, 270, fill=hl, width=SS)
    d.line((P + R, P + o, P + W - R, P + o), fill=hl, width=SS)
    return img.resize((W0 + 2 * P0, H0 + 2 * P0), Image.LANCZOS)


# ---------- «бегущий огонёк» вокруг плитки, пока сервис включается ----------

COMET_STEPS = 60       # положений огонька на один круг
COMET_TRAIL = 0.5      # длина хвоста, доля круга


@lru_cache(maxsize=8)
def _ring(w: int, h: int, s: float, radius: int) -> Image.Image:
    """Рамка на полной яркости: свечение + яркая кайма + чёткая линия."""
    P0, W0, H0 = int(GLOW_PAD * s), int(w * s), int(h * s)
    k = s * SS
    P, W, H = P0 * SS, W0 * SS, H0 * SS
    R = int(radius * k)
    size = (W + 2 * P, H + 2 * P)
    box = (P, P, P + W - 1, P + H - 1)
    img = _halo(size, box, R, 4 * k, 3 * k, T.accent, 3.0)
    img.alpha_composite(_halo(size, box, R, 2 * k, 1 * k, T.accent_light, 2.0))
    ImageDraw.Draw(img).rounded_rectangle(box, radius=R, outline=(*T.ring_line, 255),
                                          width=max(2 * SS, int(1.8 * k)))
    return img.resize((W0 + 2 * P0, H0 + 2 * P0), Image.LANCZOS)


@lru_cache(maxsize=8)
def _conic(side: int) -> Image.Image:
    """Квадратная маска-«комета»: голова на угле 0, хвост тянется против часовой."""
    c = (side - 1) / 2
    full = 2 * math.pi
    trail = COMET_TRAIL * full
    lead = 0.035 * full    # короткое мягкое нарастание перед головой
    data = []
    for y in range(side):
        for x in range(side):
            d = (-math.atan2(y - c, x - c)) % full   # насколько пиксель позади головы
            if d < trail:
                v = (1 - d / trail) ** 1.3
            elif d > full - lead:
                v = ((d - (full - lead)) / lead) ** 2
            else:
                v = 0.0
            data.append(int(255 * v))
    m = Image.new("L", (side, side))
    m.putdata(data)
    return m


@lru_cache(maxsize=512)
def comet(w: int, h: int, s: float, step: int, radius: int = 14) -> Image.Image:
    base = _glass(w, h, s, 0.0, radius).copy()
    ring = _ring(w, h, s, radius)
    side = int(math.hypot(*ring.size)) + 2
    mask = _conic(side).rotate(-360 * step / COMET_STEPS, resample=Image.BILINEAR)
    l, t = (side - ring.width) // 2, (side - ring.height) // 2
    mask = mask.crop((l, t, l + ring.width, t + ring.height))
    layer = ring.copy()
    layer.putalpha(ImageChops.multiply(ring.getchannel("A"), mask))
    base.alpha_composite(layer)
    return base


def tile(w: int, h: int, s: float, glow: float, icon: Image.Image | None = None,
         icon_xy=(12, 12), icon_size=34, radius: int = 14, spin: int | None = None) -> Image.Image:
    """Плитка с прозрачным краем (больше плитки на GLOW_PAD с каждой стороны).
    spin — положение бегущего огонька; если задан, glow не используется."""
    P = int(GLOW_PAD * s)
    out = (comet(w, h, s, spin, radius) if spin is not None
           else _glass(w, h, s, round(glow, 2), radius)).copy()
    if icon is not None:
        n = int(icon_size * s)
        out.alpha_composite(icon.resize((n, n), Image.LANCZOS),
                            (P + int(icon_xy[0] * s), P + int(icon_xy[1] * s)))
    return out


def themed_icon(glyph: Image.Image) -> Image.Image:
    """Значок в стиле приложения: тёмный стеклянный квадрат с рамкой и глифом в цвете темы."""
    n = glyph.width
    r = int(n * 0.24)
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, n - 1, n - 1), radius=r, fill=255)
    img = _vgradient(n, n, _mix(T.body_top, T.accent, 0.35), _mix(T.body_bottom, T.accent, 0.12)).convert("RGBA")
    img.putalpha(mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 1, n - 2, n - 2), radius=r, outline=(*T.accent_light, 170), width=max(2, n // 40))
    tint = Image.new("RGBA", (n, n), (*T.accent_light, 255))
    tint.putalpha(glyph.getchannel("A"))
    img.alpha_composite(tint)
    return img


def faded(img: Image.Image, k: float = 0.4) -> Image.Image:
    img = img.convert("RGBA")
    img.putalpha(img.getchannel("A").point(lambda a: int(a * k)))
    return img
