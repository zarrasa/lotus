"""Обновление ipset для игрового режима.

Большинство онлайн-игр (DBD и т.п.) держат сервера на Amazon (AWS) или за Cloudflare.
Игры Steam (и не только Valve) подключаются через сеть Valve: свои сервера и ретрансляторы
Steam Datagram Relay. Именно эти сети режут через DPI, поэтому собираем их подсети.
"""

import json
import urllib.request
from pathlib import Path

AWS_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
CLOUDFLARE_URL = "https://www.cloudflare.com/ips-v4"
VALVE_ASN_URL = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS32590"
STEAM_SDR_URL = "https://api.steampowered.com/ISteamApps/GetSDRConfig/v1/?appid=730"

# известные сети Valve — на случай, если оба источника выше недоступны
VALVE_FALLBACK = [
    "155.133.224.0/19", "162.254.192.0/21", "185.25.180.0/22", "205.196.6.0/24",
    "208.64.200.0/22", "208.78.164.0/22", "103.10.124.0/23", "103.28.54.0/23",
    "146.66.152.0/21", "45.121.184.0/22", "190.217.32.0/22", "153.254.86.0/24",
    "192.69.96.0/22",
]


RIOT_ASN_URL = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS6507"
# известные сети Riot Games — на случай, если реестр недоступен
RIOT_FALLBACK = ["192.64.168.0/21", "162.249.72.0/21", "104.160.128.0/19", "185.40.64.0/22",
                 "151.106.240.0/20", "138.0.12.0/23", "45.7.36.0/22", "192.207.0.0/24"]


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Lotus"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _valve() -> set[str]:
    nets = set(VALVE_FALLBACK)
    try:   # все сети Valve из реестра RIPE
        data = json.loads(_get(VALVE_ASN_URL))
        nets |= {p["prefix"] for p in data["data"]["prefixes"] if ":" not in p["prefix"]}
    except Exception:
        pass
    try:   # ретрансляторы Steam Datagram Relay (часть стоит у партнёров, вне сети Valve)
        data = json.loads(_get(STEAM_SDR_URL))
        for pop in data.get("pops", {}).values():
            for relay in pop.get("relays", []):
                if relay.get("ipv4"):
                    nets.add(relay["ipv4"] + "/32")
    except Exception:
        pass
    return nets


def riot() -> list[str]:
    """Сеть Riot Games (League of Legends, Valorant): её игровые правила не трогают —
    LoL не блокируют, а фейковые пакеты его сервера отбрасывают («нет соединения»)."""
    nets = set(RIOT_FALLBACK)
    try:
        data = json.loads(_get(RIOT_ASN_URL))
        nets |= {p["prefix"] for p in data["data"]["prefixes"] if ":" not in p["prefix"]}
    except Exception:
        pass
    return sorted(nets)


def fetch_game_ranges() -> list[str]:
    nets: set[str] = set()

    aws = json.loads(_get(AWS_URL))
    for p in aws["prefixes"]:
        # EC2 и GameLift — там живут игровые сервера
        if p["service"] in ("EC2", "GAMELIFT"):
            nets.add(p["ip_prefix"])

    for line in _get(CLOUDFLARE_URL).decode().splitlines():
        line = line.strip()
        if line:
            nets.add(line)

    return sorted(nets)   # сеть Valve — отдельным списком у плитки Steam, чтобы не пересекались


def update(lists_dir: Path) -> int:
    nets = fetch_game_ranges()
    (lists_dir / "ipset-games.txt").write_text("\n".join(nets) + "\n", encoding="utf-8")
    # отдельно только Valve — для плитки Steam (игры Steam работают и без плитки «Игры»)
    valve = sorted(_valve())
    (lists_dir / "ipset-valve.txt").write_text("\n".join(valve) + "\n", encoding="utf-8")
    (lists_dir / "ipset-games-exclude.txt").write_text("\n".join(riot()) + "\n", encoding="utf-8")
    return len(nets)


if __name__ == "__main__":
    n = update(Path(__file__).parent / "lists")
    print(f"ipset-games.txt: {n} подсетей")
