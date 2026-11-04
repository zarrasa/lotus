"""Импорт стратегий из сборки Flowseal/zapret-discord-youtube (MIT, bol-van + Flowseal).

Берёт официальный релиз, вытаскивает из general*.bat параметры winws для YouTube и Discord,
а также их списки доменов и файлы-«фейки». Части про игровой фильтр и ipset-all выкидываются —
игры в Lotus обходит своя плитка. Результат: flowseal/strategies.json, flowseal/lists, flowseal/fake.

Запуск: python tools/import_flowseal.py [версия релиза, по умолчанию 1.10.4]
"""

import io
import json
import re
import shlex
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "Flowseal/zapret-discord-youtube"
OUT = Path(__file__).resolve().parent.parent / "flowseal"
LISTS = ("list-general.txt", "list-google.txt", "list-exclude.txt", "ipset-exclude.txt")


def order(name: str) -> tuple:
    """Порядок как у Flowseal: general, ALT, ALT2…ALT13, EXP, FAKE TLS AUTO…, SIMPLE FAKE…"""
    m = re.match(r"general(?: \((.*)\))?$", name)
    inner = (m.group(1) or "") if m else name
    groups = ["", "ALT", "EXP", "FAKE TLS AUTO", "SIMPLE FAKE"]
    base = re.sub(r"\s*ALT\d*$", "", inner) if inner.startswith(("FAKE", "SIMPLE")) else re.sub(r"\d+$", "", inner)
    num = re.search(r"ALT(\d*)$", inner)
    n = (int(num.group(1)) if num.group(1) else 1) if num and inner != base else 0
    return (groups.index(base) if base in groups else 99, n)


def parse_bat(text: str) -> list[list[str]]:
    """Профили winws (между --new) из строки запуска в .bat."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if 'winws.exe"' in l)
    cmd = ""
    for l in lines[start:]:
        cmd += l.rstrip().removesuffix("^") + " "
        if not l.rstrip().endswith("^"):
            break
    cmd = cmd.split('winws.exe"', 1)[1]
    tokens = shlex.split(cmd, posix=True)
    profiles, cur = [], []
    for t in tokens + ["--new"]:
        if t == "--new":
            profiles.append(cur)
            cur = []
        elif not t.startswith(("--wf-tcp", "--wf-udp")):
            cur.append(t)
    result = []
    for p in profiles:
        if any("%GameFilter" in t or "ipset-all.txt" in t for t in p):
            continue   # игровой фильтр Flowseal — у Lotus для игр своя плитка
        p = [t for t in p if "-user.txt" not in t]          # пользовательские списки Flowseal
        p = [t.replace("%LISTS%", "{FS_LISTS}/").replace("%BIN%", "{FS_FAKE}/") for t in p]
        if p:
            result.append(p)
    return result


def main(version: str) -> None:
    url = f"https://github.com/{REPO}/releases/download/{version}/zapret-discord-youtube-{version}.zip"
    with urllib.request.urlopen(url, timeout=300) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    names = z.namelist()
    root = next((n.split("/")[0] + "/" for n in names if n.endswith("general.bat") and "/" in n), "")

    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "lists").mkdir(parents=True)
    (OUT / "fake").mkdir()
    strategies = []
    for n in names:
        base = n[len(root):]
        if re.fullmatch(r"general( \(.*\))?\.bat", base):
            strategies.append({"name": base[:-4], "profiles": parse_bat(z.read(n).decode("utf-8", "replace"))})
        elif base.startswith("bin/") and base.endswith(".bin"):
            (OUT / "fake" / base[4:]).write_bytes(z.read(n))
        elif base.startswith("lists/") and base[6:] in LISTS:
            (OUT / "lists" / base[6:]).write_bytes(z.read(n))
        elif base == "LICENSE.txt":
            (OUT / "LICENSE.txt").write_bytes(z.read(n))
    strategies.sort(key=lambda s: order(s["name"]))
    # файлы-фейки, на которые реально ссылаются стратегии; остальные не нужны
    used = {m for s in strategies for p in s["profiles"] for t in p for m in re.findall(r"\{FS_FAKE\}/([\w.-]+)", t)}
    for f in (OUT / "fake").iterdir():
        if f.name not in used:
            f.unlink()
    (OUT / "strategies.json").write_text(json.dumps({"version": version, "strategies": strategies},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"flowseal {version}: {len(strategies)} стратегий, фейков {len(used)}, списков {len(LISTS)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1.10.4")
