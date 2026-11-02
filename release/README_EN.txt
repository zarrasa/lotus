LOTUS — unblock YouTube, Discord, Telegram, Steam and more
===========================================================

Helps when YouTube, Discord, Telegram, Steam, Instagram, Twitch or online games
(e.g. Dead by Daylight) don't work. No VPN: everything runs on your own PC,
speed and ping are not affected.


INSTALL
-------
Option 1 (recommended) — LotusSetup.exe: run it and click "Next" a few times.
Option 2 — Lotus.exe: a single program, no installation, just run it.

Windows will ask "Do you want to allow this app to make changes?" — click "Yes".
Bypassing blocks needs administrator rights.

To switch the interface to English: ⚙ (top right) → Language → English.


HOW TO USE
----------
Click a service tile — it gets unblocked right away. Click again to turn it off.
While a service is starting, a light runs around the tile. When the whole frame
glows and the tile says "works" — you're done.

• Instagram means Instagram, Facebook and Threads together.
• Custom sites — open ⚙, type any sites (one per line), click "Save sites"
  and turn on the "Custom sites" tile.


IF WINDOWS OR ANTIVIRUS COMPLAINS
---------------------------------
Lotus is not code-signed and includes the WinDivert network driver (same as
zapret and GoodbyeDPI), so false alarms are possible.
• "Windows protected your PC" — click "More info", then "Run anyway".
• Antivirus removed the file — add Lotus to your antivirus exclusions.


TELEGRAM
--------
Works with Telegram Desktop. Turn on the Telegram tile, then ⚙ → "Connect
Telegram" and press "Connect" in Telegram. Only needed once.


IF SOMETHING DOESN'T OPEN
-------------------------
Every 5 minutes Lotus checks the enabled services itself; if one stops working,
it picks another bypass method and shows a notification.
Still blocked? ⚙ → "Pick automatically", or choose another preset manually.
Games don't connect — ⚙ → "Update game IPs". Steam doesn't open — close other
bypass tools (GoodbyeDPI, zapret, VPN). Include the log from ⚙ when asking for help.


PRESETS
-------
A preset is a way to fool the ISP filter; different ISPs need different ones.
Easiest: ⚙ → "Pick automatically" — Lotus tries all 10 and picks a working one per
service. Each preset's description is shown under the list in ⚙.

Why does Lotus say "blocked" while YouTube opens in the browser? Browsers use QUIC
for YouTube, a separate path that works on any preset. Lotus checks the regular
connection used by apps, TVs and browsers when QUIC is unavailable — prefer a preset
where it says "works".


TRAY AND AUTOSTART
------------------
The X button hides Lotus next to the clock — it keeps working. Right-click the
tray icon to toggle services or quit. ⚙ → "Start with Windows" for autostart.


UNINSTALL
---------
Installed with LotusSetup.exe: Settings → Apps → Lotus → Uninstall.
Portable Lotus.exe: turn off autostart, quit Lotus, delete Lotus.exe and %APPDATA%\Lotus.


BUILT WITH
----------
zapret (bol-van, MIT) · GoodbyeDPI (ValdikSS, Apache 2.0) ·
tg-ws-proxy (Flowseal, MIT) · Font Awesome Free icons (CC BY 4.0)
