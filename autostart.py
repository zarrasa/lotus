"""Автозапуск Lotus при входе в Windows.

Через Планировщик заданий, а не реестр Run: Lotus нужны права администратора,
а программы из Run Windows с повышенными правами не запускает.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

import engine

TASK = "Lotus"


def _command() -> tuple[str, str]:
    if engine.FROZEN:
        return sys.executable, "--tray"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return str(pythonw), f'"{Path(__file__).with_name("app.py")}" --tray'


def _schtasks(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["schtasks", *args], capture_output=True, text=True,
                          errors="replace", creationflags=engine.NO_WINDOW)


def is_enabled() -> bool:
    return _schtasks("/Query", "/TN", TASK).returncode == 0


def registered_command() -> str:
    r = _schtasks("/Query", "/TN", TASK, "/XML")
    return r.stdout if r.returncode == 0 else ""


def enable() -> None:
    exe, args = _command()
    user = f'{os.environ.get("USERDOMAIN", "")}\\{os.environ.get("USERNAME", "")}'
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Lotus: обход блокировок</Description></RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled><UserId>{escape(user)}</UserId><Delay>PT10S</Delay></LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{escape(user)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(exe)}</Command>
      <Arguments>{escape(args)}</Arguments>
      <WorkingDirectory>{escape(str(Path(exe).parent))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
    path = Path(tempfile.gettempdir()) / "lotus_task.xml"
    path.write_text(xml, encoding="utf-16")
    try:
        r = _schtasks("/Create", "/TN", TASK, "/XML", str(path), "/F")
    finally:
        path.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "schtasks не смог создать задачу")


def disable() -> None:
    _schtasks("/Delete", "/TN", TASK, "/F")


def refresh_path() -> None:
    """Если Lotus.exe перенесли в другое место — перерегистрировать задачу на новый путь."""
    if engine.FROZEN and is_enabled() and sys.executable not in registered_command():
        enable()
