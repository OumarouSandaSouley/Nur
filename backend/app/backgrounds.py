"""Téléchargement / bibliothèque de fonds vidéo + recherche Pexels."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

from .data import HEADERS
from .pipeline import ROOT

UPLOADS_DIR = ROOT / "uploads"
ASSETS_FONDS = ROOT / "assets" / "fonds"
CACHE_URLS = ROOT / "cache" / "fonds_url"

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def list_library() -> list[dict]:
    """Fonds assets + uploads + telechargements URL/Pexels."""
    ASSETS_FONDS.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_URLS.mkdir(parents=True, exist_ok=True)
    thumbs = ROOT / "cache" / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []

    def enrich(p: Path, source: str, item_id: str) -> dict:
        duration = None
        try:
            from .pipeline import obtenir_duree

            duration = round(obtenir_duree(str(p)), 1)
        except Exception:  # noqa: BLE001
            pass
        thumb_name = f"{p.stem}.jpg"
        thumb_path = thumbs / thumb_name
        if not thumb_path.is_file():
            try:
                subprocess_thumb(p, thumb_path)
            except Exception:  # noqa: BLE001
                pass
        return {
            "id": item_id,
            "name": p.name if source in ("upload", "url") else p.stem,
            "source": source,
            "path": str(p),
            "duration": duration,
            "thumb_url": f"/api/backgrounds/thumb/{thumb_name}" if thumb_path.is_file() else None,
        }

    for p in sorted(ASSETS_FONDS.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.suffix.lower() in VIDEO_EXTS:
            items.append(enrich(p, "library", f"asset:{p.name}"))

    for p in sorted(UPLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.suffix.lower() in VIDEO_EXTS:
            items.append(enrich(p, "upload", f"upload:{p.name}"))

    for p in sorted(CACHE_URLS.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.suffix.lower() in VIDEO_EXTS:
            items.append(enrich(p, "url", f"url:{p.name}"))
    return items


def subprocess_thumb(video: Path, out: Path) -> None:
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "0.5",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            "scale=180:-1",
            str(out),
        ],
        capture_output=True,
        check=True,
    )


def delete_library_item(item_id: str) -> bool:
    path = resolve_library_id(item_id)
    if not path or not path.is_file():
        return False
    # assets locaux non supprimables
    if str(path).startswith(str(ASSETS_FONDS.resolve())):
        raise ValueError("Les fonds assets ne peuvent pas etre supprimes.")
    path.unlink(missing_ok=True)
    thumb = ROOT / "cache" / "thumbs" / f"{path.stem}.jpg"
    thumb.unlink(missing_ok=True)
    return True


def resolve_library_id(item_id: str) -> Path | None:
    if ":" not in item_id:
        for folder in (ASSETS_FONDS, UPLOADS_DIR, CACHE_URLS):
            p = folder / item_id
            if p.is_file():
                return p
        return None
    kind, name = item_id.split(":", 1)
    folders = {
        "asset": ASSETS_FONDS,
        "upload": UPLOADS_DIR,
        "url": CACHE_URLS,
        "pexels": CACHE_URLS,
    }
    folder = folders.get(kind)
    if not folder:
        return None
    p = folder / name
    return p if p.is_file() else None


def save_upload(filename: str, data: bytes) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in filename if c.isalnum() or c in "._-") or "fond.mp4"
    if Path(safe).suffix.lower() not in VIDEO_EXTS:
        safe += ".mp4"
    path = UPLOADS_DIR / f"{uuid.uuid4().hex[:8]}_{safe}"
    path.write_bytes(data)
    return path


def import_video_url(
    url: str,
    display_name: str | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> dict:
    """Telecharge une URL (Pexels / mp4) dans la bibliotheque (cache fonds_url)."""
    dest = download_background_url(url, on_progress=on_progress)
    if display_name:
        safe = "".join(c for c in display_name if c.isalnum() or c in "._- ")[:40].strip()
        safe = safe.replace(" ", "_") or dest.stem
        ext = dest.suffix.lower() or ".mp4"
        renamed = dest.with_name(f"{uuid.uuid4().hex[:8]}_{safe}{ext}")
        try:
            dest.rename(renamed)
            dest = renamed
        except OSError:
            pass

    thumbs = ROOT / "cache" / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    thumb_name = f"{dest.stem}.jpg"
    thumb_path = thumbs / thumb_name
    try:
        subprocess_thumb(dest, thumb_path)
    except Exception:  # noqa: BLE001
        pass

    duration = None
    try:
        from .pipeline import obtenir_duree

        duration = round(obtenir_duree(str(dest)), 1)
    except Exception:  # noqa: BLE001
        pass

    return {
        "id": f"url:{dest.name}",
        "name": dest.name,
        "source": "url",
        "path": str(dest),
        "duration": duration,
        "thumb_url": f"/api/backgrounds/thumb/{thumb_name}" if thumb_path.is_file() else None,
    }


def download_background_url(
    url: str,
    on_progress: Callable[[int, str], None] | None = None,
) -> Path:
    """Télécharge une vidéo depuis une URL directe (mp4…) vers le cache."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL invalide (http/https requis).")

    CACHE_URLS.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext not in VIDEO_EXTS:
        ext = ".mp4"
    dest = CACHE_URLS / f"{uuid.uuid4().hex[:10]}{ext}"

    with requests.get(url, headers=HEADERS, timeout=120, stream=True) as r:
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype:
            raise ValueError(
                "L’URL renvoie une page web, pas une vidéo. Colle un lien .mp4 direct."
            )
        total = int(r.headers.get("Content-Length") or 0)
        size = 0
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                size += len(chunk)
                if on_progress and total:
                    pct = min(95, int(100 * size / total))
                    on_progress(pct, f"Fond {size // (1024 * 1024)} Mo")
                if size > 120 * 1024 * 1024:
                    dest.unlink(missing_ok=True)
                    raise ValueError(
                        "Vidéo trop volumineuse (>120 Mo). Choisis une qualité ≤1080p."
                    )
    if dest.stat().st_size < 5000:
        dest.unlink(missing_ok=True)
        raise ValueError("Téléchargement trop petit — URL probablement incorrecte.")
    return dest


