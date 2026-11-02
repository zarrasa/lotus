"""Сборка Lotus.

python build.py          — dist/LotusSetup.exe (установщик, быстрый запуск) и dist/Lotus.exe (портативный)
python build.py --test   — портативный без запроса прав, в dist_test/ (для проверки окна)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from version import VERSION

HERE = Path(__file__).parent
test = "--test" in sys.argv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # консоль может быть не в UTF-8

COMMON = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed",
    "--name", "Lotus", "--icon", "icons/lotus.ico",
    "--add-data", "bin;bin", "--add-data", "lists;lists", "--add-data", "icons;icons",
    # tg-ws-proxy: импортируется только в режиме --tgproxy, поэтому собираем явно
    "--paths", "tgproxy", "--collect-submodules", "proxy", "--hidden-import", "utils.logging_setup",
    "--collect-data", "customtkinter",
    "--hidden-import", "pystray._win32",   # бэкенд трея выбирается динамически
]


def pyinstaller(*extra: str) -> None:
    subprocess.check_call([*COMMON, *extra, "app.py"], cwd=HERE)


def iscc() -> str:
    for p in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
              Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")):
        if p.exists():
            return str(p)
    raise SystemExit("Не найден Inno Setup (ISCC.exe): winget install JRSoftware.InnoSetup")


if test:
    pyinstaller("--onefile", "--distpath", "dist_test", "--workpath", "build_test")
    sys.exit(0)

# 1) папка для установщика: без распаковки при каждом запуске — стартует мгновенно
pyinstaller("--onedir", "--uac-admin", "--distpath", "dist", "--workpath", "build/onedir")
subprocess.check_call([iscc(), f"/DAppVersion={VERSION}", "/Q", "installer.iss"], cwd=HERE)
# 2) портативный один файл
pyinstaller("--onefile", "--uac-admin", "--distpath", "dist", "--workpath", "build/onefile")

shutil.rmtree(HERE / "build", ignore_errors=True)
(HERE / "Lotus.spec").unlink(missing_ok=True)
print(f"Готово: dist/LotusSetup.exe и dist/Lotus.exe (версия {VERSION})")
