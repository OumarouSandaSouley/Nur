"""API FastAPI — Studio Vidéo Coranique."""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .backgrounds import (
    delete_library_item,
    list_library,
    resolve_library_id,
    save_upload,
    search_pexels_videos,
)
from .data import liste_reciteurs, liste_sourates
from .jobs import manager
from .pipeline import OUTPUTS, JobConfig, ROOT, estimer_duree, valider_config
from .styles import liste_styles_sous_titres, liste_styles_video

load_dotenv(ROOT / ".env")

app = FastAPI(title="Studio Vidéo Coranique", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/reciters")
def get_reciters():
    return liste_reciteurs()


@app.get("/api/reciters/{reciter_id}/preview")
def reciter_preview(reciter_id: int, surah: int = Query(1), ayah: int = Query(1)):
    """Stream le premier verset (telecharge si besoin) pour apercu audio."""
    from .data import RECITEURS
    from .pipeline import CACHE_AUDIO, EVERYAYAH_BASE, HEADERS
    import requests as req

    if reciter_id not in RECITEURS:
        raise HTTPException(400, "Reciteur invalide.")
    dossier = RECITEURS[reciter_id]["dossier"]
    cache_dir = CACHE_AUDIO / dossier
    cache_dir.mkdir(parents=True, exist_ok=True)
    nom = f"{surah:03d}{ayah:03d}.mp3"
    path = cache_dir / nom
    if not path.is_file() or path.stat().st_size < 1000:
        url = f"{EVERYAYAH_BASE}/{dossier}/{nom}"
        r = req.get(url, headers=HEADERS, timeout=45)
        if r.status_code != 200 or len(r.content) < 1000:
            raise HTTPException(404, "Audio introuvable.")
        path.write_bytes(r.content)
    return FileResponse(path, media_type="audio/mpeg", filename=nom)


@app.get("/api/surahs")
def get_surahs():
    return liste_sourates()


@app.get("/api/styles")
def get_styles():
    return {
        "subtitles": liste_styles_sous_titres(),
        "video": liste_styles_video(),
    }


@app.get("/api/estimate")
def estimate_duration(
    reciter_id: int = Query(...),
    surah: int = Query(...),
    ayah_from: int = Query(...),
    ayah_to: int = Query(...),
    include_basmala: bool = Query(True),
):
    try:
        return estimer_duree(reciter_id, surah, ayah_from, ayah_to, include_basmala)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/backgrounds")
def get_backgrounds():
    return list_library()


@app.get("/api/backgrounds/thumb/{name}")
def background_thumb(name: str):
    safe = Path(name).name
    path = ROOT / "cache" / "thumbs" / safe
    if not path.is_file():
        raise HTTPException(404, "Miniature introuvable.")
    return FileResponse(path, media_type="image/jpeg")


@app.delete("/api/backgrounds/{item_id:path}")
def delete_background(item_id: str):
    try:
        ok = delete_library_item(item_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not ok:
        raise HTTPException(404, "Fond introuvable.")
    return {"ok": True}


@app.get("/api/pexels/search")
def pexels_search(q: str = Query("nature", min_length=1), per_page: int = Query(12, ge=1, le=30)):
    try:
        return search_pexels_videos(q, per_page=per_page)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Recherche Pexels échouée : {exc}") from exc


@app.post("/api/uploads")
async def upload_only(background: UploadFile = File(...)):
    if not background.filename:
        raise HTTPException(400, "Fichier manquant.")
    data = await background.read()
    if len(data) < 1000:
        raise HTTPException(400, "Fichier trop petit.")
    path = save_upload(background.filename, data)
    return {
        "id": f"upload:{path.name}",
        "name": path.name,
        "source": "upload",
        "path": str(path),
    }


@app.post("/api/jobs")
async def create_job(
    reciter_id: int = Form(...),
    surah: int = Form(...),
    ayah_from: int = Form(...),
    ayah_to: int = Form(...),
    subtitle_style: str = Form("classic"),
    video_style: str = Form("clean"),
    include_basmala: str = Form("true"),
    translation: str = Form("none"),
    font_size: int | None = Form(None),
    watermark_mode: str = Form("none"),
    watermark_text: str = Form(""),
    background_id: str | None = Form(None),
    background_ids: str | None = Form(None),  # JSON list for multi-fonds
    background_url: str | None = Form(None),
    background: UploadFile | None = File(None),
):
    bg_path: str | None = None
    bg_paths: list[str] | None = None
    basmala = include_basmala.strip().lower() in ("1", "true", "yes", "on")
    bg_url: str | None = None
    tr = translation.strip().lower() if translation else "none"
    if tr not in ("none", "fr", "en"):
        raise HTTPException(400, "Traduction invalide (none/fr/en).")
    wm = (watermark_mode or "none").strip().lower()
    if wm not in ("none", "logo", "text"):
        raise HTTPException(400, "Watermark invalide (none/logo/text).")
    wm_text = (watermark_text or "").strip()[:40]
    if wm == "text" and not wm_text:
        raise HTTPException(400, "Indique un pseudo pour le watermark texte.")

    try:
        if background and background.filename:
            data = await background.read()
            if len(data) < 1000:
                raise HTTPException(400, "Fichier de fond trop petit ou vide.")
            bg_path = str(save_upload(background.filename, data))
        elif background_url and background_url.strip():
            # Téléchargé dans le worker (progression visible)
            bg_url = background_url.strip()
        elif background_ids and background_ids.strip():
            try:
                ids = json.loads(background_ids)
            except json.JSONDecodeError as exc:
                raise HTTPException(400, "background_ids JSON invalide.") from exc
            if not isinstance(ids, list) or not ids:
                raise HTTPException(400, "Liste de fonds vide.")
            resolved_list: list[str] = []
            for bid in ids:
                resolved = resolve_library_id(str(bid))
                if not resolved:
                    raise HTTPException(400, f"Fond inconnu: {bid}")
                resolved_list.append(str(resolved))
            bg_paths = resolved_list
            bg_path = resolved_list[0]
        elif background_id:
            resolved = resolve_library_id(background_id)
            if not resolved:
                raise HTTPException(400, "Fond inconnu.")
            bg_path = str(resolved)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Fond invalide : {exc}") from exc

    cfg = JobConfig(
        reciter_id=reciter_id,
        surah=surah,
        ayah_from=ayah_from,
        ayah_to=ayah_to,
        subtitle_style=subtitle_style,
        video_style=video_style,
        bg_path=bg_path,
        bg_paths=bg_paths,
        background_url=bg_url,
        include_basmala=basmala,
        translation=tr,
        font_size=font_size if font_size and 12 <= font_size <= 48 else None,
        watermark_mode=wm,
        watermark_text=wm_text,
    )
    try:
        valider_config(cfg)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    job = manager.create(cfg)
    return job.to_dict()


@app.get("/api/jobs")
def list_jobs():
    return [j.to_dict() for j in manager.list_recent()]


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = manager.cancel(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable.")
    return job.to_dict()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable.")
    return job.to_dict()


@app.get("/api/history")
def history():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(OUTPUTS.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        meta_path = OUTPUTS / f"{p.stem}.json"
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                meta = {}
        items.append(
            {
                "id": p.name,
                "name": p.name,
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
                "has_srt": (OUTPUTS / f"{p.stem}.srt").is_file(),
                "meta": meta,
                "preview_url": f"/api/history/{p.name}/preview",
                "download_url": f"/api/history/{p.name}/download",
            }
        )
    return items[:50]


@app.get("/api/history/{filename}/preview")
def history_preview(filename: str):
    path = _safe_output(filename)
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/history/{filename}/download")
def history_download(filename: str):
    path = _safe_output(filename)
    return FileResponse(path, media_type="video/mp4", filename=filename)


@app.delete("/api/history/{filename}")
def history_delete(filename: str):
    path = _safe_output(filename)
    stem = path.stem
    path.unlink(missing_ok=True)
    (OUTPUTS / f"{stem}.json").unlink(missing_ok=True)
    (OUTPUTS / f"{stem}.srt").unlink(missing_ok=True)
    return {"ok": True}


def _safe_output(filename: str) -> Path:
    name = Path(filename).name
    if not name.endswith(".mp4") or ".." in name:
        raise HTTPException(400, "Nom de fichier invalide.")
    path = OUTPUTS / name
    if not path.is_file():
        raise HTTPException(404, "Video introuvable.")
    return path


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable.")
    if job.status != "done" or not job.output_path:
        raise HTTPException(400, "Vidéo pas encore prête.")
    path = Path(job.output_path)
    if not path.is_file():
        raise HTTPException(404, "Fichier manquant.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=job.output_name or path.name,
    )


@app.get("/api/jobs/{job_id}/preview")
def preview_job(job_id: str):
    """Même fichier que download, pour lecture inline dans le navigateur."""
    return download_job(job_id)


FRONTEND_DIST = ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
