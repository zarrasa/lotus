# Lotus

**RU** · Бесплатная программа для Windows, которая возвращает доступ к YouTube, Discord, Telegram,
Steam, Instagram, Twitch и онлайн-играм без VPN: обход DPI-блокировок провайдера прямо на компьютере.
Сервис включается нажатием на его плитку.

**EN** · A free Windows app that restores access to YouTube, Discord, Telegram, Steam, Instagram,
Twitch and online games blocked by your ISP's DPI — no VPN, everything runs on your PC.

**Скачать / Download:** раздел [Releases](../../releases/latest) — `LotusSetup.exe` (установщик)
или `Lotus.exe` (без установки). Инструкция — `release/README.txt` / `release/README_EN.txt`.

Lotus — оболочка над проверенными открытыми инструментами: [zapret](https://github.com/bol-van/zapret),
[GoodbyeDPI](https://github.com/ValdikSS/GoodbyeDPI) и [tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy)
(подробнее — [THIRD_PARTY.md](THIRD_PARTY.md)).

## Запуск из исходников

```
pip install -r requirements.txt
python app.py
```

Нужны права администратора (WinDivert) — программа сама их попросит.

## Сборка

```
python build.py
```

Нужен Inno Setup 6 (`winget install JRSoftware.InnoSetup`). Результат:
`dist/LotusSetup.exe` (установщик, распакованная версия — быстрый запуск) и `dist/Lotus.exe` (портативный).
Рабочие файлы Lotus хранит в `%APPDATA%\Lotus`.

## Выпуск новой версии

1. Поднять `VERSION` в `version.py`, закоммитить.
2. Поставить тег и отправить: `git tag v<версия>` → `git push --tags`.
3. GitHub Actions (`.github/workflows/release.yml`) соберёт `LotusSetup.exe` и `Lotus.exe`,
   подпишет их (если настроен SignPath — см. [SIGNING.md](SIGNING.md)) и выложит релиз.
   Lotus у пользователей раз в сутки проверяет последний релиз и предлагает обновиться
   (с проверкой sha256).

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by
[SignPath Foundation](https://signpath.org) (once the project is approved).

- Releases are built only by GitHub Actions from this repository; signed builds are produced
  only from tagged commits on the default branch.
- Committers and approvers: the repository owner.
- Privacy: Lotus does not collect or send any personal data. It only contacts the services you
  enable (to check access), GitHub (to check for updates) and public IP-range sources
  (Amazon, Cloudflare, RIPE, Steam) to update game server lists.

## Что где

- `app.py` — окно, плитки, анимация, трей, окно настроек
- `ui_render.py` — отрисовка стекла, свечения и бегущего огонька
- `themes.py` — расцветки: все тёмные, как «Ночь», отличаются цветом свечения; логотипы тем —
  перекрашенный исходный логотип, `icons/theme_*.png` (`tools/make_themes.py`)
- `engine.py` — запуск winws и tg-ws-proxy, проверка доступа, автоподбор пресета
- `services.py` — сервисы и пресеты обхода
- `i18n.py` — все надписи на русском и английском
- `updater.py` — обновления Lotus (GitHub), zapret (с проверкой sha256) и IP игр; `version.py` — версия
- `installer.iss` — сценарий установщика Inno Setup
- `autostart.py` — автозапуск через Планировщик заданий
- `update_lists.py` — обновление IP игровых серверов (Amazon, Cloudflare; Valve — для плитки Steam)
- `lists/` — домены и подсети сервисов
- `bin/` — zapret v72.13 (winws, WinDivert), MIT
- `bin/gdpi/` — GoodbyeDPI 0.2.3rc3, Apache 2.0: Steam (`-9` + перенаправление DNS на 77.88.8.8:1253,
  т.к. Steam режут и через DNS). WinDivert рядом — та же сборка, что у zapret, чтобы драйверы не конфликтовали
- `tgproxy/` — Flowseal/tg-ws-proxy v1.11.4, MIT
- `icons/` — логотип и иконки сервисов (Font Awesome Free, CC BY 4.0)
- `tools/` — генерация иконок и логотипа
