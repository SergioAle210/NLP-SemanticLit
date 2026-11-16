"""Prepara de forma reproducible los corpus de la configuración efectiva.

Uso: ``python -m gamerag.bootstrap``. No descarga fuentes ni modelos y no llama
al LLM. Un perfil con búsqueda secundaria prepara también ``*-multi.jsonl``.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from gamerag.games import GameConfig, load_all_games
from gamerag.ingest.build import ChunkerName, build_chunks
from gamerag.settings import Settings, get_settings


@dataclass(frozen=True)
class PreparedCorpus:
    game: str
    tag: str
    status: str  # built | reused
    chunks: int
    path: str
    fingerprint: str


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def corpus_fingerprint(cfg: GameConfig, root: Path, chunker: str, *, extras: bool) -> str:
    """Incluye configuración, revisiones, bytes de las fuentes y código de ingesta."""
    files = {}
    snapshots = [cfg.snapshot_dir] + ([extra.snapshot_dir for extra in cfg.extra_sources] if extras else [])
    for directory in snapshots:
        snapshot = root / directory
        manifest_path = snapshot / "manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        files[str(directory / "manifest.json")] = _digest(manifest_bytes)
        manifest = json.loads(manifest_bytes)
        for page in manifest["pages"]:
            path = snapshot / page["file"]
            files[str(directory / page["file"])] = _digest(path.read_bytes())
    ingest_dir = Path(__file__).parent / "ingest"
    implementation = {path.name: _digest(path.read_bytes()) for path in sorted(ingest_dir.glob("*.py"))}
    payload = {"schema": 1, "game": cfg.model_dump(mode="json"), "chunker": chunker,
               "extras": extras, "sources": files, "ingest": implementation}
    return _digest(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _prepare(cfg: GameConfig, settings: Settings, *, extras: bool) -> PreparedCorpus:
    tag = settings.chunker + ("-multi" if extras else "")
    out = settings.path(settings.data_dir) / "processed" / cfg.game_id
    chunks_path, stats_path = out / f"chunks.{tag}.jsonl", out / f"stats.{tag}.json"
    metadata_path = out / f"bootstrap.{tag}.json"
    fingerprint = corpus_fingerprint(cfg, settings.root, settings.chunker, extras=extras)
    try:
        cached = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (cached["fingerprint"] == fingerprint
                and cached["chunks_sha256"] == _digest(chunks_path.read_bytes())
                and cached["stats_sha256"] == _digest(stats_path.read_bytes())):
            return PreparedCorpus(cfg.game_id, tag, "reused", cached["chunks"], str(chunks_path), fingerprint)
    except (OSError, ValueError, KeyError, TypeError):
        pass  # caché ausente, anterior o incompleta: reconstruir desde los snapshots
    chunks, stats = build_chunks(cfg, settings.root, chunker=cast(ChunkerName, settings.chunker), extras=extras)
    chunks_text = "".join(chunk.model_dump_json() + "\n" for chunk in chunks)
    stats_text = json.dumps(stats, indent=2, ensure_ascii=False) + "\n"
    metadata = {"schema": 1, "fingerprint": fingerprint, "chunks": len(chunks),
                "chunks_sha256": _digest(chunks_text.encode("utf-8")),
                "stats_sha256": _digest(stats_text.encode("utf-8"))}
    _atomic_text(chunks_path, chunks_text)
    _atomic_text(stats_path, stats_text)
    # Publicar el manifiesto al final: un arranque interrumpido no valida salidas parciales.
    _atomic_text(metadata_path, json.dumps(metadata, indent=2) + "\n")
    return PreparedCorpus(cfg.game_id, tag, "built", len(chunks), str(chunks_path), fingerprint)


def ensure_corpora(settings: Settings) -> list[PreparedCorpus]:
    if settings.chunker not in ("fixed", "structural", "rows"):
        raise ValueError(f"chunker desconocido: {settings.chunker}")
    games = load_all_games(settings.path(settings.games_config_dir))
    unknown = set(settings.only_games) - games.keys()
    if unknown:
        raise ValueError(f"juegos desconocidos: {', '.join(sorted(unknown))}")
    selected = [cfg for game, cfg in games.items() if not settings.only_games or game in settings.only_games]
    results = []
    for cfg in selected:
        results.append(_prepare(cfg, settings, extras=False))
        if settings.secondary_search:
            results.append(_prepare(cfg, settings, extras=True))
    return results


def main() -> None:
    settings = get_settings()
    effective = settings.model_dump(include={
        "profile", "generator", "retriever", "embedding_model", "chunker", "query_expansion", "only_games",
        "use_graph", "evidence_eval", "secondary_search", "secondary_mode", "secondary_k",
        "security_guards", "spoiler_gates",
    })
    effective["full_without_key"] = settings.profile == "full" and settings.anthropic_api_key is None
    print(json.dumps({"configuration": effective}, ensure_ascii=False))
    for result in ensure_corpora(settings):
        print(json.dumps(asdict(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
