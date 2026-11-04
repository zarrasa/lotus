"""Движок: собирает команду для winws.exe (zapret), запускает/останавливает, проверяет доступ."""

import ctypes
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from i18n import svc_name, tr
from services import (DISCORD_VOICE_PORTS, GAME_PORTS, PRESETS, PRESETS_BY_ID,
                      SERVICES_BY_ID, Preset)

FROZEN = getattr(sys, "frozen", False)
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # внутри .exe — временная папка распаковки
# Внутри .exe всё рабочее живёт в %APPDATA%\Lotus: настройки, логи, обновляемые списки
# и winws с драйвером — драйвер должен запускаться всегда из одного места, а не из временной папки.
DATA = Path(os.environ.get("APPDATA", Path.home())) / "Lotus" if FROZEN else Path(__file__).parent
BIN = DATA / "bin" if FROZEN else ROOT / "bin"
FAKE = BIN / "fake"
LISTS = DATA / "lists" if FROZEN else ROOT / "lists"
CONFIG = DATA / "config.json"
LOG = DATA / "winws.log"
TG_DIR = ROOT / "tgproxy"
TG_LOG = DATA / "tgproxy.log"
TG_PORT = 1443
FLOWSEAL = ROOT / "flowseal"   # стратегии Flowseal для YouTube + Discord (tools/import_flowseal.py)
FLOWSEAL_SERVICES = ("youtube", "discord")
GDPI_DIR = BIN / "gdpi"
GDPI_LOG = DATA / "goodbyedpi.log"
# DNS-запросы уходят на Яндекс DNS через нестандартный порт 1253 — провайдер их не подменяет
DNS_REDIRECT = ["--dns-addr", "77.88.8.8", "--dns-port", "1253",
                "--dnsv6-addr", "2a02:6b8::feed:0ff", "--dnsv6-port", "1253"]

NO_WINDOW = 0x08000000

# Что открываем при проверке. Скачиваем больше 16 КБ — провайдеры часто режут именно после 16 КБ.
TEST_URLS = {s.id: s.test_url for s in SERVICES_BY_ID.values() if s.test_url}


