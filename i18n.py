"""Надписи Lotus на русском и английском. tr("ключ", **параметры)."""

LANG = "ru"

STRINGS = {
    "ru": {
        # плитки и статусы
        "svc.games": "Игры", "svc.custom": "Свои сайты", "svc.meta": "Instagram",
        "st.off": "выключен", "st.starting": "включаю…", "st.checking": "проверяю…",
        "st.ok": "открывается", "st.fail": "не открывается", "st.error": "ошибка",
        "st.video_fail": "видео не грузится", "st.voice_fail": "голос не работает",
        "st.ok_many": "открываются", "st.two_presets": "2 пресета", "tile.ytdc": "YouTube + Discord",
        "msg.tile_preset": "{tile}: стратегия «{name}».", "msg.others": "остальные — {name}",
        "st.proxy": "прокси {port}", "st.subnets": "{n} подсетей", "st.sites": "{n} сайтов",
        "st.no_sites": "добавь сайты в ⚙",
        "pill.on": "работает", "pill.off": "выключено",
        "hint": "Нажми на сервис, чтобы включить для него обход.",
        # сообщения
        "msg.all_ok": "Всё работает.", "msg.all_off": "Всё выключено.", "msg.more": "(подробнее в ⚙)",
        "msg.fail": "Не открывается: {names}. Попробуй другой пресет в ⚙.",
        "msg.error": "Ошибка: {e}", "msg.preset": "Пресет: «{name}».",
        "msg.best": "Подобрал пресеты: {name}.",
        "set.overrides": "Отдельно подобраны: {list}",
        "msg.none_helped": "Ни один пресет не помог. Возможно, блокировка по IP — тут нужен прокси.",
        "msg.checking": "Проверяю доступ…", "msg.check_line": "  {name}: {res}",
        "msg.ipset": "IP игр обновлены: {n} подсетей.",
        "msg.tg_open": "Открываю Telegram — нажми «Подключиться» в окне прокси.",
        "msg.tg_copy": "Telegram Desktop не найден. Ссылка скопирована — отправь её себе в «Избранное» и нажми по ней.",
        "msg.autostart_on": "Автозапуск с Windows включён.", "msg.autostart_off": "Автозапуск выключен.",
        "msg.autostart_err": "Не удалось изменить автозапуск: {e}",
        "msg.sites_saved": "Свои сайты сохранены: {n}.",
        "msg.watch_fail": "Перестало открываться: {names}. Подбираю пресет заново…",
        "msg.watch_fixed": "Подобрал пресеты ({name}) — всё снова работает.",
        "msg.watch_broken": "Не открывается: {names}, и подбор пресета не помог.",
        "msg.upd_none": "Обновлений нет: Lotus {v}, zapret {z}.",
        "msg.upd_lotus": "Вышел Lotus {v} — обнови в ⚙.",
        "msg.upd_zapret": "Вышел zapret {v} — обнови в ⚙.",
        "msg.upd_zapret_done": "zapret обновлён до {v}.",
        "msg.upd_err": "Не удалось проверить обновления: {e}",
        "msg.upd_downloading": "Скачиваю обновление…",
        "msg.upd_auto": "Ставлю обновление Lotus {v} — через минуту Lotus перезапустится сам.",
        "msg.updated": "Lotus обновлён до версии {v}.",
        "tray.updated_title": "Lotus обновлён",
        "set.auto_update": "Обновлять Lotus автоматически",
        "msg.upd_norepo": "Адрес для обновлений Lotus не настроен.",
        "tray.hint_title": "Lotus свёрнут в трей",
        "tray.hint": "Lotus продолжает работать здесь. Выйти — правой кнопкой по значку.",
        "tray.fail_title": "Lotus: проблема с доступом",
        "tray.update_title": "Lotus: есть обновление",
        "tray.open": "Открыть Lotus", "tray.autostart": "Запускать вместе с Windows",
        "tray.quit": "Выход", "tray.on": "Lotus — работает", "tray.off": "Lotus — выключено",
        # настройки
        "set.title": "Lotus — настройки", "set.theme": "Оформление: {name}", "set.lang": "Язык",
        "set.preset": "Пресет для остальных сервисов (YouTube + Discord — стрелочка ▼ на плитке)",
        "set.auto": "Подобрать автоматически",
        "sm.title": "Стратегия YouTube + Discord", "sg.main": "Основные — по очереди сверху вниз",
        "sg.exp": "Экспериментальная", "sg.fake_tls": "Фейковый TLS — часто помогает Discord",
        "sg.simple": "Простой фейк — если другие рвут соединение",
        "tray.warn": "Lotus — что-то не открывается", "set.back": "Назад",
        "set.tools": "Инструменты", "set.check": "Проверить доступ", "set.ipset": "Обновить IP игр",
        "set.tg": "Подключить Telegram",
        "set.sites": "Свои сайты (по одному домену в строке)", "set.sites_save": "Сохранить сайты",
        "set.watch": "Следить за доступом и чинить сам", "set.autostart": "Запускать вместе с Windows",
        "set.updates": "Обновления", "set.version": "Lotus {v} · zapret {z}",
        "set.check_upd": "Проверить обновления", "set.upd_lotus": "Установить Lotus {v}",
        "set.upd_zapret": "Обновить zapret до {v}", "set.log": "Журнал",
        # движок
        "eng.no_services": "Не выбран ни один сервис",
        "eng.winws_died": "winws.exe сразу закрылся, подробности в winws.log:\n{log}",
        "eng.gdpi_died": "GoodbyeDPI сразу закрылся, подробности в goodbyedpi.log:\n{log}",
        "eng.gdpi_other": "Уже запущен другой GoodbyeDPI (например, из .cmd). Закрой его — два перенаправления DNS мешают друг другу.",
        "eng.tg_died": "tg-ws-proxy сразу закрылся, подробности в tgproxy.log:\n{log}",
        "eng.try": "Пробую «{name}»...", "eng.try_err": "  ошибка: {e}",
        "eng.yes": "ок", "eng.no": "нет",
        "admin": "Нужны права администратора.",
        # пресеты
        "preset.general": "Основной", "preset.alt": "Альтернативный", "preset.seqovl": "Перекрытие (seqovl)",
        "preset.faketls": "Фейковый TLS", "preset.ttl": "Короткий TTL",
        "preset.hostfake": "Подмена хоста", "preset.badseqinc": "Сдвиг SEQ", "preset.seqovl2": "Перекрытие 2",
        "preset.fakeddis": "Фейк + беспорядок", "preset.fakedsplit": "Фейк + сплит",
        # короткие подсказки прямо в выпадающем списке — когда выбирать
        "phint.general": "начни с него", "phint.alt": "если «Основной» не помог",
        "phint.seqovl": "против «умных» фильтров (ТСПУ)", "phint.faketls": "часто помогает Discord",
        "phint.ttl": "если другие рвут соединение", "phint.hostfake": "провайдер смотрит на имя сайта",
        "phint.badseqinc": "когда остальные не берут", "phint.seqovl2": "если «Перекрытие» не помогло",
        "phint.fakeddis": "против простых фильтров", "phint.fakedsplit": "универсальный запасной",
        # описания пресетов: что делает и когда пробовать
        "pdesc.general": "Подходит большинству провайдеров — начни с него. Отправляет фильтру провайдера поддельный запрос и режет настоящий на перемешанные части.",
        "pdesc.alt": "Если «Основной» не помог. Поддельный запрос + запрос, разрезанный сразу после первого байта.",
        "pdesc.seqovl": "Против «умных» фильтров (часто ТСПУ в России). Прячет имя сайта за подложным кусочком данных, который сайт отбрасывает, а фильтр — нет.",
        "pdesc.faketls": "Перед настоящим запросом шлёт поддельный «запрос к google.com». Часто помогает для Discord.",
        "pdesc.ttl": "Поддельные пакеты «умирают» по дороге и до сайта не доходят — только до фильтра. Для провайдеров, где другие способы ломают соединение.",
        "pdesc.hostfake": "Подсовывает фильтру чужое имя сайта (ya.ru). Помогает, когда провайдер смотрит именно на имя сайта.",
        "pdesc.badseqinc": "Поддельные пакеты с неверными номерами: сайт их выбрасывает, а фильтр принимает за настоящие.",
        "pdesc.seqovl2": "Вариант «Перекрытия» с другим размером подложки — пробуй, если первое не помогло.",
        "pdesc.fakeddis": "Части запроса приходят в перемешанном порядке вместе с подделками — против фильтров, которые не умеют собирать пакеты.",
        "pdesc.fakedsplit": "Одна из самых универсальных стратегий в сборках zapret: подделки + запрос, разрезанный на части.",
        "pdesc.auto": "Не знаешь, какой выбрать? Нажми «Подобрать автоматически» — Lotus проверит все и для каждого сервиса возьмёт рабочий.",
        "msg.quic_hint": "Если в браузере YouTube при этом открывается — он идёт по QUIC (UDP), а Lotus проверяет обычное соединение, которым пользуются приложения, ТВ и браузер, когда QUIC недоступен. Лучше выбрать пресет, где «открывается».",
        # темы
        "theme.night": "Ночь", "theme.green": "Зелёная", "theme.pink": "Розовая",
        "theme.orange": "Оранжевая", "theme.gold": "Золотая", "theme.coral": "Коралловая",
    },
    "en": {
        "svc.games": "Games", "svc.custom": "Custom sites", "svc.meta": "Instagram",
        "st.off": "off", "st.starting": "starting…", "st.checking": "checking…",
        "st.ok": "works", "st.fail": "blocked", "st.error": "error",
        "st.video_fail": "video blocked", "st.voice_fail": "voice blocked",
        "st.ok_many": "both work", "st.two_presets": "2 presets", "tile.ytdc": "YouTube + Discord",
        "msg.tile_preset": "{tile}: strategy “{name}”.", "msg.others": "others — {name}",
        "st.proxy": "proxy {port}", "st.subnets": "{n} subnets", "st.sites": "{n} sites",
        "st.no_sites": "add sites in ⚙",
        "pill.on": "running", "pill.off": "stopped",
        "hint": "Click a service to unblock it.",
        "msg.all_ok": "Everything works.", "msg.all_off": "Everything is off.", "msg.more": "(more in ⚙)",
        "msg.fail": "Blocked: {names}. Try another preset in ⚙.",
        "msg.error": "Error: {e}", "msg.preset": "Preset: “{name}”.",
        "msg.best": "Picked presets: {name}.",
        "set.overrides": "Picked separately: {list}",
        "msg.none_helped": "No preset helped. The block may be by IP — that needs a proxy.",
        "msg.checking": "Checking access…", "msg.check_line": "  {name}: {res}",
        "msg.ipset": "Game IPs updated: {n} subnets.",
        "msg.tg_open": "Opening Telegram — press “Connect” in the proxy window.",
        "msg.tg_copy": "Telegram Desktop not found. Link copied — send it to your Saved Messages and click it.",
        "msg.autostart_on": "Start with Windows: on.", "msg.autostart_off": "Start with Windows: off.",
        "msg.autostart_err": "Couldn't change autostart: {e}",
        "msg.sites_saved": "Custom sites saved: {n}.",
        "msg.watch_fail": "Stopped working: {names}. Picking a preset again…",
        "msg.watch_fixed": "Picked presets ({name}) — everything works again.",
        "msg.watch_broken": "Blocked: {names}, and picking a preset didn't help.",
        "msg.upd_none": "No updates: Lotus {v}, zapret {z}.",
        "msg.upd_lotus": "Lotus {v} is out — update in ⚙.",
        "msg.upd_zapret": "zapret {v} is out — update in ⚙.",
        "msg.upd_zapret_done": "zapret updated to {v}.",
        "msg.upd_err": "Couldn't check for updates: {e}",
        "msg.upd_downloading": "Downloading the update…",
        "msg.upd_auto": "Installing Lotus {v} — Lotus will restart by itself in a minute.",
        "msg.updated": "Lotus updated to version {v}.",
        "tray.updated_title": "Lotus updated",
        "set.auto_update": "Update Lotus automatically",
        "msg.upd_norepo": "Lotus update address isn't set up.",
        "tray.hint_title": "Lotus is in the tray",
        "tray.hint": "Lotus keeps working here. To quit, right-click the icon.",
        "tray.fail_title": "Lotus: access problem",
        "tray.update_title": "Lotus: update available",
        "tray.open": "Open Lotus", "tray.autostart": "Start with Windows",
        "tray.quit": "Quit", "tray.on": "Lotus — running", "tray.off": "Lotus — stopped",
        "set.title": "Lotus — settings", "set.theme": "Theme: {name}", "set.lang": "Language",
        "set.preset": "Preset for other services (YouTube + Discord — arrow ▼ on the tile)",
        "set.auto": "Pick automatically",
        "sm.title": "YouTube + Discord strategy", "sg.main": "Main — try top to bottom",
        "sg.exp": "Experimental", "sg.fake_tls": "Fake TLS — often helps Discord",
        "sg.simple": "Simple fake — if others break the connection",
        "tray.warn": "Lotus — something is blocked", "set.back": "Back",
        "set.tools": "Tools", "set.check": "Check access", "set.ipset": "Update game IPs",
        "set.tg": "Connect Telegram",
        "set.sites": "Custom sites (one domain per line)", "set.sites_save": "Save sites",
        "set.watch": "Watch access and fix it myself", "set.autostart": "Start with Windows",
        "set.updates": "Updates", "set.version": "Lotus {v} · zapret {z}",
        "set.check_upd": "Check for updates", "set.upd_lotus": "Install Lotus {v}",
        "set.upd_zapret": "Update zapret to {v}", "set.log": "Log",
        "eng.no_services": "No service selected",
        "eng.winws_died": "winws.exe exited right away, see winws.log:\n{log}",
        "eng.gdpi_died": "GoodbyeDPI exited right away, see goodbyedpi.log:\n{log}",
        "eng.gdpi_other": "Another GoodbyeDPI is already running (e.g. from a .cmd). Close it — two DNS redirects conflict.",
        "eng.tg_died": "tg-ws-proxy exited right away, see tgproxy.log:\n{log}",
        "eng.try": "Trying “{name}”...", "eng.try_err": "  error: {e}",
        "eng.yes": "ok", "eng.no": "no",
        "admin": "Administrator rights are required.",
        "preset.general": "Main", "preset.alt": "Alternative", "preset.seqovl": "Overlap (seqovl)",
        "preset.faketls": "Fake TLS", "preset.ttl": "Short TTL",
        "preset.hostfake": "Host spoof", "preset.badseqinc": "SEQ shift", "preset.seqovl2": "Overlap 2",
        "preset.fakeddis": "Fake + disorder", "preset.fakedsplit": "Fake + split",
        "phint.general": "start here", "phint.alt": "if “Main” didn't help",
        "phint.seqovl": "against “smart” filters", "phint.faketls": "often helps Discord",
        "phint.ttl": "if others break the connection", "phint.hostfake": "ISP checks the site name",
        "phint.badseqinc": "when nothing else works", "phint.seqovl2": "if “Overlap” didn't help",
        "phint.fakeddis": "against simple filters", "phint.fakedsplit": "universal fallback",
        "pdesc.general": "Works for most ISPs — start here. Sends the ISP filter a fake request and cuts the real one into shuffled parts.",
        "pdesc.alt": "If “Main” didn't help. A fake request plus the request cut right after its first byte.",
        "pdesc.seqovl": "Against “smart” filters. Hides the site name behind a decoy chunk that the site drops but the filter reads.",
        "pdesc.faketls": "Sends a fake “request to google.com” before the real one. Often helps Discord.",
        "pdesc.ttl": "Fake packets “die” on the way and reach only the filter, not the site. For ISPs where other methods break the connection.",
        "pdesc.hostfake": "Feeds the filter a different site name (ya.ru). Helps when the ISP looks at the site name.",
        "pdesc.badseqinc": "Fake packets with wrong sequence numbers: the site drops them, the filter takes them as real.",
        "pdesc.seqovl2": "A variant of “Overlap” with a different decoy size — try it if the first one didn't help.",
        "pdesc.fakeddis": "Request parts arrive out of order mixed with fakes — against filters that can't reassemble packets.",
        "pdesc.fakedsplit": "One of the most universal zapret strategies: fakes plus the request cut into parts.",
        "pdesc.auto": "Not sure which one? Press “Pick automatically” — Lotus tries them all and picks a working one per service.",
        "msg.quic_hint": "If YouTube still opens in your browser, it goes over QUIC (UDP); Lotus checks the regular connection used by apps, TVs and browsers when QUIC is unavailable. Better pick a preset where it says “works”.",
        "theme.night": "Night", "theme.green": "Green", "theme.pink": "Pink",
        "theme.orange": "Orange", "theme.gold": "Gold", "theme.coral": "Coral",
    },
}
LANGS = {"ru": "Русский", "en": "English"}

