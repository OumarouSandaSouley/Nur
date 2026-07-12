"""Pipeline de génération vidéo coranique."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from .data import (
    API_TEXTE_ARABE,
    API_TRADUCTION,
    BISMILLAH_ARABE,
    BISMILLAH_EN,
    BISMILLAH_FR,
    EVERYAYAH_BASE,
    HAUTEUR_SORTIE,
    HEADERS,
    LARGEUR_SORTIE,
    NB_VERSETS,
    RECITEURS,
    SOURATES,
    TRADUCTIONS,
)
from .styles import VIDEO_STYLES, ass_force_style, decorate_srt_text

ProgressCallback = Callable[[str, int, str], None]

ROOT = Path(__file__).resolve().parents[2]
CACHE_AUDIO = ROOT / "cache" / "audio"
OUTPUTS = ROOT / "outputs"
ASSETS_FONDS = ROOT / "assets" / "fonds"
FONTS_DIR = ROOT / "assets" / "fonts"


@dataclass
class JobConfig:
    reciter_id: int
    surah: int
    ayah_from: int
    ayah_to: int
    subtitle_style: str = "classic"
    video_style: str = "clean"
    bg_path: str | None = None
    background_url: str | None = None
    include_basmala: bool = True
    font_name: str = "Traditional Arabic"
    translation: str = "none"  # none | fr | en
    font_size: int | None = None
    watermark_mode: str = "none"  # none | logo | text
    watermark_text: str = ""  # TikTok handle when mode=text
    bg_paths: list[str] | None = None  # multi-fonds montage


def estimer_duree(
    reciter_id: int,
    surah: int,
    ayah_from: int,
    ayah_to: int,
    include_basmala: bool = True,
) -> dict:
    """Estime la duree a partir du cache audio (ou approx 5s/verset)."""
    if reciter_id not in RECITEURS:
        raise ValueError("Reciteur invalide.")
    if not (1 <= surah <= 114):
        raise ValueError("Sourate invalide.")
    max_v = NB_VERSETS[surah - 1]
    if not (1 <= ayah_from <= ayah_to <= max_v):
        raise ValueError("Intervalle invalide.")

    dossier = RECITEURS[reciter_id]["dossier"]
    cache_dir = CACHE_AUDIO / dossier
    numeros = list(range(ayah_from, ayah_to + 1))
    if include_basmala and ayah_from == 1 and surah not in (1, 9):
        numeros = [0] + numeros

    total = 0.0
    known = 0
    missing = 0
    for n in numeros:
        path = cache_dir / f"{surah:03d}{n:03d}.mp3"
        if path.is_file() and path.stat().st_size > 1000:
            try:
                total += obtenir_duree(str(path))
                known += 1
                continue
            except Exception:  # noqa: BLE001
                pass
        total += 5.0  # approx
        missing += 1

    return {
        "seconds": round(total, 1),
        "formatted": _format_duree(total),
        "ayah_count": len(numeros),
        "from_cache": known,
        "estimated_ayahs": missing,
        "precise": missing == 0,
    }


def _format_duree(seconds: float) -> str:
    s = int(round(seconds))
    m, sec = divmod(s, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h {m:02d}m {sec:02d}s"
    if m:
        return f"{m}m {sec:02d}s"
    return f"{sec}s"


def verifier_ffmpeg() -> None:
    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            raise RuntimeError(
                f"'{exe}' est introuvable dans le PATH. Installez ffmpeg puis reessayez."
            )


def nettoyer_nom(nom: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", nom).strip()


def valider_config(cfg: JobConfig) -> None:
    if cfg.reciter_id not in RECITEURS:
        raise ValueError("Récitateur invalide (1–12).")
    if not (1 <= cfg.surah <= 114):
        raise ValueError("Sourate invalide (1–114).")
    max_v = NB_VERSETS[cfg.surah - 1]
    if not (1 <= cfg.ayah_from <= cfg.ayah_to <= max_v):
        raise ValueError(f"Intervalle invalide (1–{max_v}).")
    if cfg.subtitle_style not in (
        "classic",
        "gold",
        "center",
        "soft",
        "large",
        "shadow",
        "banner",
        "fade",
    ):
        raise ValueError("Style de sous-titres invalide.")
    if cfg.video_style not in VIDEO_STYLES:
        raise ValueError("Style video invalide.")
    if cfg.translation not in TRADUCTIONS:
        raise ValueError("Traduction invalide (none/fr/en).")
    if cfg.bg_path and not os.path.isfile(cfg.bg_path):
        raise ValueError(f"Video de fond introuvable : {cfg.bg_path}")


def telecharger_versets_audio(
    session: requests.Session,
    dossier_everyayah: str,
    numero_sourate: int,
    ayah_from: int,
    ayah_to: int,
    include_basmala: bool,
    on_progress: ProgressCallback | None = None,
) -> list[tuple[int, str]]:
    """Télécharge (ou réutilise le cache) les MP3 de l'intervalle demandé."""
    cache_dir = CACHE_AUDIO / dossier_everyayah
    cache_dir.mkdir(parents=True, exist_ok=True)

    numeros: list[int] = list(range(ayah_from, ayah_to + 1))
    if (
        include_basmala
        and ayah_from == 1
        and numero_sourate not in (1, 9)
    ):
        numeros = [0] + numeros

    chemins: list[tuple[int, str]] = []
    total = len(numeros)
    for i, n in enumerate(numeros):
        nom_fichier = f"{numero_sourate:03d}{n:03d}.mp3"
        chemin_local = cache_dir / nom_fichier
        if not chemin_local.is_file() or chemin_local.stat().st_size < 1000:
            url = f"{EVERYAYAH_BASE}/{dossier_everyayah}/{nom_fichier}"
            reponse = session.get(url, headers=HEADERS, timeout=45)
            if reponse.status_code != 200 or len(reponse.content) < 1000:
                continue
            chemin_local.write_bytes(reponse.content)
        chemins.append((n, str(chemin_local)))
        if on_progress:
            pct = 10 + int(40 * (i + 1) / max(total, 1))
            on_progress("downloading", pct, f"Audio {i + 1}/{total}")
    if not chemins:
        raise RuntimeError("Aucun fichier audio récupéré pour cet intervalle.")
    return chemins


