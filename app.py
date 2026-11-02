"""Интерфейс Lotus: стеклянные плитки сервисов в стиле логотипа. Движок — engine.py."""

import ctypes
import math
import os
import queue
import re
import sys
import threading
import time
from tkinter import messagebox

import customtkinter as ctk
import pystray
from PIL import Image, ImageTk

import autostart
import engine
import i18n
import ui_render as R
import updater
from i18n import svc_name, tr
from services import PRESETS, PRESETS_BY_ID
from themes import THEMES, THEMES_BY_ID, NIGHT
from version import VERSION

ICONS = engine.ROOT / "icons"

W, H = 340, 520
# id -> (x, y, w, h); «Игры» и «Свои сайты» — широкие плитки
TILES = {
    "youtube": (16, 60, 150, 88), "discord": (174, 60, 150, 88),
    "telegram": (16, 156, 150, 88), "steam": (174, 156, 150, 88),
    "meta": (16, 252, 150, 88), "twitch": (174, 252, 150, 88),
    "games": (16, 348, 308, 56), "custom": (16, 412, 308, 56),
}
THEMED_ICONS = ("games", "custom")   # значки в стиле приложения, перекрашиваются под тему
PILL = (210, 17, 86, 24)

FRAME_MS = 16          # ~60 кадров в секунду
SPIN_PERIOD = 1.1      # секунд на круг бегущего огонька
WATCH_SEC = 300        # сторож проверяет доступ раз в 5 минут
UPDATE_SEC = 24 * 3600 # zapret и списки — раз в сутки
LOTUS_SEC = 3600       # новая версия Lotus — раз в час (лимит GitHub без входа: 60 запросов в час)


def _ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def ignite_frames(n: int = 26) -> list[float]:
    """Розжиг рамки, когда сервис запустился: быстрая вспышка и плавное успокоение."""
    out = []
    for i in range(1, n + 1):
        t = i / n
        if t < 0.35:
            g = 0.2 + 1.35 * _ease_out(t / 0.35)
        else:
            u = (t - 0.35) / 0.65
            g = 1.55 - 0.55 * (0.5 - 0.5 * math.cos(math.pi * u))
        out.append(round(g, 2))
    return out


def fade_frames(start: float, n: int = 14) -> list[float]:
    return [round(start * (1 - _ease_out(i / n)), 2) for i in range(1, n + 1)]


