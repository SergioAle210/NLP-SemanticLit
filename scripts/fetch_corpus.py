"""Descarga el corpus de varias wikis por juego según `config/sources.yaml` (MediaWiki API, solo texto).

    python scripts/fetch_corpus.py --list                    # qué se descargaría
    python scripts/fetch_corpus.py gta_sa oot                # solo esos juegos
    python scripts/fetch_corpus.py --all --skip-existing     # todo lo que falte

Por cada (juego, fuente) escribe `data/wiki_snapshot/<sitio>/<juego>/pages/*.wiki` y `manifest.json` (título, URL,
revid, licencia), igual que `download_wiki.py`. Selección de páginas por `prefix` (subpáginas), `categories`
(miembros de categorías) o `titles` (lista explícita; los que no existen se reportan, no fallan). `limit` acota las
páginas por fuente y `min_chars` descarta esbozos. El contenido sigue la licencia de cada sitio (ver manifest).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import yaml

UA = {"User-Agent": "Mozilla/5.0 (CC3103 UVG educational NLP project)"}
ROOT = pathlib.Path(__file__).resolve().parents[1]


def api_get(api: str, params: dict, retries: int = 4) -> dict:
    url = api + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as resp:
                return json.load(resp)
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def pages_by_prefix(api: str, prefix: str) -> list[str]:
    out, cont = [prefix], {}
    while True:
        d = api_get(api, {"action": "query", "list": "allpages", "apprefix": prefix.replace(" ", "_") + "/",
                          "aplimit": 500, "format": "json", **cont})
        out += [p["title"] for p in d["query"]["allpages"]]
        if "continue" not in d:
            return out
        cont = d["continue"]


def pages_by_category(api: str, category: str, limit: int) -> list[str]:
    out, cont = [], {}
    while len(out) < limit:
        d = api_get(api, {"action": "query", "list": "categorymembers", "cmtitle": f"Category:{category}",
                          "cmnamespace": 0, "cmlimit": 500, "format": "json", **cont})
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            break
        cont = d["continue"]
    return out[:limit]


def fetch_page(api: str, title: str) -> dict | None:
    d = api_get(api, {"action": "parse", "page": title, "prop": "wikitext|revid", "redirects": 1, "format": "json"})
    if "error" in d or "parse" not in d:
        return None
    p = d["parse"]
    return {"title": p["title"], "revid": p.get("revid"), "text": p["wikitext"]["*"]}


def fname(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", title.replace("/", "__")) + ".wiki"


def download(site: dict, spec: dict, out: pathlib.Path, delay: float) -> dict:
    api = site["api"]
    titles: list[str] = []
    if "prefix" in spec:
        titles += pages_by_prefix(api, spec["prefix"])
    cats = spec.get("categories", [])
    for cat in cats:  # el tope se reparte entre categorías para que una grande no desplace a las demás
        titles += pages_by_category(api, cat, max(1, spec.get("limit", 200) // len(cats)))
    titles += spec.get("titles", [])
    titles = list(dict.fromkeys(titles))[: spec.get("limit", 10_000)]

    (out / "pages").mkdir(parents=True, exist_ok=True)
    manifest, missing, seen = [], [], set()
    for title in titles:
        page = fetch_page(api, title)
        time.sleep(delay)
        if page is None or page["title"] in seen:
            if page is None:
                missing.append(title)
            continue
        if len(page["text"]) < spec.get("min_chars", 400) or page["text"].lstrip().lower().startswith("#redirect"):
            continue
        seen.add(page["title"])
        (out / "pages" / fname(page["title"])).write_text(page["text"], encoding="utf-8", newline="\n")
        manifest.append({"title": page["title"],
                         "url": site["url_base"] + urllib.parse.quote(page["title"].replace(" ", "_")),
                         "revid": page["revid"], "file": "pages/" + fname(page["title"]), "chars": len(page["text"])})
    report = {"source": site["name"], "license": site["license"], "license_note": site.get("license_note", ""),
              "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
              "total_chars": sum(m["chars"] for m in manifest), "missing_titles": missing, "pages": manifest}
    (out / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8",
                                       newline="\n")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("games", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--spec", default="config/sources.yaml")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / args.spec).read_text(encoding="utf-8"))
    sites = {k: {"name": k, **v} for k, v in cfg["sites"].items()}
    wanted = list(cfg["games"]) if args.all else args.games
    if not wanted:
        ap.error("indica juegos o --all")
    for game in wanted:
        for spec in cfg["games"][game]:
            site = sites[spec["site"]]
            out = ROOT / "data" / "wiki_snapshot" / site["name"] / game
            label = f"{game:18} {site['name']:16}"
            if args.list:
                print(label, {k: v for k, v in spec.items() if k != "site"})
                continue
            if args.skip_existing and (out / "manifest.json").exists():
                print(label, "ya existe; se omite")
                continue
            try:
                rep = download(site, spec, out, args.delay)
                print(f"{label} {len(rep['pages']):4} páginas {rep['total_chars']/1000:8.0f} KB"
                      f"  faltan: {len(rep['missing_titles'])}", flush=True)
            except Exception as exc:  # noqa: BLE001 - una fuente caída no detiene a las demás
                print(f"{label} ERROR {type(exc).__name__}: {exc}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
