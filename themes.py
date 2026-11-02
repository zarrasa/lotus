"""Расцветки Lotus. Все тёмные, как исходная «Ночь»: меняется только цвет свечения и акцентов
(логотипы тем — исходный, перекрашенный в цвет темы: icons/theme_<id>.png, см. tools/make_themes.py)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    logo: str                 # файл в icons/ (png и ico с тем же именем)
    dark: bool
    # отрисовка (RGB)
    bg_top: tuple
    bg_bottom: tuple
    accent: tuple             # свечение рамки
    accent_light: tuple       # яркая кайма свечения
    ring_line: tuple          # линия бегущего огонька
    body_top: tuple
    body_bottom: tuple
    body_alpha: int
    edge_off: tuple
    sheen: int                # сила блика на стекле
    bottom_glow: int
    # текст и виджеты (hex)
    text: str
    text_off: str
    muted: str
    ok: str
    err: str
    window_bg: str
    field_bg: str
    border: str
    hover: str
    swatch: str               # кружок в выборе темы

    @property
    def accent_hex(self) -> str:
        return _hex(self.accent)


def _hex(c) -> str:
    return "#%02X%02X%02X" % c


def _mix(a, b, t: float) -> tuple:
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _rgb(h: str) -> tuple:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


WHITE, BLACK = (255, 255, 255), (0, 0, 0)


NIGHT = Theme(
    id="night", name="Ночь", logo="lotus", dark=True,
    bg_top=(24, 32, 43), bg_bottom=(11, 15, 21),
    accent=(79, 168, 232), accent_light=(150, 205, 245), ring_line=(240, 250, 255),
    body_top=(31, 43, 57), body_bottom=(15, 21, 29), body_alpha=238,
    edge_off=(48, 60, 76), sheen=13, bottom_glow=40,
    text="#E6EEF5", text_off="#7A8899", muted="#6B7A8C", ok="#7CC4F5", err="#F09595",
    window_bg="#10161E", field_bg="#18212C", border="#2A3644", hover="#1F2B38", swatch="#4FA8E8",
)

def dark(tid: str, name: str, accent: str) -> Theme:
    """Тёмная тема как «Ночь», но свечение и акценты — в цвете accent; фон чуть тонирован им."""
    a = _rgb(accent)
    n = NIGHT
    tint = lambda c, k: _mix(c, a, k)
    return Theme(
        id=tid, name=name, logo=f"theme_{tid}", dark=True,
        bg_top=tint(n.bg_top, 0.07), bg_bottom=tint(n.bg_bottom, 0.03),
        accent=a, accent_light=_mix(a, WHITE, 0.45), ring_line=_mix(a, WHITE, 0.85),
        body_top=tint(n.body_top, 0.06), body_bottom=n.body_bottom, body_alpha=n.body_alpha,
        edge_off=tint(n.edge_off, 0.12), sheen=n.sheen, bottom_glow=n.bottom_glow,
        text=n.text, text_off=n.text_off, muted=n.muted, ok=_hex(_mix(a, WHITE, 0.35)), err=n.err,
        window_bg=_hex(tint(_rgb(n.window_bg), 0.04)), field_bg=_hex(tint(_rgb(n.field_bg), 0.06)),
        border=_hex(tint(_rgb(n.border), 0.15)), hover=_hex(tint(_rgb(n.hover), 0.12)), swatch=accent,
    )


THEMES = [
    NIGHT,
    dark("green", "Зелёная", "#2FCB7A"),
    dark("pink", "Розовая", "#F0549E"),
    dark("orange", "Оранжевая", "#FF8C2E"),
    dark("gold", "Золотая", "#E5AE45"),
    dark("coral", "Коралловая", "#FF5A6E"),
]
THEMES_BY_ID = {t.id: t for t in THEMES}
