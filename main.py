#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ancien point d'entrée CLI — l'app web est maintenant le mode principal.

  python run_server.py          # API
  cd frontend && npm run dev    # UI

Ce fichier lance une génération rapide Al-Fatiha 1-7 (fond auto) pour smoke test.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.pipeline import JobConfig, generer_video  # noqa: E402

if __name__ == "__main__":
    out = generer_video(
        JobConfig(
            reciter_id=3,
            surah=112,
            ayah_from=1,
            ayah_to=4,
            subtitle_style="classic",
            video_style="clean",
            bg_path=None,
        ),
        Path("tmp_jobs") / "cli_test",
        on_progress=lambda stage, pct, msg: print(f"[{pct:3d}%] {stage}: {msg}"),
    )
    print(f"OK → {out}")
