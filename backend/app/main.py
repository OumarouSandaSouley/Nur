"""API FastAPI — Studio Vidéo Coranique."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .backgrounds import (
    list_library,
    resolve_library_id,
    save_upload,
    search_pexels_videos,
)
from .data import liste_reciteurs, liste_sourates
from .jobs import manager
from .pipeline import JobConfig, ROOT, valider_config
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


@app.get("/api/surahs")
def get_surahs():
    return liste_sourates()


@app.get("/api/styles")
def get_styles():
    return {
        "subtitles": liste_styles_sous_titres(),
        "video": liste_styles_video(),
    }


@app.get("/api/backgrounds")
def get_backgrounds():
    return list_library()


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
    background_id: str | None = Form(None),
    background_url: str | None = Form(None),
    background: UploadFile | None = File(None),
):
    bg_path: str | None = None
    basmala = include_basmala.strip().lower() in ("1", "true", "yes", "on")
    bg_url: str | None = None

    try:
        if background and background.filename:
            data = await background.read()
            if len(data) < 1000:
                raise HTTPException(400, "Fichier de fond trop petit ou vide.")
            bg_path = str(save_upload(background.filename, data))
        elif background_url and background_url.strip():
            # Téléchargé dans le worker (progression visible)
            bg_url = background_url.strip()
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
        background_url=bg_url,
        include_basmala=basmala,
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


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable.")
    return job.to_dict()


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
