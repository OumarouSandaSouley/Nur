"""Edition simple des MP4 generes (trim + concat)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .pipeline import OUTPUTS, nettoyer_nom, obtenir_duree


def _safe_output_name(name: str) -> Path:
    safe = Path(name).name
    if not safe.endswith(".mp4") or ".." in safe:
        raise ValueError("Nom de fichier invalide.")
    path = OUTPUTS / safe
    if not path.is_file():
        raise ValueError("Video introuvable.")
    return path


def trim_output(
    filename: str,
    start: float = 0.0,
    end: float | None = None,
    suffix: str = "trim",
) -> dict:
    src = _safe_output_name(filename)
    start = max(0.0, float(start))
    duration = obtenir_duree(str(src))
    if end is None or end <= 0:
        end = duration
    end = min(float(end), duration)
    if end - start < 0.4:
        raise ValueError("La coupe doit faire au moins 0.4s.")

    out_name = nettoyer_nom(f"{src.stem}_{suffix}.mp4")
    out = OUTPUTS / out_name
    # Re-encode for accurate cuts (stream copy often fails on keyframes)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", str(src),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Trim echoue : {result.stderr[-800:]}")

    meta = {
        "source": src.name,
        "edit": "trim",
        "start": round(start, 2),
        "end": round(end, 2),
        "duration_seconds": round(obtenir_duree(str(out)), 1),
        "output_name": out_name,
    }
    (OUTPUTS / f"{out.stem}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "ok": True,
        "name": out_name,
        "preview_url": f"/api/history/{out_name}/preview",
        "download_url": f"/api/history/{out_name}/download",
        "duration": meta["duration_seconds"],
    }


def concat_outputs(filenames: list[str], suffix: str = "montage") -> dict:
    if len(filenames) < 2:
        raise ValueError("Selectionne au moins 2 videos.")
    if len(filenames) > 8:
        raise ValueError("Maximum 8 videos.")

    paths = [_safe_output_name(n) for n in filenames]
    work = OUTPUTS / "_edit_tmp"
    work.mkdir(parents=True, exist_ok=True)

    # Normalize each clip then concat (different encodes are common)
    segs: list[Path] = []
    for i, src in enumerate(paths):
        seg = work / f"c_{i:02d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                   "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-pix_fmt", "yuv420p",
            str(seg),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Normalisation clip {i} echouee : {result.stderr[-600:]}")
        segs.append(seg)

    liste = work / "concat.txt"
    lines = []
    for s in segs:
        p = str(s.resolve()).replace("\\", "/")
        p = p.replace("'", r"'\''")
        lines.append(f"file '{p}'")
    liste.write_text("\n".join(lines), encoding="utf-8")

    out_name = nettoyer_nom(f"montage_{len(paths)}clips_{suffix}.mp4")
    # unique-ish
    import time

    out_name = nettoyer_nom(f"montage_{int(time.time())}_{len(paths)}clips.mp4")
    out = OUTPUTS / out_name
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(liste),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # fallback reencode
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(liste),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(out),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Concat echoue : {result.stderr[-800:]}")

    meta = {
        "sources": [p.name for p in paths],
        "edit": "concat",
        "duration_seconds": round(obtenir_duree(str(out)), 1),
        "output_name": out_name,
    }
    (OUTPUTS / f"{out.stem}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "ok": True,
        "name": out_name,
        "preview_url": f"/api/history/{out_name}/preview",
        "download_url": f"/api/history/{out_name}/download",
        "duration": meta["duration_seconds"],
    }
