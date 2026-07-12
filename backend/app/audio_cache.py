"""Inventaire du cache audio (MP3 téléchargés), classé par récitateur."""

from __future__ import annotations

import re
from pathlib import Path

from .data import RECITEURS, SOURATES
from .pipeline import CACHE_AUDIO, obtenir_duree

_VERSE_RE = re.compile(r"^(\d{3})(\d{3})\.mp3$", re.I)
_FULL_RE = re.compile(r"^(\d{3})_full\.mp3$", re.I)


def _dossier_to_reciter() -> dict[str, tuple[int, str]]:
    return {info["dossier"]: (rid, info["nom"]) for rid, info in RECITEURS.items()}


def list_audio_cache() -> list[dict]:
    """Liste les sons en cache, regroupés par récitateur puis sourate."""
    CACHE_AUDIO.mkdir(parents=True, exist_ok=True)
    by_dossier = _dossier_to_reciter()
    groups: list[dict] = []

    for folder in sorted(CACHE_AUDIO.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        rid, nom = by_dossier.get(folder.name, (0, folder.name.replace("_", " ")))
        surah_map: dict[int, dict] = {}
        file_count = 0
        total_bytes = 0

        for f in sorted(folder.glob("*.mp3")):
            if f.stat().st_size < 500:
                continue
            meta = _parse_audio_name(f.name)
            if not meta:
                continue
            surah = meta["surah"]
            bucket = surah_map.setdefault(
                surah,
                {
                    "surah": surah,
                    "name_fr": SOURATES[surah - 1][0] if 1 <= surah <= 114 else f"Sourate {surah}",
                    "name_ar": SOURATES[surah - 1][1] if 1 <= surah <= 114 else "",
                    "files": [],
                },
            )
            size = f.stat().st_size
            total_bytes += size
            file_count += 1
            duration = None
            try:
                duration = round(obtenir_duree(str(f)), 1)
            except Exception:  # noqa: BLE001
                pass
            bucket["files"].append(
                {
                    "name": f.name,
                    "ayah": meta["ayah"],
                    "kind": meta["kind"],
                    "size": size,
                    "duration": duration,
                    "play_url": f"/api/audio/{folder.name}/{f.name}",
                }
            )

        if not file_count:
            continue

        surahs = [surah_map[k] for k in sorted(surah_map.keys())]
        for s in surahs:
            s["files"].sort(key=lambda x: (0 if x["kind"] == "full" else 1, x["ayah"] or 0))

        groups.append(
            {
                "reciter_id": rid,
                "nom": nom,
                "dossier": folder.name,
                "file_count": file_count,
                "total_bytes": total_bytes,
                "surahs": surahs,
            }
        )

    groups.sort(key=lambda g: (g["nom"].lower(), g["dossier"]))
    return groups


def resolve_audio_file(dossier: str, filename: str) -> Path | None:
    safe_dir = Path(dossier).name
    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".mp3"):
        return None
    path = (CACHE_AUDIO / safe_dir / safe_name).resolve()
    root = CACHE_AUDIO.resolve()
    if not str(path).startswith(str(root)):
        return None
    return path if path.is_file() else None


def _parse_audio_name(name: str) -> dict | None:
    m = _FULL_RE.match(name)
    if m:
        return {"surah": int(m.group(1)), "ayah": None, "kind": "full"}
    m = _VERSE_RE.match(name)
    if m:
        surah = int(m.group(1))
        ayah = int(m.group(2))
        if ayah == 0:
            return {"surah": surah, "ayah": 0, "kind": "basmala"}
        return {"surah": surah, "ayah": ayah, "kind": "verse"}
    return None