def search_pexels_videos(query: str, per_page: int = 12) -> dict:
    """Recherche Pexels — préfère ~720–1080p (pas de 4K)."""
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return {
            "ok": False,
            "need_key": True,
            "message": (
                "Ajoute PEXELS_API_KEY dans .env "
                "(clé gratuite : https://www.pexels.com/api/)."
            ),
            "videos": [],
        }

    q = query.strip() or "nature"
    r = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": q, "per_page": per_page, "orientation": "portrait"},
        headers={"Authorization": key},
        timeout=30,
    )
    if r.status_code == 401:
        return {
            "ok": False,
            "need_key": True,
            "message": "Clé Pexels invalide.",
            "videos": [],
        }
    r.raise_for_status()
    data = r.json()
    videos = []
    for v in data.get("videos", []):
        files = [f for f in (v.get("video_files") or []) if f.get("link")]
        if not files:
            continue

        def score(f: dict) -> tuple:
            h = int(f.get("height") or 0)
            w = int(f.get("width") or 0)
            portrait = 1 if w and h and w <= h else 0
            if 700 <= h <= 1100:
                closeness = 0
            elif 500 <= h < 700:
                closeness = 1
            elif 1100 < h <= 1440:
                closeness = 2
            else:
                closeness = 3 + abs(h - 1080) // 500
            return (-portrait, closeness, abs(h - 1080))

        best = min(files, key=score)
        videos.append(
            {
                "id": str(v.get("id")),
                "url": best["link"],
                "preview": (v.get("image") or ""),
                "duration": v.get("duration"),
                "user": (v.get("user") or {}).get("name", "Pexels"),
                "width": best.get("width"),
                "height": best.get("height"),
            }
        )
    return {"ok": True, "need_key": False, "message": "", "videos": videos}