class App(ctk.CTk):
    def __init__(self, start_hidden: bool = False, show_event=None, updated: bool = False) -> None:
        cfg = engine.load_config()
        i18n.set_lang(cfg.get("lang", "ru"))
        R.set_theme(THEMES_BY_ID.get(cfg.get("theme"), NIGHT))
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=R.T.window_bg)
        self.title("Lotus")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self._set_window_icon()

        # системный таймер Windows по умолчанию тикает раз в 15.6 мс — для 60 кадров нужен 1 мс
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

        self.engine = engine.Engine()
        self.cfg = cfg
        self.busy = False
        self.dirty = False                   # выбор поменялся, нужно применить
        self.results: dict[str, bool] = {}   # итог проверки доступа по сервисам
        self.reasons: dict[str, str] = {}    # что именно не работает: st.fail / st.video_fail / ...
        self.quic_hint_shown = False
        self.installing = False              # идёт установка новой версии Lotus
        self.log_lines: list[str] = []
        self.settings: Settings | None = None
        self.ui_q: queue.Queue = queue.Queue()  # задачи для окна из фоновых потоков
        self.watch_strikes = 0               # сколько проверок подряд что-то не открывалось
        self.updates: dict = {"lotus": None, "zapret": None}

        # --- холст и фон ---
        self.s = self._get_window_scaling()
        s = self.s
        self.canvas = ctk.CTkCanvas(self, width=int(W * s), height=int(H * s),
                                    highlightthickness=0, bd=0, bg=R.T.window_bg)
        self.canvas.pack()
        self._build_bg()
        # Tk не умеет полупрозрачность, поэтому вся сцена (фон, плитки, плашка)
        # собирается в одну картинку в PIL; поверх неё — только текст.
        self.scene = self.canvas.create_image(0, 0, anchor="nw")
        self._scene_tk = None
        self._scene_key = None
        self.layers: dict[str, tuple] = {}   # имя -> (ключ, картинка, x, y)
        self.title_item = self.text(54, 29, "Lotus", 17, R.T.text, bold=True, anchor="w")

        # --- статус и шестерёнка ---
        self.pill_text = self.text(PILL[0] + PILL[2] / 2, PILL[1] + PILL[3] / 2, "", 11, R.T.muted)
        self.gear = self.text(318, 29, "⚙", 17, R.T.text_off, tag="gear")
        self.canvas.tag_bind("gear", "<Button-1>", lambda e: self.open_settings())
        self.canvas.tag_bind("gear", "<Enter>", lambda e: self._hover_gear(True))
        self.canvas.tag_bind("gear", "<Leave>", lambda e: self._hover_gear(False))

        # --- плитки ---
        self._load_icons()
        self.items: dict[str, tuple[int, int, int]] = {}
        self.glow = {sid: 0.0 for sid in TILES}
        self.anim: dict[str, list[float]] = {}
        self.spin: dict[str, float] = {}      # когда у плитки побежал огонёк (сервис включается)
        self.hover_lvl = {sid: 0.0 for sid in TILES}
        self.hover: str | None = None
        self.was_on = {sid: sid in self.cfg["services"] for sid in TILES}
        for sid, (x, y, w, h) in TILES.items():
            if h < 80:
                nm = self.text(x + 56, y + h / 2, svc_name(sid), 14, R.T.text, bold=True, anchor="w")
                st = self.text(x + w - 14, y + h / 2, "", 11, R.T.muted, anchor="e")
            else:
                nm = self.text(x + 14, y + 52, svc_name(sid), 14, R.T.text, bold=True, anchor="nw")
                st = self.text(x + 14, y + 71, "", 11, R.T.muted, anchor="nw")
            self.items[sid] = (None, nm, st)
            self.glow[sid] = 1.0 if self.was_on[sid] else 0.0
        # клики и наведение — по координатам: плитки нарисованы картинкой, а не виджетами
        self.canvas.bind("<Button-1>", lambda e: (k := self._hit(e)) and self.on_tile(k))
        self.canvas.bind("<Motion>", lambda e: self._set_hover(self._hit(e)))
        self.canvas.bind("<Leave>", lambda e: self._set_hover(None))

        self.msg = self.text(W / 2, 492, tr("hint"), 11, R.T.muted, width=300)

        # --- трей: крестик сворачивает окно к часам, обход продолжает работать ---
        self.show_event = show_event       # второй запуск Lotus просит показать окно
        self.tray_hint_shown = False
        self.autostart_on = autostart.is_enabled()
        self.tray = pystray.Icon("Lotus", Image.open(ICONS / f"{R.T.logo}.png"), "Lotus", self._tray_menu())
        self.tray.run_detached()
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        if start_hidden:
            self.withdraw()
            self.tray_hint_shown = True    # при автозапуске не показываем подсказку
        try:
            autostart.refresh_path()
        except Exception:
            pass

        # заранее посчитать маску огонька (~70 мс), чтобы первая анимация не дёрнулась
        threading.Thread(target=lambda: [R.comet(w, h, s, 0) for w, h in {(150, 88), (308, 56)}],
                         daemon=True).start()
        self.refresh()
        self._tick()
        self._drain_ui()
        if self.selected():  # что было включено в прошлый раз — включаем сразу
            self.apply()
        self.after(WATCH_SEC * 1000, self._watch)
        self.after(15_000, lambda: self.check_updates(quiet=True))
        self.after(20_000, self._lotus_check)
        if updated:   # перезапуск после автообновления
            self.after(1500, lambda: (self.log(tr("msg.updated", v=VERSION)),
                                      self.notify(tr("tray.updated_title"), tr("msg.updated", v=VERSION))))

    # --- оформление ---

    def _set_window_icon(self) -> None:
        try:
            self.iconbitmap(str(ICONS / f"{R.T.logo}.ico"))
        except Exception:
            pass

    def _load_icons(self) -> None:
        self.icons = {sid: Image.open(ICONS / f"{sid}.png").convert("RGBA") for sid in TILES}
        for sid in THEMED_ICONS:
            self.icons[sid] = R.themed_icon(self.icons[sid])
        self.icons_off = {sid: R.faded(im) for sid, im in self.icons.items()}

    def _build_bg(self) -> None:
        s = self.s
        self.bg = R.background(W, H, s)
        logo = Image.open(ICONS / f"{R.T.logo}.png").resize((int(30 * s),) * 2, Image.LANCZOS)
        self.bg.alpha_composite(logo, (int(16 * s), int(14 * s)))

    def apply_theme(self, tid: str) -> None:
        """Сменить расцветку на лету: фон, логотип, стекло, свечение, текст, иконки."""
        theme = THEMES_BY_ID[tid]
        if theme is R.T:
            return
        R.set_theme(theme)
        self.cfg["theme"] = tid
        engine.save_config(self.cfg)
        self.configure(fg_color=theme.window_bg)
        self.canvas.configure(bg=theme.window_bg)
        self._build_bg()
        self._load_icons()
        self.layers.clear()
        self._scene_key = None
        self.canvas.itemconfigure(self.title_item, fill=theme.text)
        self.canvas.itemconfigure(self.gear, fill=theme.text_off)
        self.canvas.itemconfigure(self.msg, fill=theme.muted)
        self.refresh()
        self._set_window_icon()
        try:
            self.tray.icon = Image.open(ICONS / f"{theme.logo}.png")
        except Exception:
            pass
        self._reopen_settings()

    def apply_lang(self, lang: str) -> None:
        if lang == i18n.LANG:
            return
        i18n.set_lang(lang)
        self.cfg["lang"] = lang
        engine.save_config(self.cfg)
        for sid, (_, nm, _) in self.items.items():
            self.canvas.itemconfigure(nm, text=svc_name(sid))
        self.canvas.itemconfigure(self.msg, text=tr("hint"))
        self.tray.menu = self._tray_menu()
        self.tray.update_menu()
        self.refresh()
        self._reopen_settings()

    def _reopen_settings(self) -> None:
        """Окно настроек проще пересоздать в новых цветах/языке на том же месте."""
        if self.settings and self.settings.winfo_exists():
            pos = self.settings.geometry().split("+", 1)[1]
            self.settings.destroy()
            self.settings = Settings(self)
            self.settings.geometry(f"+{pos}")

    # --- рисование ---

    def text(self, x, y, text, size, color, bold=False, anchor="center", tag=None, width=None):
        s = self.s
        font = ("Segoe UI Semibold" if bold else "Segoe UI", -int(size * s))
        kw = {"width": int(width * s), "justify": "center"} if width else {}
        return self.canvas.create_text(x * s, y * s, text=text, fill=color, font=font,
                                       anchor=anchor, tags=tag, **kw)

    def _layer(self, name: str, key: tuple, x: float, y: float, make) -> None:
        """Обновить слой сцены, только если его вид поменялся."""
        if self.layers.get(name, (None,))[0] != key:
            self.layers[name] = (key, make(), x, y)

    def _draw_tile(self, sid: str, spin: int | None = None) -> None:
        on = sid in self.cfg["services"]
        glow = round((self.glow[sid] + 0.2 * self.hover_lvl[sid]) * 50) / 50   # шаг 0.02
        x, y, w, h = TILES[sid]
        icon = self.icons[sid] if on else self.icons_off[sid]
        key = ("spin", spin, on) if spin is not None else (glow, on)
        self._layer(sid, key, x, y, lambda: R.tile(
            w, h, self.s, glow, icon, icon_xy=(14, (h - 34) / 2) if h < 80 else (14, 12), spin=spin))

    def _draw_pill(self, running: bool) -> None:
        x, y, w, h = PILL
        self._layer("pill", (running,), x, y,
                    lambda: R.tile(w, h, self.s, 0.6 if running else 0.0, radius=12))
        self.canvas.itemconfigure(self.pill_text, text=tr("pill.on") if running else tr("pill.off"),
                                  fill=R.T.ok if running else R.T.muted)
        if hasattr(self, "tray"):
            self.tray.title = tr("tray.on") if running else tr("tray.off")

    def _render(self) -> None:
        key = tuple((n, v[0]) for n, v in sorted(self.layers.items()))
        if key == self._scene_key:
            return
        self._scene_key = key
        P = int(R.GLOW_PAD * self.s)
        img = self.bg.copy()
        for _, im, x, y in self.layers.values():
            img.alpha_composite(im, (int(x * self.s) - P, int(y * self.s) - P))
        self._scene_tk = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(self.scene, image=self._scene_tk)

    def _tick(self) -> None:
        """Кадр анимации: огонёк бегает по рамке, пока сервис включается; когда запустился —
        рамка разгорается целиком; при выключении плавно гаснет."""
        if self.state() == "withdrawn":  # окно в трее — рисовать незачем
            self.after(200, self._tick)
            return
        started = time.perf_counter()
        pending = (tr("st.starting"), tr("st.checking"))
        for sid in TILES:
            on = sid in self.cfg["services"]
            target = 1.0 if self.hover == sid else 0.0
            self.hover_lvl[sid] += (target - self.hover_lvl[sid]) * 0.25

            if on and self.canvas.itemcget(self.items[sid][2], "text") in pending:
                # положение огонька — по времени, а не по кадрам: скорость не зависит от FPS
                t0 = self.spin.setdefault(sid, time.perf_counter())
                step = int((time.perf_counter() - t0) / SPIN_PERIOD * R.COMET_STEPS) % R.COMET_STEPS
                self.anim.pop(sid, None)
                self.glow[sid] = 0.2
                self._draw_tile(sid, spin=step)
                continue
            if self.spin.pop(sid, None) is not None and on:
                self.anim[sid] = ignite_frames()

            if self.anim.get(sid):
                self.glow[sid] = self.anim[sid].pop(0)
            else:
                self.glow[sid] = 1.0 if on else 0.0
            self._draw_tile(sid)
        self._render()
        spent = (time.perf_counter() - started) * 1000   # время кадра вычитаем из паузы
        self.after(max(1, int(FRAME_MS - spent)), self._tick)

    def _hit(self, e) -> str | None:
        x, y = e.x / self.s, e.y / self.s
        for sid, (tx, ty, w, h) in TILES.items():
            if tx <= x <= tx + w and ty <= y <= ty + h:
                return sid
        return None

    def _set_hover(self, sid: str | None) -> None:
        if sid != self.hover:
            self.hover = sid
            self.canvas.configure(cursor="hand2" if sid else "")

    def _hover_gear(self, on: bool) -> None:
        self.canvas.itemconfigure(self.gear, fill=R.T.text if on else R.T.text_off)
        self.canvas.configure(cursor="hand2" if on else "")

    # --- трей ---

    def _tray_menu(self) -> pystray.Menu:
        """Меню значка в трее: сервисы можно включать прямо отсюда, не открывая окно."""
        def toggle(sid):
            return lambda: self.post(lambda: self.on_tile(sid))

        services = [pystray.MenuItem(svc_name(sid), toggle(sid),
                                     checked=lambda item, k=sid: k in self.cfg["services"])
                    for sid in TILES]
        return pystray.Menu(
            pystray.MenuItem(tr("tray.open"), lambda: self.post(self.show_window), default=True),
            pystray.Menu.SEPARATOR,
            *services,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(tr("tray.autostart"),
                             lambda: self.post(lambda: self.set_autostart(not self.autostart_on)),
                             checked=lambda item: self.autostart_on),
            pystray.MenuItem(tr("tray.quit"), lambda: self.post(self.quit_app)),
        )

    def notify(self, title: str, text: str) -> None:
        try:
            self.tray.notify(text, title)
        except Exception:
            pass

    # --- helpers ---

    def selected(self) -> list[str]:
        return list(self.cfg["services"])

    def post(self, fn) -> None:
        """Выполнить fn в главном потоке (tkinter нельзя трогать из фоновых)."""
        self.ui_q.put(fn)

    def _drain_ui(self) -> None:
        while not self.ui_q.empty():
            self.ui_q.get_nowait()()
        if self.show_event and self.show_event.is_set():
            self.show_event.clear()
            self.show_window()
        self.after(50, self._drain_ui)

    def log(self, text: str) -> None:
        def do():
            self.log_lines.append(text)
            # внизу окна места на 2-3 строки; длинное целиком остаётся в журнале в ⚙
            short = text if len(text) <= 110 else text[:100].rsplit(" ", 1)[0] + "… " + tr("msg.more")
            self.canvas.itemconfigure(self.msg, text=short)
            if self.settings and self.settings.winfo_exists():
                self.settings.append_log(text)
        self.post(do)

    def run_bg(self, fn) -> None:
        if self.busy:
            return
        self.busy = True
        self.refresh()

        def wrap():
            try:
                fn()
            except Exception as e:
                self.log(tr("msg.error", e=e))
            finally:
                self.busy = False
                self.post(self._bg_done)
        threading.Thread(target=wrap, daemon=True).start()

    def start_engine(self, preset_id: str | None = None) -> None:
        self.engine.start(self.selected(), preset_id or self.cfg["preset"], self.cfg["tg_secret"],
                          self.cfg.get("overrides"))

    def run_autodetect(self) -> bool:
        """Подобрать пресеты (свой у сервиса, если общий ему не подходит) и включить выбранное.
        True — если хоть что-то подошло."""
        self.results = {}
        found = engine.autodetect(self.engine, self.selected(), self.log)
        if found:
            self.cfg["preset"], self.cfg["overrides"] = found
            engine.save_config(self.cfg)
            self.log(tr("msg.best", name=self.preset_summary()))
        else:
            self.log(tr("msg.none_helped"))
        self.dirty = True  # autodetect всё остановил — вернуть выбранные сервисы
        self._apply_loop()
        return bool(found)

    def preset_summary(self) -> str:
        """«Основной» или «Основной; Discord — Фейковый TLS»."""
        main = tr(f"preset.{self.cfg['preset']}")
        extra = [f"{svc_name(s)} — {tr(f'preset.{p}')}" for s, p in self.cfg.get("overrides", {}).items()]
        return "; ".join([main, *extra])

    def set_results(self, details: dict) -> None:
        """Итог engine.check_details: открывается ли сервис и если нет — что именно."""
        self.results.update({s: r is None for s, r in details.items()})
        self.reasons.update({s: r for s, r in details.items() if r})
        for s, r in details.items():
            if r is None:
                self.reasons.pop(s, None)

    def start_and_check(self) -> None:
        self.results = {}
        self.start_engine()
        self.post(self.refresh)
        self.set_results(engine.check_details(self.selected()))
        bad = [svc_name(s) for s, ok in self.results.items() if not ok]
        self.log(tr("msg.fail", names=", ".join(bad)) if bad else tr("msg.all_ok"))
        if self.results.get("youtube") is False and not self.quic_hint_shown:
            self.quic_hint_shown = True   # почему браузер открывает, а Lotus пишет «нет» — раз за запуск
            self.log(tr("msg.quic_hint"))

    def apply(self) -> None:
        """Применить текущий выбор плиток. Клики во время применения не теряются:
        после текущего шага выбор применится ещё раз."""
        self.dirty = True
        if not self.busy:
            self.run_bg(self._apply_loop)

    def _bg_done(self) -> None:
        self.refresh()
        if self.dirty:  # клик пришёлся на самый конец фоновой работы
            self.apply()

    def _apply_loop(self) -> None:
        while self.dirty:
            self.dirty = False
            if self.selected():
                self.start_and_check()
            else:
                self.engine.stop()
                self.results = {}
                self.log(tr("msg.all_off"))

    def refresh(self) -> None:
        running = self.engine.running
        sel = self.selected()
        for sid in TILES:
            on = sid in sel
            if not on:
                text, color = tr("st.off"), R.T.muted
            elif sid == "custom" and not engine.domains("custom"):
                text, color = tr("st.no_sites"), R.T.muted
            elif not running:
                text, color = (tr("st.starting"), R.T.muted) if self.busy else (tr("st.error"), R.T.err)
            elif sid == "telegram":
                text, color = tr("st.proxy", port=engine.TG_PORT), R.T.ok
            elif sid == "games":
                text, color = tr("st.subnets", n=count_ipset()), R.T.ok
            elif sid == "custom":
                text, color = tr("st.sites", n=len(engine.domains("custom"))), R.T.ok
            elif sid not in self.results:
                text, color = tr("st.checking"), R.T.muted
            elif self.results[sid]:
                text, color = tr("st.ok"), R.T.ok
            else:
                text, color = tr(self.reasons.get(sid, "st.fail")), R.T.err
            _, nm, st = self.items[sid]
            self.canvas.itemconfigure(st, text=text, fill=color)
            self.canvas.itemconfigure(nm, fill=R.T.text if on else R.T.text_off)
            if on != self.was_on[sid]:
                self.was_on[sid] = on
                if not on:
                    self.spin.pop(sid, None)
                    self.anim[sid] = fade_frames(max(self.glow[sid], 0.6))
        self._draw_pill(running)
        if hasattr(self, "tray"):
            self.tray.update_menu()

    # --- сторож: сам замечает, что сервис перестал открываться, и подбирает пресет ---

    def _watch(self) -> None:
        self.after(WATCH_SEC * 1000, self._watch)
        if not self.cfg.get("watchdog", True) or self.busy or not self.engine.running:
            return
        testable = [s for s in self.selected() if s in engine.TEST_URLS]
        if not testable:
            return

        def check():
            res = engine.check_details(testable)
            self.post(lambda: self._watch_result(res))
        threading.Thread(target=check, daemon=True).start()

    def _watch_result(self, details: dict) -> None:
        if self.busy:
            return
        self.set_results(details)
        bad = [s for s, r in details.items() if r]
        self.refresh()
        if not bad:
            self.watch_strikes = 0
            return
        self.watch_strikes += 1
        if self.watch_strikes < 2:   # одна неудача — может быть случайной, ждём следующей проверки
            return
        self.watch_strikes = 0
        names = ", ".join(svc_name(s) for s in bad)
        self.log(tr("msg.watch_fail", names=names))
        self.notify(tr("tray.fail_title"), tr("msg.watch_fail", names=names))
        self.run_bg(self._autofix)

    def _autofix(self) -> None:
        self.run_autodetect()
        bad = [svc_name(s) for s, ok in self.results.items() if not ok]
        if bad:
            text = tr("msg.watch_broken", names=", ".join(bad))
        else:
            text = tr("msg.watch_fixed", name=self.preset_summary())
        self.log(text)
        self.notify(tr("tray.fail_title") if bad else "Lotus", text)

    # --- обновления ---

    def check_updates(self, quiet: bool = False) -> None:
        """Раз в сутки (и по кнопке): IP игр, если устарели; новые версии zapret и Lotus."""
        if quiet:
            self.after(UPDATE_SEC * 1000, lambda: self.check_updates(quiet=True))

        def go():
            try:
                if updater.ipset_is_old():
                    n = updater.update_ipset()
                    count_ipset.cache = None
                    self.log(tr("msg.ipset", n=n))
                z = updater.check_zapret()
                l = None if quiet else updater.check_lotus()   # сам Lotus проверяется раз в час
            except Exception as e:
                if not quiet:
                    self.log(tr("msg.upd_err", e=e))
                return
            self.updates["zapret"] = z
            if z:
                self.log(tr("msg.upd_zapret", v=z))
                self.notify(tr("tray.update_title"), tr("msg.upd_zapret", v=z))
            if l:
                self.post(lambda: self._on_lotus_update(l))
            elif not z and not quiet:
                self.log(tr("msg.upd_none", v=VERSION, z=updater.zapret_version()))
            self.post(self._reopen_settings)
        threading.Thread(target=go, daemon=True).start()

    def update_zapret(self) -> None:
        tag = self.updates.get("zapret")
        if not tag:
            return

        def go():
            self.engine.stop()   # файлы winws заняты, пока он работает
            updater.update_zapret(tag)
            self.updates["zapret"] = None
            self.log(tr("msg.upd_zapret_done", v=tag))
            self.dirty = True
            self._apply_loop()
            self.post(self._reopen_settings)
        self.run_bg(go)

    def _lotus_check(self) -> None:
        """Раз в час: нет ли новой версии Lotus на GitHub."""
        self.after(LOTUS_SEC * 1000, self._lotus_check)

        def go():
            try:
                info = updater.check_lotus()
            except Exception:
                return   # нет сети или GitHub недоступен — попробуем через час
            if info:
                self.post(lambda: self._on_lotus_update(info))
        threading.Thread(target=go, daemon=True).start()

    def _on_lotus_update(self, info: tuple) -> None:
        self.updates["lotus"] = info
        if self.installing:
            return
        if self.cfg.get("auto_update", True) and updater.is_installed():
            if self.busy:   # идёт включение/подбор — поставим чуть позже
                self.after(60_000, lambda: self._on_lotus_update(info))
                return
            self.log(tr("msg.upd_auto", v=info[0]))
            self.notify(tr("tray.update_title"), tr("msg.upd_auto", v=info[0]))
            self.install_lotus_update(silent=True)
            return
        if self.cfg.get("notified_version") != info[0]:   # о каждой версии напоминаем один раз
            self.cfg["notified_version"] = info[0]
            engine.save_config(self.cfg)
            self.log(tr("msg.upd_lotus", v=info[0]))
            self.notify(tr("tray.update_title"), tr("msg.upd_lotus", v=info[0]))
        self._reopen_settings()

    def install_lotus_update(self, silent: bool = False) -> None:
        info = self.updates.get("lotus")
        if not info or self.installing:
            return
        self.installing = True   # следующая ежечасная проверка не должна запустить установку ещё раз

        def go():
            self.log(tr("msg.upd_downloading"))
            try:
                updater.install_lotus(info[1], info[2], silent=silent)
            except Exception:
                self.installing = False   # не вышло — попробуем при следующей проверке
                raise
            self.post(self.quit_app)   # установщик заменит файлы и запустит новую версию
        self.run_bg(go)

    # --- действия ---

    def on_tile(self, sid: str) -> None:
        sel = self.selected()
        sel.remove(sid) if sid in sel else sel.append(sid)
        self.cfg["services"] = sel
        engine.save_config(self.cfg)
        self.results.pop(sid, None)
        self.reasons.pop(sid, None)
        self.apply()
        self.refresh()

    def save_custom_sites(self, text: str) -> None:
        sites = []
        for line in text.splitlines():
            d = re.sub(r"^\s*(https?://)?(www\.)?", "", line.strip().lower()).split("/")[0].strip()
            if d and "." in d and d not in sites:
                sites.append(d)
        (engine.LISTS / "custom.txt").write_text("\n".join(sites) + ("\n" if sites else ""), encoding="utf-8")
        self.log(tr("msg.sites_saved", n=len(sites)))
        if "custom" in self.selected():
            self.engine.invalidate()   # тот же набор сервисов, но другие домены — перезапустить
            self.apply()
        self.refresh()

    def open_settings(self) -> None:
        if self.settings and self.settings.winfo_exists():
            self.settings.focus()
            return
        self.settings = Settings(self)

    def hide_to_tray(self) -> None:
        if self.settings and self.settings.winfo_exists():
            self.settings.destroy()
        self.withdraw()
        if not self.tray_hint_shown:
            self.tray_hint_shown = True
            self.notify(tr("tray.hint_title"), tr("tray.hint"))

    def show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def set_autostart(self, on: bool) -> None:
        try:
            autostart.enable() if on else autostart.disable()
            self.autostart_on = autostart.is_enabled()
            self.log(tr("msg.autostart_on") if self.autostart_on else tr("msg.autostart_off"))
        except Exception as e:
            self.log(tr("msg.autostart_err", e=e))
        self.tray.update_menu()
        if self.settings and self.settings.winfo_exists():
            self.settings.sync_switches()

    def quit_app(self) -> None:
        self.engine.stop()
        try:
            self.tray.visible = False   # убрать значок сразу, иначе в трее остаётся «призрак»
        except Exception:
            pass
        self.tray.stop()
        try:
            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:
            pass
        self.destroy()