def recuperer_textes_arabes(session: requests.Session, numero_sourate: int) -> dict[int, str]:
    url = API_TEXTE_ARABE.format(numero=numero_sourate)
    reponse = session.get(url, headers=HEADERS, timeout=30)
    reponse.raise_for_status()
    data = reponse.json()
    return {a["numberInSurah"]: a["text"] for a in data["data"]["ayahs"]}


def recuperer_traduction(
    session: requests.Session, numero_sourate: int, lang: str
) -> dict[int, str]:
    edition = TRADUCTIONS.get(lang)
    if not edition:
        return {}
    url = API_TRADUCTION.format(numero=numero_sourate, edition=edition)
    reponse = session.get(url, headers=HEADERS, timeout=30)
    reponse.raise_for_status()
    data = reponse.json()
    return {a["numberInSurah"]: a["text"] for a in data["data"]["ayahs"]}


def wrap_latin_text(text: str, width: int = 42, max_lines: int = 3) -> str:
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for i, word in enumerate(words):
        trial = f"{current} {word}".strip() if current else word
        if len(trial) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines - 1:
            rest = " ".join([current] + words[i + 1 :])
            if len(rest) > width * 2:
                rest = rest[: width * 2 - 1] + "..."
            lines.append(rest)
            return "\n".join(lines)
    if current:
        lines.append(current)
    return "\n".join(lines[:max_lines])


def obtenir_duree(chemin_fichier: str) -> float:
    resultat = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            chemin_fichier,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(resultat.stdout)
    return float(data["format"]["duration"])