# числа со склонением: (1, 2-4, 5+) для русского; (1, много) для английского
PLURALS = {
    "ru": {"st.sites": ("{n} сайт", "{n} сайта", "{n} сайтов"),
           "st.subnets": ("{n} подсеть", "{n} подсети", "{n} подсетей")},
    "en": {"st.sites": ("{n} site", "{n} sites", "{n} sites"),
           "st.subnets": ("{n} subnet", "{n} subnets", "{n} subnets")},
}


def _plural_form(n: int) -> int:
    if LANG != "ru":
        return 0 if n == 1 else 1
    if n % 10 == 1 and n % 100 != 11:
        return 0
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return 1
    return 2


def set_lang(lang: str) -> None:
    global LANG
    LANG = lang if lang in STRINGS else "ru"


def tr(key: str, **kw) -> str:
    if key in PLURALS[LANG] and "n" in kw:
        return PLURALS[LANG][key][_plural_form(kw["n"])].format(**kw)
    s = STRINGS[LANG].get(key) or STRINGS["ru"].get(key, key)
    return s.format(**kw) if kw else s


def svc_name(sid: str) -> str:
    """Имя сервиса для плиток и сообщений (бренды не переводятся)."""
    from services import SERVICES_BY_ID
    key = f"svc.{sid}"
    return tr(key) if key in STRINGS["ru"] else SERVICES_BY_ID[sid].name
