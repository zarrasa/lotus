"""Сервисы, которые можно включать галочками, и пресеты обхода DPI.

Сервис = набор доменов (hostlist) и/или подсетей (ipset) + какие порты/протоколы ловить.
Пресет = как именно "ломать" пакеты. У разных провайдеров работают разные пресеты,
поэтому их несколько и есть автоподбор.
"""

from dataclasses import dataclass, field


@dataclass
class Service:
    id: str
    name: str
    hostlist: str | None = None   # файл в lists/ с доменами
    ipset: str | None = None      # файл в lists/ с подсетями
    voice: bool = False           # голос Discord (UDP 50000-65535, STUN/Discord)
    game: bool = False            # игровой режим: широкие порты TCP/UDP по ipset
    tgproxy: bool = False         # не winws, а локальный tg-ws-proxy
    gdpi: bool = False            # не winws, а GoodbyeDPI: DPI-обход + перенаправление DNS
    test_url: str | None = None   # что открыть при проверке доступа (больше 16 КБ)
    description: str = ""


SERVICES: list[Service] = [
    Service("youtube", "YouTube", hostlist="youtube.txt", test_url="https://www.youtube.com/",
            description="Сайт, видео, приложение"),
    Service("discord", "Discord", hostlist="discord.txt", voice=True, test_url="https://discord.com/",
            description="Чат, картинки, голосовые"),
    # Steam часто режут ещё и через DNS (например, во Вьетнаме провайдер отвечает 127.0.0.1),
    # а winws DNS не трогает — поэтому сайты Steam идут через GoodbyeDPI с перенаправлением DNS.
    # Игровые сервера и ретрансляторы Valve — через winws в игровом режиме (ipset-valve.txt),
    # чтобы игры Steam работали без отдельной плитки «Игры».
    Service("steam", "Steam", hostlist="steam.txt", gdpi=True, ipset="ipset-valve.txt", game=True,
            test_url="https://store.steampowered.com/", description="Магазин, библиотека и игровые сервера"),
    Service("meta", "Instagram", hostlist="meta.txt", test_url="https://www.instagram.com/",
            description="Instagram, Facebook, Threads"),
    Service("twitch", "Twitch", hostlist="twitch.txt", test_url="https://www.twitch.tv/",
            description="Стримы и чат"),
    Service("games", "Игры (DBD и др.)", ipset="ipset-games.txt", game=True,
            description="Игровые сервера на Amazon и Cloudflare (игры Steam — в плитке Steam)"),
    Service("telegram", "Telegram", tgproxy=True,
            description="Telegram Desktop через tg-ws-proxy"),
    # домены вписывает сам пользователь в настройках (lists/custom.txt)
    Service("custom", "Свои сайты", hostlist="custom.txt", description="Свои домены"),
]

SERVICES_BY_ID = {s.id: s for s in SERVICES}


@dataclass
class Preset:
    id: str
    name: str
    # стратегия для TCP 443 (TLS) — главное, что отличается между пресетами
    tls: list[str]
    # стратегия для UDP 443 (QUIC)
    quic: list[str] = field(default_factory=lambda: [
        "--dpi-desync=fake", "--dpi-desync-repeats=6",
        "--dpi-desync-fake-quic={FAKE}/quic_initial_www_google_com.bin",
    ])
    # стратегия для TCP 80 (HTTP)
    http: list[str] = field(default_factory=lambda: [
        "--dpi-desync=fake,multisplit", "--dpi-desync-autottl=2",
        "--dpi-desync-fooling=md5sig",
    ])


PRESETS: list[Preset] = [
    Preset("general", "Основной", tls=[
        "--dpi-desync=fake,multidisorder", "--dpi-desync-split-pos=midsld",
        "--dpi-desync-repeats=6", "--dpi-desync-fooling=md5sig,badseq",
    ]),
    Preset("alt", "Альтернативный", tls=[
        "--dpi-desync=fake,fakedsplit", "--dpi-desync-split-pos=1",
        "--dpi-desync-repeats=8", "--dpi-desync-fooling=ts",
        "--dpi-desync-fake-tls={FAKE}/tls_clienthello_www_google_com.bin",
    ]),
    Preset("seqovl", "Перекрытие (seqovl)", tls=[
        "--dpi-desync=multisplit", "--dpi-desync-split-pos=2",
        "--dpi-desync-split-seqovl=652",
        "--dpi-desync-split-seqovl-pattern={FAKE}/tls_clienthello_www_google_com.bin",
    ]),
    Preset("faketls", "Фейковый TLS", tls=[
        "--dpi-desync=fake", "--dpi-desync-repeats=6",
        "--dpi-desync-fooling=badseq",
        "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
    ]),
    Preset("ttl", "Короткий TTL", tls=[
        "--dpi-desync=fake,multidisorder", "--dpi-desync-split-pos=1,midsld",
        "--dpi-desync-repeats=6", "--dpi-desync-autottl=2",
    ]),
    # ниже — стратегии, которые хорошо работают у разных провайдеров (по мотивам сборок Flowseal);
    # все параметры сверены с документацией zapret v72.13
    Preset("hostfake", "Подмена хоста", tls=[
        "--dpi-desync=fake,hostfakesplit", "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=ya.ru",
        "--dpi-desync-hostfakesplit-mod=host=ya.ru,altorder=1", "--dpi-desync-fooling=ts",
    ]),
    Preset("badseqinc", "Сдвиг SEQ", tls=[
        "--dpi-desync=fake,multisplit", "--dpi-desync-repeats=6", "--dpi-desync-fooling=badseq",
        "--dpi-desync-badseq-increment=1000",
        "--dpi-desync-fake-tls={FAKE}/tls_clienthello_www_google_com.bin",
    ]),
    Preset("seqovl2", "Перекрытие 2", tls=[
        "--dpi-desync=multisplit", "--dpi-desync-split-pos=1", "--dpi-desync-split-seqovl=681",
        "--dpi-desync-split-seqovl-pattern={FAKE}/tls_clienthello_www_google_com.bin",
    ]),
    Preset("fakeddis", "Фейк + беспорядок", tls=[
        "--dpi-desync=fake,fakeddisorder", "--dpi-desync-split-pos=midsld",
        "--dpi-desync-repeats=6", "--dpi-desync-fooling=badsum",
    ]),
    Preset("fakedsplit", "Фейк + сплит", tls=[
        "--dpi-desync=fake,fakedsplit", "--dpi-desync-repeats=6", "--dpi-desync-fooling=ts",
        "--dpi-desync-fakedsplit-pattern=0x00",
        "--dpi-desync-fake-tls={FAKE}/tls_clienthello_www_google_com.bin",
    ]),
]

PRESETS_BY_ID = {p.id: p for p in PRESETS}

# Порты игрового режима (как Game Filter во Flowseal)
GAME_PORTS = "1024-65535"
# Голос Discord
DISCORD_VOICE_PORTS = "50000-65535"