def secondes_vers_srt_temps(secondes: float) -> str:
    heures = int(secondes // 3600)
    minutes = int((secondes % 3600) // 60)
    sec = int(secondes % 60)
    millis = int(round((secondes - int(secondes)) * 1000))
    return f"{heures:02d}:{minutes:02d}:{sec:02d},{millis:03d}"


def wrap_arabic_text(text: str, width: int = 30, max_lines: int = 4) -> str:
    """Coupe un verset long en lignes lisibles (TikTok vertical)."""
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for i, word in enumerate(words):
        trial = f"{current} {word}".strip() if current else word
        if len(trial) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines - 1:
            rest = " ".join([current] + words[i + 1 :])
            # dernière ligne : coupe douce si encore trop long
            if len(rest) > width * 2:
                rest = rest[: width * 2 - 1] + "…"
            lines.append(rest)
            return "\n".join(lines)
    if current:
        lines.append(current)
    return "\n".join(lines[:max_lines])


def construire_srt_et_audio(
    versets: list[tuple[int, str]],
    textes_arabes: dict[int, str],
    dossier_tmp: Path,
    chemin_srt: Path,
    chemin_audio_final: Path,
    traductions: dict[int, str] | None = None,
    translation_lang: str = "none",
    subtitle_style: str = "classic",
) -> tuple[float, int]:
    chemin_liste = dossier_tmp / "liste_concat.txt"
    with chemin_liste.open("w", encoding="utf-8") as f:
        for _, chemin in versets:
            chemin_abs = os.path.abspath(chemin).replace("\\", "/")
            f.write(f"file '{chemin_abs}'\n")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(chemin_liste),
            "-acodec",
            "pcm_s16le",
            str(chemin_audio_final),
        ],
        check=True,
        capture_output=True,
    )

    entrees_srt: list[str] = []
    t = 0.0
    index_srt = 1
    max_len = 0
    traductions = traductions or {}
    for numero_verset, chemin in versets:
        duree = obtenir_duree(chemin)
        texte = (
            BISMILLAH_ARABE
            if numero_verset == 0
            else textes_arabes.get(numero_verset, "")
        )
        max_len = max(max_len, len(texte))
        width = 28 if len(texte) > 100 else (32 if len(texte) > 60 else 36)
        texte_wrap = wrap_arabic_text(texte, width=width, max_lines=3 if traductions else 4)

        if translation_lang != "none":
            if numero_verset == 0:
                tr = BISMILLAH_FR if translation_lang == "fr" else BISMILLAH_EN
            else:
                tr = traductions.get(numero_verset, "")
            if tr:
                texte_wrap = f"{texte_wrap}\n{wrap_latin_text(tr, width=40, max_lines=2)}"

        texte_wrap = decorate_srt_text(texte_wrap, subtitle_style)

        debut = secondes_vers_srt_temps(t)
        fin = secondes_vers_srt_temps(t + duree)
        entrees_srt.append(f"{index_srt}\n{debut} --> {fin}\n{texte_wrap}\n")
        t += duree
        index_srt += 1

    chemin_srt.write_text("\n".join(entrees_srt), encoding="utf-8")
    return t, max_len


def _filtre_fond(video_style: str) -> str:
    w, h = LARGEUR_SORTIE, HAUTEUR_SORTIE
    base = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"

    if video_style == "blur":
        return f"{base},gblur=sigma=12,eq=brightness=-0.08:saturation=0.85"
    if video_style == "dark":
        return f"{base},eq=brightness=-0.18:saturation=0.7,vignette=PI/4"
    if video_style == "kenburns":
        return (
            f"{base},"
            f"zoompan=z='min(zoom+0.00055,1.18)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps=30"
        )
    if video_style == "cinematic":
        return (
            f"{base},"
            f"eq=contrast=1.08:brightness=-0.06:saturation=0.82,"
            f"vignette=PI/5,"
            f"zoompan=z='min(zoom+0.00035,1.1)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps=30"
        )
    if video_style == "split":
        return (
            f"{base},"
            f"drawbox=x=0:y=ih*0.72:w=iw:h=ih*0.28:color=black@0.45:t=fill"
        )
    return base


def preparer_video_fond(
    chemin_source: str | None,
    duree_cible: float,
    chemin_sortie: Path,
    video_style: str,
    chemins: list[str] | None = None,
) -> None:
    paths = [p for p in (chemins or []) if p and os.path.isfile(p)]
    if not paths and chemin_source and os.path.isfile(chemin_source):
        paths = [chemin_source]

    if len(paths) > 1:
        _preparer_montage_fonds(paths, duree_cible, chemin_sortie, video_style)
        return

    if paths:
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            paths[0],
            "-t",
            str(duree_cible),
            "-vf",
            _filtre_fond(video_style),
            "-an",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            str(chemin_sortie),
        ]
    else:
        color = "0x050A0C" if video_style == "dark" else "0x0B1F1A"
        lavfi = f"color=c={color}:s={LARGEUR_SORTIE}x{HAUTEUR_SORTIE}:d={duree_cible}"
        extra_vf: list[str] = []
        if video_style == "split":
            extra_vf = [
                "-vf",
                "drawbox=x=0:y=ih*0.72:w=iw:h=ih*0.28:color=black@0.45:t=fill",
            ]
        elif video_style == "dark":
            extra_vf = ["-vf", "eq=brightness=-0.1,vignette=PI/4"]
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            lavfi,
            *extra_vf,
            "-an",
            "-r",
            "30",
            str(chemin_sortie),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Preparation fond echouee : {result.stderr[-800:]}")


