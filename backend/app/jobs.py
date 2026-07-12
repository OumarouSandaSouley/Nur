"""File de jobs sequentielle pour la generation video."""

from __future__ import annotations

import sys
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .backgrounds import list_library, save_upload
from .pipeline import JobConfig, ROOT, generer_video

JOBS_DIR = ROOT / "tmp_jobs"
UPLOADS_DIR = ROOT / "uploads"


def _log(msg: str) -> None:
    """Log console compatible Windows (cp1252)."""
    stream = getattr(sys, "stdout", None)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        safe = msg.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe, flush=True)


@dataclass
class Job:
    id: str
    config: JobConfig
    status: str = "queued"
    progress: int = 0
    stage: str = "queued"
    message: str = "En file d'attente"
    output_path: str | None = None
    output_name: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "message": self.message,
            "output_name": self.output_name,
            "error": self.error,
            "created_at": self.created_at,
            "config": {
                "reciter_id": self.config.reciter_id,
                "surah": self.config.surah,
                "ayah_from": self.config.ayah_from,
                "ayah_to": self.config.ayah_to,
                "subtitle_style": self.config.subtitle_style,
                "video_style": self.config.video_style,
                "include_basmala": self.config.include_basmala,
            },
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._queue: list[str] = []
        self._cv = threading.Condition(self._lock)
        self._worker: threading.Thread | None = None
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self._start_worker()

    def _start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="nur-job-worker"
        )
        self._worker.start()
        _log("[jobs] worker demarre")

    def create(self, config: JobConfig) -> Job:
        self._start_worker()
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, config=config)
        with self._cv:
            self._jobs[job_id] = job
            self._queue.append(job_id)
            _log(f"[jobs] queued {job_id} (file={len(self._queue)})")
            self._cv.notify()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_recent(self, limit: int = 20) -> list[Job]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]

    def _worker_loop(self) -> None:
        while True:
            with self._cv:
                while not self._queue:
                    self._cv.wait(timeout=1.0)
                if not self._queue:
                    continue
                job_id = self._queue.pop(0)
            _log(f"[jobs] run {job_id}")
            self._run_job(job_id)

    def _run_job(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return

        job_dir = JOBS_DIR / job_id

        def on_progress(stage: str, pct: int, message: str) -> None:
            job.status = "running"
            job.stage = stage
            job.progress = pct
            job.message = message
            _log(f"[jobs] {job_id} {pct}% {stage}: {message}")

        try:
            job.status = "running"
            job.message = "Demarrage..."
            job.progress = 1
            output = generer_video(job.config, job_dir, on_progress=on_progress)
            job.status = "done"
            job.progress = 100
            job.stage = "done"
            job.message = "Video prete"
            job.output_path = str(output)
            job.output_name = output.name
            _log(f"[jobs] done {job_id} -> {output.name}")
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.stage = "failed"
            job.error = str(exc)
            job.message = "Echec de la generation"
            _log(f"[jobs] FAIL {job_id}: {exc}")
            traceback.print_exc()
        finally:
            for name in ("audio_complet.wav", "fond_pret.mp4"):
                p = job_dir / name
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass


manager = JobManager()

__all__ = ["manager", "save_upload", "list_library", "Job", "JobManager"]
