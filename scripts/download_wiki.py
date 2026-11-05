"""Descarga un snapshot reproducible de las páginas de un juego en StrategyWiki.

Usa la API de MediaWiki (la web directa responde 403 a clientes automáticos).
Guarda el wikitext de cada página y un manifiesto con el revid de cada una,
para que el snapshot quede versionado.

Uso:
    python scripts/download_wiki.py "The Legend of Zelda" data/wiki_snapshot/strategywiki/zelda1
    python scripts/download_wiki.py "Ninja Gaiden (NES)" data/wiki_snapshot/strategywiki/ninja_gaiden_nes

Licencia del contenido descargado: CC BY-SA 4.0 (StrategyWiki).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

API = "https://strategywiki.org/w/api.php"
UA = {"User-Agent": "Mozilla/5.0 (CC3103 UVG educational NLP project)"}
LICENSE = {
    "name": "Creative Commons Attribution-ShareAlike 4.0",
    "url": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def api_get(params: dict, retries: int = 4) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except OSError as exc:  # URLError, SSL y timeouts heredan de OSError
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"  reintento {attempt + 1} en {wait}s ({exc})")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def list_pages(game: str) -> list[str]:
    data = api_get({
        "action": "query", "list": "allpages",
        "apprefix": game.replace(" ", "_") + "/", "aplimit": 500, "format": "json",
    })
    return [game] + [p["title"] for p in data["query"]["allpages"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("game", help='Título de la página raíz, p. ej. "The Legend of Zelda"')
    ap.add_argument("out_dir")
    ap.add_argument("--delay", type=float, default=0.5, help="Pausa entre requests (cortesía)")
    args = ap.parse_args()

    out = pathlib.Path(args.out_dir)
    pages_dir = out / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for title in list_pages(args.game):
        parsed = api_get({"action": "parse", "page": title, "prop": "wikitext|revid", "format": "json"})["parse"]
        text = parsed["wikitext"]["*"]
        fname = title.replace("/", "__").replace(" ", "_").replace(":", "") + ".wiki"
        # newline="\n": evita CRLF en Windows para que los hashes sean estables entre máquinas
        (pages_dir / fname).write_text(text, encoding="utf-8", newline="\n")
        manifest.append({
            "title": title,
            "url": "https://strategywiki.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "revid": parsed.get("revid"),
            "file": f"pages/{fname}",
            "chars": len(text),
        })
        print(f"{len(text):>7}  {title}")
        time.sleep(args.delay)

    (out / "manifest.json").write_text(json.dumps({
        "source": "StrategyWiki",
        "game": args.game,
        "license": LICENSE,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total_chars": sum(m["chars"] for m in manifest),
        "pages": manifest,
    }, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("TOTAL chars:", sum(m["chars"] for m in manifest), "| pages:", len(manifest))


if __name__ == "__main__":
    main()