def _preparer_montage_fonds(
    paths: list[str],
    duree_cible: float,
    chemin_sortie: Path,
    video_style: str,
) -> None:
    """Montage simple: parts egales; xfade si 2 clips, sinon concat."""
    import shutil

    n = len(paths)
    use_xfade = n == 2
    fade = 0.6 if use_xfade else 0.0
    base = duree_cible / n
    seg_dur = base + fade

    work = chemin_sortie.parent / "montage_segs"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    segs: list[Path] = []
    for i, src in enumerate(paths):
        seg = work / f"seg_{i:02d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", src,
            "-t", f"{seg_dur:.3f}",
            "-vf", _filtre_fond(video_style),
            "-an", "-r", "30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(seg),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Segment fond {i} echoue : {result.stderr[-600:]}")
        segs.append(seg)

    if use_xfade:
        offset = max(0.0, seg_dur - fade)
        fc = (
            f"[0:v][1:v]xfade=transition=fade:duration={fade}:offset={offset:.3f},"
            f"trim=duration={duree_cible:.3f},setpts=PTS-STARTPTS[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(segs[0]), "-i", str(segs[1]),
            "-filter_complex", fc,
            "-map", "[v]",
            "-an", "-r", "30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-t", f"{duree_cible:.3f}",
            str(chemin_sortie),
        ]
    else:
        liste = work / "concat.txt"
        lines = []
        for s in segs:
            p = str(s.resolve()).replace("\\", "/")
            # Escape single quotes for concat demuxer
            p = p.replace("'", "'\\''")
            lines.append(f"file '{p}'")
        liste.write_text("\n".join(lines), encoding="utf-8")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(liste),
            "-t", f"{duree_cible:.3f}",
            "-an", "-r", "30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            str(chemin_sortie),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Montage fonds echoue : {result.stderr[-800:]}")


def _escape_subtitles_path(path: Path) -> str:
    """Chemin compatible filtre ffmpeg subtitles (Windows)."""
    p = str(path.resolve()).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def assembler_video_finale(
    chemin_video_fond: Path,
    chemin_audio: Path,
    chemin_srt: Path,
    chemin_sortie: Path,
    subtitle_style: str,
    font_name: str,
    max_text_len: int = 0,
    font_size: int | None = None,
    audio_duration: float | None = None,
    watermark_mode: str = "none",
    watermark_text: str = "",
) -> None:
    srt_escaped = _escape_subtitles_path(chemin_srt)
    style = ass_force_style(
        subtitle_style, font_name, max_text_len=max_text_len, font_size_override=font_size
    )

    fonts_arg = ""
    if FONTS_DIR.is_dir() and any(FONTS_DIR.glob("*.ttf")):
        fonts_dir = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")
        fonts_arg = f":fontsdir='{fonts_dir}'"

    filtre = f"subtitles='{srt_escaped}'{fonts_arg}:force_style='{style}'"
    fade_out_start = max(0.0, (audio_duration or 10.0) - 1.5)
    audio_filter = f"afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start:.2f}:d=1.5"

    logo = ROOT / "assets" / "nur-logo.png"
    mode = (watermark_mode or "none").strip().lower()
    cmd = ["ffmpeg", "-y", "-i", str(chemin_video_fond), "-i", str(chemin_audio)]

    if mode == "text" and watermark_text.strip():
        safe = watermark_text.strip().replace("\\", "\\\\").replace(":", "\\:").replace("'", "")
        if not safe.startswith("@"):
            safe = f"@{safe}"
        vf = (
            f"{filtre},"
            f"drawtext=text='{safe}':fontsize=28:fontcolor=white@0.55:"
            f"x=w-tw-40:y=40:shadowcolor=black@0.4:shadowx=1:shadowy=1"
        )
        cmd += ["-vf", vf, "-af", audio_filter]
    elif mode == "logo" and logo.is_file():
        cmd += ["-i", str(logo)]
        fc = (
            f"[0:v]{filtre}[base];"
            f"[2:v]format=rgba,colorchannelmixer=aa=0.4,scale=72:-1[lg];"
            f"[base][lg]overlay=W-w-36:36[v]"
        )
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "1:a", "-af", audio_filter]
    else:
        cmd += ["-vf", filtre, "-af", audio_filter]

    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p",
        str(chemin_sortie),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Assemblage final echoue : {result.stderr[-1200:]}")