class Settings(ctk.CTkToplevel):
    def __init__(self, app: App) -> None:
        super().__init__(app, fg_color=R.T.window_bg)
        self.app = app
        self.title(tr("set.title"))
        self.geometry(f"{W}x600")
        self.resizable(False, False)
        self.transient(app)
        self.after(150, self.lift)
        self.after(250, lambda: self.iconbitmap(str(ICONS / f"{R.T.logo}.ico")))

        body = ctk.CTkScrollableFrame(self, fg_color=R.T.window_bg,
                                      scrollbar_button_color=R.T.border,
                                      scrollbar_button_hover_color=R.T.accent_hex)
        body.pack(fill="both", expand=True, padx=(4, 0), pady=(4, 8))

        def section(text):
            ctk.CTkLabel(body, text=text, text_color=R.T.muted,
                         font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(14, 4))

        def button(master, text, cmd):
            return ctk.CTkButton(master, text=text, command=cmd, height=34, corner_radius=10,
                                 fg_color=R.T.field_bg, border_width=1, border_color=R.T.border,
                                 text_color=R.T.text, hover_color=R.T.hover)

        def switch(text, value, cmd):
            sw = ctk.CTkSwitch(body, text=text, text_color=R.T.text, progress_color=R.T.accent_hex,
                               button_color="#FFFFFF", button_hover_color="#FFFFFF",
                               fg_color=R.T.border, command=cmd)
            sw.select() if value else sw.deselect()
            sw.pack(anchor="w", padx=14, pady=(10, 0))
            return sw

        # оформление и язык
        section(tr("set.theme", name=tr(f"theme.{R.T.id}")))
        swatches = ctk.CTkFrame(body, fg_color="transparent")
        swatches.pack(fill="x", padx=14)
        for th in THEMES:
            current = th is R.T
            ctk.CTkButton(swatches, text="", width=32, height=32, corner_radius=16,
                          fg_color=th.swatch, hover_color=th.swatch,
                          border_width=3 if current else 1,
                          border_color=R.T.text if current else R.T.border,
                          command=lambda t=th.id: app.apply_theme(t)).pack(side="left", padx=(0, 8))

        section(tr("set.lang"))
        langs = {name: code for code, name in i18n.LANGS.items()}
        lang = ctk.CTkSegmentedButton(body, values=list(langs), height=32, corner_radius=10,
                                      fg_color=R.T.field_bg, selected_color=R.T.accent_hex,
                                      selected_hover_color=R.T.accent_hex,
                                      unselected_color=R.T.field_bg, unselected_hover_color=R.T.hover,
                                      text_color=R.T.text,
                                      command=lambda name: app.apply_lang(langs[name]))
        lang.set(i18n.LANGS[i18n.LANG])
        lang.pack(fill="x", padx=14)

        # пресет
        section(tr("set.preset"))
        # в раскрытом списке — название и когда его выбирать; в закрытом — только название
        self.names = {f"{tr(f'preset.{p.id}')}  ·  {tr(f'phint.{p.id}')}": p.id for p in PRESETS}
        self.preset = ctk.CTkOptionMenu(body, values=list(self.names), height=34, corner_radius=10,
                                        command=self.on_preset, fg_color=R.T.field_bg,
                                        button_color=R.T.border, button_hover_color=R.T.accent_hex,
                                        text_color=R.T.text, dropdown_fg_color=R.T.field_bg,
                                        dropdown_text_color=R.T.text, dropdown_hover_color=R.T.border)
        self.preset.set(tr(f"preset.{app.cfg['preset']}"))
        self.preset.pack(fill="x", padx=14)
        ctk.CTkLabel(body, text=tr(f"pdesc.{app.cfg['preset']}"), text_color=R.T.text_off,
                     font=ctk.CTkFont(size=11), wraplength=290, justify="left").pack(anchor="w", padx=14, pady=(4, 0))
        if app.cfg.get("overrides"):
            extra = ", ".join(f"{svc_name(s)} — {tr(f'preset.{p}')}" for s, p in app.cfg["overrides"].items())
            ctk.CTkLabel(body, text=tr("set.overrides", list=extra), text_color=R.T.muted,
                         font=ctk.CTkFont(size=11), wraplength=290, justify="left").pack(anchor="w", padx=14, pady=(4, 0))
        button(body, tr("set.auto"), self.on_auto).pack(fill="x", padx=14, pady=(6, 0))
        ctk.CTkLabel(body, text=tr("pdesc.auto"), text_color=R.T.muted, font=ctk.CTkFont(size=11),
                     wraplength=290, justify="left").pack(anchor="w", padx=14, pady=(4, 0))

        # инструменты
        section(tr("set.tools"))
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", padx=14)
        row.columnconfigure((0, 1), weight=1, uniform="col")
        button(row, tr("set.check"), self.on_check).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        button(row, tr("set.ipset"), self.on_update_ipset).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        button(body, tr("set.tg"), self.on_tg).pack(fill="x", padx=14, pady=(6, 0))

        # свои сайты
        section(tr("set.sites"))
        self.sites = ctk.CTkTextbox(body, height=90, corner_radius=10, fg_color=R.T.field_bg,
                                    text_color=R.T.text, border_width=1, border_color=R.T.border,
                                    font=ctk.CTkFont(family="Consolas", size=12))
        self.sites.insert("1.0", "\n".join(engine.domains("custom")))
        self.sites.pack(fill="x", padx=14)
        button(body, tr("set.sites_save"),
               lambda: app.save_custom_sites(self.sites.get("1.0", "end"))).pack(fill="x", padx=14, pady=(6, 0))

        # переключатели
        self.watch = switch(tr("set.watch"), app.cfg.get("watchdog", True), self.on_watch)
        self.autostart = switch(tr("set.autostart"), app.autostart_on,
                                lambda: app.set_autostart(bool(self.autostart.get())))
        if updater.is_installed():   # портативный Lotus.exe сам не обновляется — только сообщает
            self.auto_update = switch(tr("set.auto_update"), app.cfg.get("auto_update", True),
                                      self.on_auto_update)

        # обновления
        section(tr("set.updates"))
        ctk.CTkLabel(body, text=tr("set.version", v=VERSION, z=updater.zapret_version()),
                     text_color=R.T.text, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        button(body, tr("set.check_upd"), lambda: app.check_updates()).pack(fill="x", padx=14, pady=(6, 0))
        if app.updates.get("zapret"):
            button(body, tr("set.upd_zapret", v=app.updates["zapret"]),
                   app.update_zapret).pack(fill="x", padx=14, pady=(6, 0))
        if app.updates.get("lotus"):
            button(body, tr("set.upd_lotus", v=app.updates["lotus"][0]),
                   app.install_lotus_update).pack(fill="x", padx=14, pady=(6, 0))

        # журнал
        section(tr("set.log"))
        self.logbox = ctk.CTkTextbox(body, height=150, corner_radius=10, fg_color=R.T.field_bg,
                                     text_color=R.T.text, border_width=1, border_color=R.T.border,
                                     font=ctk.CTkFont(family="Consolas", size=11))
        self.logbox.pack(fill="x", padx=14, pady=(0, 8))
        for line in app.log_lines[-50:]:
            self.append_log(line)

    def sync_switches(self) -> None:
        self.autostart.select() if self.app.autostart_on else self.autostart.deselect()

    def append_log(self, text: str) -> None:
        self.logbox.insert("end", text + "\n")
        self.logbox.see("end")

    def on_auto_update(self) -> None:
        self.app.cfg["auto_update"] = bool(self.auto_update.get())
        engine.save_config(self.app.cfg)

    def on_watch(self) -> None:
        self.app.cfg["watchdog"] = bool(self.watch.get())
        engine.save_config(self.app.cfg)

    def on_preset(self, name: str) -> None:
        """Ручной выбор — один пресет для всех сервисов (подобранные по отдельности сбрасываются)."""
        a = self.app
        a.cfg["preset"] = self.names[name]
        a.cfg["overrides"] = {}
        engine.save_config(a.cfg)
        self.preset.set(tr(f"preset.{a.cfg['preset']}"))
        a.log(tr("msg.preset", name=tr(f"preset.{a.cfg['preset']}")))
        if a.selected():
            a.apply()
        a.post(a._reopen_settings)

    def on_auto(self) -> None:
        a = self.app

        def go():
            a.run_autodetect()
            a.post(a._reopen_settings)
        a.run_bg(go)

    def on_check(self) -> None:
        a = self.app

        def go():
            a.log(tr("msg.checking"))
            details = engine.check_details(a.selected())
            a.set_results(details)
            for k, r in details.items():
                a.log(tr("msg.check_line", name=svc_name(k), res=tr(r or "st.ok")))
        a.run_bg(go)

    def on_update_ipset(self) -> None:
        a = self.app

        def go():
            n = updater.update_ipset()
            count_ipset.cache = None
            a.log(tr("msg.ipset", n=n))
        a.run_bg(go)

    def on_tg(self) -> None:
        a = self.app
        link = engine.tg_link(a.cfg["tg_secret"])
        try:
            os.startfile(link)
            a.log(tr("msg.tg_open"))
        except OSError:
            self.clipboard_clear()
            self.clipboard_append(link)
            a.log(tr("msg.tg_copy"))


def count_ipset() -> int:
    if getattr(count_ipset, "cache", None) is None:
        try:
            text = (engine.LISTS / "ipset-games.txt").read_text(encoding="utf-8")
            count_ipset.cache = sum(1 for line in text.splitlines() if line.strip())
        except OSError:
            count_ipset.cache = 0
    return count_ipset.cache


def run_tgproxy(args: list[str]) -> None:
    """Режим Telegram-прокси: Lotus.exe --tgproxy ... (так .exe запускает сам себя)."""
    sys.path.insert(0, str(engine.TG_DIR))
    for name in ("stdout", "stderr"):  # в оконном .exe их нет, а прокси туда пишет
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
    from proxy.tg_ws_proxy import main
    sys.argv = ["tg-ws-proxy", *args]
    main()


class ShowEvent:
    """Именованное событие Windows: второй запуск Lotus «стучится» в первый."""
    NAME = "Local\\LotusShowWindow"

    def __init__(self) -> None:
        k32 = ctypes.windll.kernel32
        self.k32 = k32
        self.h = k32.CreateEventW(None, False, False, self.NAME)   # автосброс

    def is_set(self) -> bool:
        return self.k32.WaitForSingleObject(self.h, 0) == 0

    def clear(self) -> None:
        pass  # событие с автосбросом уже сброшено проверкой

    def signal(self) -> None:
        self.k32.SetEvent(self.h)


def already_running() -> bool:
    """Одна копия Lotus: держим именованный мьютекс до выхода из программы."""
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\LotusSingleInstance")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


if __name__ == "__main__":
    if sys.argv[1:2] == ["--tgproxy"]:
        run_tgproxy(sys.argv[2:])
        sys.exit(0)
    if not engine.is_admin() and not os.environ.get("LOTUS_SKIP_ADMIN"):
        try:
            engine.relaunch_as_admin()
        except Exception:
            messagebox.showerror("Lotus", tr("admin"))
    show = ShowEvent()
    if already_running():
        show.signal()   # Lotus уже в трее — просто показать его окно
        sys.exit(0)
    engine.install_runtime()
    updated = "--updated" in sys.argv   # запущен установщиком после автообновления
    App(start_hidden="--tray" in sys.argv or updated, show_event=show, updated=updated).mainloop()