def domains(service_id: str) -> list[str]:
    """Домены из списка сервиса (для «Своих сайтов» список ведёт пользователь)."""
    svc = SERVICES_BY_ID[service_id]
    if not svc.hostlist:
        return []
    try:
        text = (LISTS / svc.hostlist).read_text(encoding="utf-8")
    except OSError:
        return []
    return [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def install_runtime() -> None:
    """Внутри .exe: разложить winws и списки в %APPDATA%\\Lotus.
    Бинарники обновляются, если отличаются; списки — только если их ещё нет
    (ipset игр мог быть обновлён кнопкой и его нельзя затирать)."""
    if not FROZEN:
        return
    # zapret мог быть обновлён из настроек до версии новее встроенной — его файлы не откатываем
    ver = lambda p: tuple(int(x) for x in re.findall(r"\d+", p.read_text()) or [0]) if p.exists() else (0,)
    keep_zapret = ver(DATA / "bin" / "ZAPRET_VERSION") > ver(ROOT / "bin" / "ZAPRET_VERSION")
    zapret_files = {"winws.exe", "WinDivert.dll", "WinDivert64.sys", "cygwin1.dll", "ZAPRET_VERSION"}
    for sub, overwrite in (("bin", True), ("lists", False)):
        for src in (ROOT / sub).rglob("*"):
            if src.is_dir():
                continue
            dst = DATA / sub / src.relative_to(ROOT / sub)
            if keep_zapret and sub == "bin" and (src.name in zapret_files or src.parent.name == "fake"):
                continue
            if dst.exists() and (not overwrite or dst.stat().st_size == src.stat().st_size):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                dst.write_bytes(src.read_bytes())
            except OSError:
                pass  # winws из прошлого запуска ещё держит файл — оставляем старый


# ---------- настройки ----------

DEFAULT_CONFIG = {"services": ["youtube", "discord"], "preset": "general"}


def load_config() -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        cfg = {**DEFAULT_CONFIG, **json.loads(CONFIG.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        cfg = dict(DEFAULT_CONFIG)
    if "tg_secret" not in cfg:  # ключ для Telegram-прокси создаётся один раз
        cfg["tg_secret"] = os.urandom(16).hex()
        save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- права администратора ----------

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin() -> None:
    """Перезапустить программу с правами админа (появится окно UAC)."""
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, ""
    else:
        exe, params = sys.executable, f'"{Path(sys.argv[0]).resolve()}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


# ---------- стратегии Flowseal ----------

_flowseal_cache: dict | None = None


def flowseal() -> dict:
    """{"version": ..., "strategies": [{"name": "general (ALT)", "profiles": [[...], ...]}, ...]}"""
    global _flowseal_cache
    if _flowseal_cache is None:
        try:
            _flowseal_cache = json.loads((FLOWSEAL / "strategies.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _flowseal_cache = {"version": "?", "strategies": []}
    return _flowseal_cache


def strategy_names() -> list[str]:
    return [s["name"] for s in flowseal()["strategies"]]


def strategy_profiles(name: str) -> list[list[str]]:
    lists, fake = str(FLOWSEAL / "lists") + "\\", str(FLOWSEAL / "fake") + "\\"
    for s in flowseal()["strategies"]:
        if s["name"] == name:
            return [[t.replace("{FS_LISTS}/", lists).replace("{FS_FAKE}/", fake) for t in p]
                    for p in s["profiles"]]
    return []


# ---------- сборка команды ----------

def _sub(args: list[str]) -> list[str]:
    return [a.replace("{FAKE}/", str(FAKE) + "\\") for a in args]


def build_args(service_ids: list[str], preset: Preset, overrides: dict[str, str] | None = None,
               strategy: str | None = None) -> list[str]:
    """Команда winws. У каждого сервиса может быть свой пресет (overrides: id -> id пресета):
    у одного провайдера YouTube и Discord часто режутся по-разному, и одного пресета на всех мало.
    strategy — стратегия Flowseal для YouTube и Discord: её профили идут первыми и заменяют
    наши правила для этих двух сервисов (включая голос Discord)."""
    overrides = overrides or {}
    pick = lambda sid: PRESETS_BY_ID.get(overrides.get(sid), preset)
    fs_profiles = strategy_profiles(strategy) if strategy and any(s in FLOWSEAL_SERVICES for s in service_ids) else []
    if fs_profiles:
        service_ids = [s for s in service_ids if s not in FLOWSEAL_SERVICES]
    services = [SERVICES_BY_ID[s] for s in service_ids if s in SERVICES_BY_ID]
    groups: dict[str, list[str]] = {}   # id пресета -> hostlist'ы сервисов с этим пресетом
    for s in services:
        if s.hostlist and not s.gdpi:   # домены Steam обходит GoodbyeDPI, не winws
            groups.setdefault(pick(s.id).id, []).append(f"--hostlist={LISTS / s.hostlist}")
    voice = any(s.voice for s in services)
    games = [s for s in services if s.game]
    game = bool(games)

    wf_tcp, wf_udp = ["80", "443"], ["443"]
    if voice:
        wf_udp.append(DISCORD_VOICE_PORTS)
    if game:
        wf_tcp.append(GAME_PORTS)
        wf_udp.append(GAME_PORTS)

    # порты, которые ловят профили Flowseal (например, голос Discord по TCP 2053-8443)
    for p in fs_profiles:
        for t in p:
            for opt, target in (("--filter-tcp=", wf_tcp), ("--filter-udp=", wf_udp)):
                if t.startswith(opt):
                    target.extend(x for x in t[len(opt):].split(",") if x not in target)

    args = [str(BIN / "winws.exe"), f"--wf-tcp={','.join(wf_tcp)}", f"--wf-udp={','.join(wf_udp)}"]
    profiles: list[list[str]] = list(fs_profiles)   # Flowseal первыми: winws берёт первый подходящий

    for pid, hostlists in groups.items():
        p = PRESETS_BY_ID[pid]
        profiles.append(["--filter-udp=443", *hostlists, *_sub(p.quic)])
        profiles.append(["--filter-tcp=80", *hostlists, *_sub(p.http)])
        profiles.append(["--filter-tcp=443", *hostlists, *_sub(p.tls)])

    if voice:
        profiles.append([f"--filter-udp={DISCORD_VOICE_PORTS}", "--filter-l7=discord,stun",
                         "--dpi-desync=fake", "--dpi-desync-repeats=6"])

    for g in games:
        ipset = f"--ipset={LISTS / g.ipset}"
        # у Steam HTTPS (443) уже обрабатывает GoodbyeDPI — два обхода на одних пакетах ломают вход
        tcp = GAME_PORTS if g.gdpi else f"443,{GAME_PORTS}"
        profiles.append([f"--filter-tcp={tcp}", ipset, *_sub(pick(g.id).tls)])
        profiles.append([f"--filter-udp={GAME_PORTS}", ipset,
                         "--dpi-desync=fake", "--dpi-desync-autottl=2", "--dpi-desync-repeats=12",
                         "--dpi-desync-any-protocol=1",
                         f"--dpi-desync-fake-unknown-udp={FAKE / 'quic_initial_www_google_com.bin'}",
                         "--dpi-desync-cutoff=n3"])

    for i, p in enumerate(profiles):
        if i:
            args.append("--new")
        args.extend(p)
    return args


# ---------- запуск ----------

def _alive(p: subprocess.Popen | None) -> bool:
    return p is not None and p.poll() is None


def _terminate(p: subprocess.Popen | None) -> None:
    if _alive(p):
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()


def _console_python() -> str:
    """python.exe рядом с pythonw.exe — у pythonw нет stderr, прокси пишет в него логи."""
    exe = Path(sys.executable)
    alt = exe.with_name("python.exe")
    return str(alt if alt.exists() else exe)


def tg_link(secret: str) -> str:
    return f"tg://proxy?server=127.0.0.1&port={TG_PORT}&secret=dd{secret}"


class Engine:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None      # winws.exe
        self.tg_proc: subprocess.Popen | None = None   # tg-ws-proxy
        self.gdpi_proc: subprocess.Popen | None = None # GoodbyeDPI (Steam + DNS)
        self.winws_key: tuple | None = None            # с какими сервисами/пресетом запущен winws
        self.gdpi_key: tuple | None = None

    @property
    def running(self) -> bool:
        return _alive(self.proc) or _alive(self.tg_proc) or _alive(self.gdpi_proc)

    def start(self, service_ids: list[str], preset_id: str, tg_secret: str | None = None,
              overrides: dict[str, str] | None = None, strategy: str | None = None) -> None:
        """Привести запущенное к выбранному. Перезапускается только то, что изменилось:
        например, включение Telegram не рвёт обход YouTube, и наоборот.
        overrides — свой пресет для отдельных сервисов (id сервиса -> id пресета)."""
        if not service_ids:
            raise ValueError(tr("eng.no_services"))
        svc = [SERVICES_BY_ID[s] for s in service_ids]
        # сервис со списком доменов, но пустым («Свои сайты» без сайтов) — пропускаем
        svc = [s for s in svc if not s.hostlist or domains(s.id)]
        # winws: всё, кроме Telegram; у Steam — только игровые сервера Valve (ipset)
        dpi = [s.id for s in svc if not s.tgproxy and (not s.gdpi or s.ipset)]
        gdpi = tuple(sorted(s.id for s in svc if s.gdpi))
        overrides = {s: p for s, p in (overrides or {}).items() if s in dpi and p in PRESETS_BY_ID}
        key = (tuple(sorted(dpi)), preset_id, tuple(sorted(overrides.items())), strategy)

        if not gdpi:
            self._stop_gdpi()
        elif not (_alive(self.gdpi_proc) and self.gdpi_key == gdpi):
            self._stop_gdpi()
            self._start_gdpi(list(gdpi))
            self.gdpi_key = gdpi
        if not dpi:
            self._stop_winws()
        elif not (_alive(self.proc) and self.winws_key == key):
            self._stop_winws()
            kill_stray()
            self._start_winws(dpi, preset_id, overrides, strategy)
            self.winws_key = key

        if tg_secret and any(s.tgproxy for s in svc):
            if not _alive(self.tg_proc):
                self._start_tg(tg_secret)
        else:
            _terminate(self.tg_proc)
            self.tg_proc = None

    def _stop_winws(self) -> None:
        _terminate(self.proc)
        self.proc = self.winws_key = None

    def _start_winws(self, service_ids: list[str], preset_id: str, overrides: dict[str, str],
                     strategy: str | None = None) -> None:
        if not (BIN / "winws.exe").exists():
            raise FileNotFoundError(f"Нет {BIN / 'winws.exe'}")
        args = build_args(service_ids, PRESETS_BY_ID[preset_id], overrides, strategy)
        log = open(LOG, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(args, cwd=BIN, stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=NO_WINDOW)
        time.sleep(1.5)
        if not _alive(self.proc):
            raise RuntimeError(tr("eng.winws_died", log=read_log_tail()))

    def _start_gdpi(self, service_ids: list[str]) -> None:
        """GoodbyeDPI в режиме -9 (как 2_any_country_dnsredir.cmd), но трюки с пакетами —
        только для доменов выбранных сервисов; DNS перенаправляется для всей системы."""
        exe = GDPI_DIR / "goodbyedpi.exe"
        if not exe.exists():
            raise FileNotFoundError(f"Нет {exe}")
        if other_goodbyedpi_running():
            raise RuntimeError(tr("eng.gdpi_other"))
        lists = [a for s in service_ids for a in ("--blacklist", str(LISTS / SERVICES_BY_ID[s].hostlist))]
        args = [str(exe), "-9", *lists, *DNS_REDIRECT]
        log = open(GDPI_LOG, "w", encoding="utf-8", errors="replace")
        self.gdpi_proc = subprocess.Popen(args, cwd=GDPI_DIR, stdout=log, stderr=subprocess.STDOUT,
                                          creationflags=NO_WINDOW)
        time.sleep(1.5)
        if not _alive(self.gdpi_proc):
            raise RuntimeError(tr("eng.gdpi_died", log=read_log_tail(GDPI_LOG)))
        flush_dns()  # иначе в кэше Windows так и останутся подменённые адреса (127.0.0.1)

    def _stop_gdpi(self) -> None:
        was = _alive(self.gdpi_proc)
        _terminate(self.gdpi_proc)
        self.gdpi_proc = self.gdpi_key = None
        if was:
            flush_dns()

    def _start_tg(self, secret: str) -> None:
        # внутри .exe прокси запускается тем же Lotus.exe с флагом --tgproxy
        launcher = [sys.executable, "--tgproxy"] if FROZEN else [_console_python(), "-m", "proxy.tg_ws_proxy"]
        args = [*launcher, "--port", str(TG_PORT), "--secret", secret, "--log-file", str(TG_LOG)]
        self.tg_proc = subprocess.Popen(args, cwd=DATA if FROZEN else TG_DIR, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
        time.sleep(1.5)
        if not _alive(self.tg_proc):
            raise RuntimeError(tr("eng.tg_died", log=read_log_tail(TG_LOG)))

    def invalidate(self) -> None:
        """Списки доменов поменялись — при следующем start перезапустить winws и GoodbyeDPI."""
        self.winws_key = self.gdpi_key = None

    def stop(self) -> None:
        self._stop_winws()
        self._stop_gdpi()
        _terminate(self.tg_proc)
        self.tg_proc = None


def other_goodbyedpi_running() -> bool:
    """Наш GoodbyeDPI к этому моменту уже остановлен — значит, любой найденный чужой."""
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq goodbyedpi.exe", "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
    return "goodbyedpi.exe" in r.stdout.lower()


def flush_dns() -> None:
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True, creationflags=NO_WINDOW)


def kill_stray() -> None:
    """Убить winws, оставшийся от прошлого запуска или от другого zapret."""
    subprocess.run(["taskkill", "/F", "/IM", "winws.exe"], capture_output=True,
                   creationflags=NO_WINDOW)


def read_log_tail(path: Path = LOG, n: int = 15) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return ""


# ---------- проверка и автоподбор ----------

def check_url(url: str, need: int = 64 * 1024, timeout: float = 8) -> bool:
    """True, если удалось скачать хотя бы need байт (или страницу целиком)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    got = 0
    deadline = time.monotonic() + timeout
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            while got < need:
                if time.monotonic() > deadline:
                    return False
                chunk = r.read(8192)
                if not chunk:
                    return got > 0
                got += len(chunk)
        return True
    except Exception:
        return False


# Дополнительные проверки: сайт может открываться, а видео/голос — нет (их режут отдельно).
# googlevideo.com — сервера видео YouTube; discord.media — голосовые сервера Discord
# (latency.discord.media/rtc сам клиент Discord опрашивает, выбирая регион голоса).
EXTRA_CHECKS = {
    "youtube": ("https://redirector.googlevideo.com/report_mapping?di=no", "st.video_fail"),
    "discord": ("https://latency.discord.media/rtc", "st.voice_fail"),
}


def check_detail(service_id: str, retry: bool = False) -> str | None:
    """None — всё открывается; иначе ключ статуса: st.fail / st.video_fail / st.voice_fail.
    retry — при неудаче проверить ещё раз: первое соединение бывает медленным (DNS, прогрев)."""
    for attempt in range(2 if retry else 1):
        if not check_url(TEST_URLS[service_id]):
            result = "st.fail"
            continue
        extra = EXTRA_CHECKS.get(service_id)
        if extra and not check_url(extra[0], need=1):
            result = extra[1]
            continue
        return None
    return result


def check_details(service_ids: list[str], retry: bool = True) -> dict[str, str | None]:
    """Проверить сервисы одновременно (по очереди при 10 пресетах автоподбор шёл бы минуты)."""
    ids = [s for s in service_ids if s in TEST_URLS]
    if not ids:
        return {}
    with ThreadPoolExecutor(max_workers=len(ids)) as pool:
        return dict(zip(ids, pool.map(lambda s: check_detail(s, retry), ids)))


def check_services(service_ids: list[str]) -> dict[str, bool]:
    """Быстрая проверка для автоподбора — без повтора, иначе перебор 10 пресетов затянется."""
    return {s: r is None for s, r in check_details(service_ids, retry=False).items()}


def autodetect_strategy(engine: Engine, service_ids: list[str], preset_id: str,
                        on_progress=print) -> str | None:
    """Перебирает стратегии Flowseal для YouTube + Discord: первая, где открылись оба;
    если такой нет — та, где открылось больше; None — если не помогла ни одна."""
    testable = [s for s in FLOWSEAL_SERVICES if s in service_ids]
    dpi = [s for s in service_ids if not SERVICES_BY_ID[s].tgproxy and not SERVICES_BY_ID[s].gdpi]
    best, best_score = None, 0
    for name in strategy_names():
        on_progress(tr("eng.try", name=name))
        try:
            engine.start(dpi, preset_id, strategy=name)
            time.sleep(1)
            res = check_services(testable)
        except Exception as e:
            on_progress(tr("eng.try_err", e=e))
            continue
        finally:
            engine.stop()
        on_progress("  " + ", ".join(f"{svc_name(k)}: {tr('eng.yes') if v else tr('eng.no')}"
                                     for k, v in res.items()))
        score = sum(res.values())
        if score == len(testable):
            return name
        if score > best_score:
            best, best_score = name, score
    return best


def autodetect(engine: Engine, service_ids: list[str], on_progress=print,
               exclude: tuple = ()) -> tuple[str, dict[str, str]] | None:
    """Перебирает пресеты и для каждого сервиса запоминает первый, при котором он открылся.
    Возвращает (основной пресет, {сервис: свой пресет}) или None, если не помог ни один.
    Основной — тот, что подошёл большинству; свой пресет — только у тех, кому нужен другой.
    exclude — сервисы, которые подбираются отдельно (YouTube и Discord — по стратегиям Flowseal)."""
    # от пресета zapret зависят только сервисы, которые идут через winws по списку доменов
    testable = [s for s in service_ids if s in TEST_URLS and s not in exclude
                and not SERVICES_BY_ID[s].gdpi and not SERVICES_BY_ID[s].tgproxy]
    if not testable:
        if exclude:
            return None   # подбирать нечего — всё нужное подбирается отдельно
        testable = ["youtube", "discord"]
    dpi = [s for s in service_ids if not SERVICES_BY_ID[s].tgproxy and not SERVICES_BY_ID[s].gdpi] or testable
    works: dict[str, list[str]] = {s: [] for s in testable}   # сервис -> пресеты, где открылся
    for p in PRESETS:
        on_progress(tr("eng.try", name=tr(f"preset.{p.id}")))
        try:
            engine.start(dpi, p.id)
            time.sleep(1)
            res = check_services(testable)
        except Exception as e:
            on_progress(tr("eng.try_err", e=e))
            continue
        finally:
            engine.stop()
        on_progress("  " + ", ".join(f"{svc_name(k)}: {tr('eng.yes') if v else tr('eng.no')}"
                                     for k, v in res.items()))
        for s, ok in res.items():
            if ok:
                works[s].append(p.id)
        if all(res.values()):   # этот пресет подошёл всем — дальше искать незачем
            return p.id, {}
    score = {p.id: sum(p.id in w for w in works.values()) for p in PRESETS}
    main = max(PRESETS, key=lambda p: score[p.id]).id   # при равенстве — первый по списку
    if score[main] == 0:
        return None
    overrides = {s: w[0] for s, w in works.items() if w and main not in w}
    return main, overrides