def generer_video(
    cfg: JobConfig,
    job_dir: Path,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """Exécute tout le pipeline. Retourne le chemin du MP4 final."""

    def progress(stage: str, pct: int, message: str) -> None:
        if on_progress:
            on_progress(stage, pct, message)

    valider_config(cfg)
    verifier_ffmpeg()

    reciteur = RECITEURS[cfg.reciter_id]
    job_dir.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    bg_path = cfg.bg_path
    if cfg.background_url and not bg_path:
        progress("bg_download", 3, "Telechargement du fond...")
        print(f"[job] download fond: {cfg.background_url[:80]}...", flush=True)
        from .backgrounds import download_background_url

        def dl_prog(pct: int, msg: str) -> None:
            # map 0-95 -> 3-20
            progress("bg_download", 3 + int(pct * 0.17), msg)

        bg_path = str(download_background_url(cfg.background_url, on_progress=dl_prog))
        try:
            print(f"[job] fond OK: {bg_path}", flush=True)
        except UnicodeEncodeError:
            print("[job] fond OK", flush=True)

    progress("downloading", 8, "Telechargement audio...")
    versets = telecharger_versets_audio(
        session,
        reciteur["dossier"],
        cfg.surah,
        cfg.ayah_from,
        cfg.ayah_to,
        cfg.include_basmala,
        on_progress=on_progress,
    )

    progress("text", 55, "Recuperation du texte arabe...")
    textes = recuperer_textes_arabes(session, cfg.surah)
    traductions: dict[int, str] = {}
    if cfg.translation != "none":
        progress("text", 57, f"Traduction {cfg.translation.upper()}...")
        traductions = recuperer_traduction(session, cfg.surah, cfg.translation)

    progress("audio", 60, "Concatenation audio + sous-titres...")
    chemin_srt = job_dir / "sous_titres.srt"
    chemin_audio = job_dir / "audio_complet.wav"
    duree, max_text_len = construire_srt_et_audio(
        versets,
        textes,
        job_dir,
        chemin_srt,
        chemin_audio,
        traductions=traductions,
        translation_lang=cfg.translation,
        subtitle_style=cfg.subtitle_style,
    )

    progress("background", 70, "Preparation du fond...")
    try:
        print(f"[job] preparer fond style={cfg.video_style} duree={duree:.1f}s", flush=True)
    except UnicodeEncodeError:
        print("[job] preparer fond", flush=True)
    chemin_fond = job_dir / "fond_pret.mp4"
    preparer_video_fond(
        bg_path,
        duree,
        chemin_fond,
        cfg.video_style,
        chemins=cfg.bg_paths,
    )

    progress("encoding", 80, "Assemblage final (1-3 min)...")
    surah_name = SOURATES[cfg.surah - 1][0]
    nom = nettoyer_nom(
        f"{reciteur['nom']}_{surah_name}_{cfg.ayah_from}-{cfg.ayah_to}_"
        f"{cfg.subtitle_style}_{cfg.video_style}.mp4"
    )
    chemin_sortie = OUTPUTS / nom
    assembler_video_finale(
        chemin_fond,
        chemin_audio,
        chemin_srt,
        chemin_sortie,
        cfg.subtitle_style,
        cfg.font_name,
        max_text_len=max_text_len,
        font_size=cfg.font_size,
        audio_duration=duree,
        watermark_mode=cfg.watermark_mode,
        watermark_text=cfg.watermark_text,
    )

    # Sidecar for history / regenerate
    meta = {
        "reciter_id": cfg.reciter_id,
        "surah": cfg.surah,
        "ayah_from": cfg.ayah_from,
        "ayah_to": cfg.ayah_to,
        "subtitle_style": cfg.subtitle_style,
        "video_style": cfg.video_style,
        "include_basmala": cfg.include_basmala,
        "translation": cfg.translation,
        "watermark_mode": cfg.watermark_mode,
        "watermark_text": cfg.watermark_text,
        "output_name": nom,
        "duration_seconds": round(duree, 1),
    }
    (OUTPUTS / f"{chemin_sortie.stem}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Also keep SRT next to output for CapCut users
    try:
        (OUTPUTS / f"{chemin_sortie.stem}.srt").write_text(
            chemin_srt.read_text(encoding="utf-8"), encoding="utf-8"
        )
    except OSError:
        pass

    progress("done", 100, "Video prete")
    return chemin_sortie
