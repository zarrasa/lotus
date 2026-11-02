"""Обновления: самого Lotus (релизы на GitHub), движка zapret и списков IP игр."""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import engine
import update_lists
from version import UPDATE_REPO, VERSION

ZAPRET_REPO = "bol-van/zapret"
# что берём из релиза zapret: путь в архиве (после zapret-vX/) -> куда кладём в bin/
ZAPRET_FILES = {
    "binaries/windows-x86_64/winws.exe": "winws.exe",
    "binaries/windows-x86_64/WinDivert.dll": "WinDivert.dll",
    "binaries/windows-x86_64/WinDivert64.sys": "WinDivert64.sys",
    "binaries/windows-x86_64/cygwin1.dll": "cygwin1.dll",
    "files/fake/quic_initial_www_google_com.bin": "fake/quic_initial_www_google_com.bin",
    "files/fake/tls_clienthello_www_google_com.bin": "fake/tls_clienthello_www_google_com.bin",
}
IPSET_MAX_AGE = 7 * 24 * 3600   # IP игр обновляем раз в неделю


def _ver(s: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", s or "")) or (0,)


def _get(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"Lotus/{VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _latest(repo: str) -> dict:
    return json.loads(_get(f"https://api.github.com/repos/{repo}/releases/latest"))


# ---------- zapret ----------

def zapret_version() -> str:
    try:
        return (engine.BIN / "ZAPRET_VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "?"


def check_zapret() -> str | None:
    """Новая версия zapret или None."""
    tag = _latest(ZAPRET_REPO)["tag_name"]
    return tag if _ver(tag) > _ver(zapret_version()) else None


def update_zapret(tag: str) -> None:
    """Скачать релиз, сверить файлы с официальными sha256 и положить в bin/.
    Движок перед этим нужно остановить — файлы winws заняты, пока он работает."""
    base = f"https://github.com/{ZAPRET_REPO}/releases/download/{tag}"
    sums = {}
    for line in _get(f"{base}/sha256sum.txt").decode().splitlines():
        h, _, p = line.partition("  ")
        sums[p.strip()] = h.strip().lower()
    z = zipfile.ZipFile(io.BytesIO(_get(f"{base}/zapret-{tag}.zip", timeout=300)))
    prefix = f"zapret-{tag}/"
    new = {}
    for src, dst in ZAPRET_FILES.items():
        data = z.read(prefix + src)
        want = sums.get(prefix + src)
        # fake/*.bin в sha256sum.txt нет — это образцы пакетов, не программы
        if want is not None and hashlib.sha256(data).hexdigest() != want:
            raise RuntimeError(f"контрольная сумма не совпала: {src}")
        if want is None and not src.startswith("files/fake/"):
            raise RuntimeError(f"нет контрольной суммы для {src}")
        new[dst] = data
    for dst, data in new.items():
        p = engine.BIN / dst
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    # GoodbyeDPI должен работать с тем же драйвером, что и zapret
    for name in ("WinDivert.dll", "WinDivert64.sys"):
        (engine.GDPI_DIR / name).write_bytes(new[name])
    (engine.BIN / "ZAPRET_VERSION").write_text(tag, encoding="utf-8")


# ---------- списки ----------

def ipset_is_old() -> bool:
    p = engine.LISTS / "ipset-games.txt"
    if not p.exists() or time.time() - p.stat().st_mtime > IPSET_MAX_AGE:
        return True
    # до версии 1.0.3 не было отдельного списка серверов Valve (игры Steam), а в 1.0.2 сеть Valve
    # лежала в списке «Игр» — там она пересекается с GoodbyeDPI у Steam. Такие списки обновить сразу.
    if not (engine.LISTS / "ipset-valve.txt").exists():
        return True
    return "\n155.133." in "\n" + p.read_text(encoding="utf-8")


def update_ipset() -> int:
    return update_lists.update(engine.LISTS)


# ---------- сам Lotus ----------

def check_lotus() -> tuple[str, str, str | None] | None:
    """(версия, ссылка на LotusSetup.exe, sha256 или None) — если на GitHub есть версия новее."""
    if not UPDATE_REPO:
        return None
    rel = _latest(UPDATE_REPO)
    tag = rel["tag_name"]
    if _ver(tag) <= _ver(VERSION):
        return None
    for a in rel.get("assets", []):
        if a["name"].lower() == "lotussetup.exe":
            digest = (a.get("digest") or "").removeprefix("sha256:") or None
            return tag.lstrip("v"), a["browser_download_url"], digest
    return None


def is_installed() -> bool:
    """Установлен через LotusSetup.exe (распакованная папка) — а не портативный Lotus.exe.
    Сам обновляться умеет только установленный: портативному ставить новую версию некуда."""
    return engine.FROZEN and (Path(sys.executable).parent / "_internal").is_dir()


def install_lotus(url: str, digest: str | None, silent: bool = False) -> None:
    """Скачать установщик новой версии и запустить его; Lotus после этого нужно закрыть.
    silent — без окон (автообновление): установщик сам закроет Lotus и запустит новую версию."""
    if not url.startswith(f"https://github.com/{UPDATE_REPO}/releases/download/"):
        raise RuntimeError("неожиданный адрес обновления")
    if silent and not digest:
        raise RuntimeError("у релиза нет контрольной суммы — тихо ставить не буду")
    data = _get(url, timeout=600)
    if digest and hashlib.sha256(data).hexdigest() != digest.lower():
        raise RuntimeError("контрольная сумма обновления не совпала")
    path = Path(tempfile.gettempdir()) / "LotusSetup.exe"
    path.write_bytes(data)
    if silent:
        subprocess.Popen([str(path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                         creationflags=subprocess.DETACHED_PROCESS | engine.NO_WINDOW)
    else:
        os.startfile(str(path))
