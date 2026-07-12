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
    subtitle_anim: str = "fade"  # none | fade | rise | soft | blur
    long_verse_mode: str = "pages"  # pages | block
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
        raise ValueError("Reciteur invalide.")
    if not (1 <= cfg.surah <= 114):
        raise ValueError("Sourate invalide (1–114).")
    info = RECITEURS[cfg.reciter_id]
    allowed = info.get("surahs")
    if allowed and cfg.surah not in allowed:
        raise ValueError(
            f"Cette sourate n'est pas disponible pour {info['nom']} "
            f"({len(allowed)} sourates en catalogue)."
        )
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
    if cfg.subtitle_anim not in ("none", "fade", "rise", "soft", "blur"):
        raise ValueError("Animation de sous-titres invalide.")
    if cfg.long_verse_mode not in ("pages", "block"):
        raise ValueError("Mode versets longs invalide (pages/block).")
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
    reciter_info: dict | None = None,
) -> list[tuple[int, str]]:
    """Telecharge (ou reutilise le cache) les MP3 de l'intervalle demande."""
    info = reciter_info or {"source": "everyayah", "dossier": dossier_everyayah}
    source = info.get("source", "everyayah")
    dossier = info.get("dossier", dossier_everyayah)
    cache_dir = CACHE_AUDIO / dossier
    cache_dir.mkdir(parents=True, exist_ok=True)

    if source == "surah":
        return _telecharger_depuis_sourate(
            session,
            info,
            numero_sourate,
            ayah_from,
            ayah_to,
            include_basmala,
            cache_dir,
            on_progress=on_progress,
        )

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
            url = f"{EVERYAYAH_BASE}/{dossier}/{nom_fichier}"
            reponse = session.get(url, headers=HEADERS, timeout=45)
            if reponse.status_code != 200 or len(reponse.content) < 1000:
                continue
            chemin_local.write_bytes(reponse.content)
        chemins.append((n, str(chemin_local)))
        if on_progress:
            pct = 10 + int(40 * (i + 1) / max(total, 1))
            on_progress("downloading", pct, f"Audio {i + 1}/{total}")
    if not chemins:
        raise RuntimeError("Aucun fichier audio recupere pour cet intervalle.")
    return chemins


def _telecharger_depuis_sourate(
    session: requests.Session,
    info: dict,
    numero_sourate: int,
    ayah_from: int,
    ayah_to: int,
    include_basmala: bool,
    cache_dir: Path,
    on_progress: ProgressCallback | None = None,
) -> list[tuple[int, str]]:
    """Telecharge une sourate complete puis decoupe les versets (approx.)."""
    template = info.get("surah_url") or ""
    if not template:
        raise RuntimeError("URL sourate manquante pour ce reciteur.")

    surah_path = cache_dir / f"{numero_sourate:03d}_full.mp3"
    if not surah_path.is_file() or surah_path.stat().st_size < 5000:
        if on_progress:
            on_progress("downloading", 12, "Telechargement sourate...")
        url = template.format(surah=numero_sourate)
        reponse = session.get(url, headers=HEADERS, timeout=120)
        if reponse.status_code != 200 or len(reponse.content) < 5000:
            raise RuntimeError(
                f"Sourate {numero_sourate} indisponible pour {info.get('nom', 'ce reciteur')}."
            )
        surah_path.write_bytes(reponse.content)

    if on_progress:
        on_progress("downloading", 30, "Decoupe des versets...")

    textes = recuperer_textes_arabes(session, numero_sourate)
    nb = NB_VERSETS[numero_sourate - 1]
    duree = obtenir_duree(str(surah_path))

    # Basmala approx. en tete (sauf Fatiha / Tawba)
    basmala_dur = 0.0
    want_basmala = (
        include_basmala
        and ayah_from == 1
        and numero_sourate not in (1, 9)
    )
    if want_basmala:
        basmala_dur = min(5.0, max(2.2, duree * 0.045))

    usable = max(0.5, duree - basmala_dur)
    weights = [max(10, len(textes.get(i, ""))) for i in range(1, nb + 1)]
    total_w = float(sum(weights)) or 1.0

    starts: dict[int, float] = {}
    ends: dict[int, float] = {}
    t = basmala_dur
    for i in range(1, nb + 1):
        starts[i] = t
        t += usable * (weights[i - 1] / total_w)
        ends[i] = t
    ends[nb] = duree

    chemins: list[tuple[int, str]] = []
    if want_basmala:
        basmala_file = cache_dir / f"{numero_sourate:03d}000.mp3"
        if not basmala_file.is_file() or basmala_file.stat().st_size < 800:
            _ffmpeg_extract(surah_path, 0.0, basmala_dur, basmala_file)
        chemins.append((0, str(basmala_file)))

    targets = list(range(ayah_from, ayah_to + 1))
    for i, n in enumerate(targets):
        out = cache_dir / f"{numero_sourate:03d}{n:03d}.mp3"
        if not out.is_file() or out.stat().st_size < 800:
            _ffmpeg_extract(surah_path, starts[n], ends[n], out)
        chemins.append((n, str(out)))
        if on_progress:
            pct = 30 + int(25 * (i + 1) / max(len(targets), 1))
            on_progress("downloading", pct, f"Verset {i + 1}/{len(targets)}")

    if not chemins:
        raise RuntimeError("Aucun segment audio produit.")
    return chemins


def _ffmpeg_extract(src: Path, start: float, end: float, out: Path) -> None:
    start = max(0.0, start)
    end = max(start + 0.25, end)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", str(src),
        "-c:a", "libmp3lame", "-q:a", "4",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not out.is_file() or out.stat().st_size < 400:
        raise RuntimeError(f"Decoupe audio echouee ({out.name}).")


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


def wrap_to_lines(text: str, width: int) -> list[str]:
    """Coupe en lignes sans jamais tronquer (pagination ensuite)."""
    text = " ".join((text or "").split())
    if not text:
        return []
    if len(text) <= width:
        return [text]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        # Mot plus large que la largeur : coupe dure
        while len(word) > width:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:width])
            word = word[width:]
        trial = f"{current} {word}".strip() if current else word
        if len(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def wrap_latin_text(text: str, width: int = 30, max_lines: int = 0) -> str:
    lines = wrap_to_lines(text, width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)


def wrap_arabic_text(text: str, width: int = 24, max_lines: int = 0) -> str:
    """Coupe un verset long en lignes lisibles (TikTok vertical)."""
    lines = wrap_to_lines(text, width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)


def _safe_line_widths(text_len: int, has_translation: bool) -> tuple[int, int]:
    """Largeurs caracteres sures pour 1080px avec marges ~100px."""
    # Arabic glyphs are visually wider
    if text_len > 160:
        ar, lat = 20, 26
    elif text_len > 100:
        ar, lat = 22, 28
    elif text_len > 60:
        ar, lat = 24, 30
    else:
        ar, lat = 26, 32
    if has_translation:
        ar = max(18, ar - 2)
        lat = max(24, lat - 2)
    return ar, lat


def _paginate_lines(
    lines: list[str],
    duration: float,
    max_lines_on_screen: int = 5,
) -> list[list[str]]:
    """Decoupe les lignes en pages temporelles (jamais de troncature)."""
    if not lines:
        return [[]]
    n = len(lines)
    if n <= max_lines_on_screen:
        return [lines]

    # Vise ~1.6s minimum par page si la duree le permet
    max_pages = max(1, int(duration / 1.55)) if duration > 0 else 1
    page_size = max(3, (n + max_pages - 1) // max_pages)
    page_size = min(page_size, max_lines_on_screen)

    pages: list[list[str]] = []
    for i in range(0, n, page_size):
        pages.append(lines[i : i + page_size])
    return pages


def _paginate_bilingual(
    ar_lines: list[str],
    tr_lines: list[str],
    duration: float,
    max_lines_on_screen: int = 5,
) -> list[list[str]]:
    """Pages avec arabe en haut + traduction en bas (jamais sequentiel)."""
    if not tr_lines:
        return _paginate_lines(ar_lines, duration, max_lines_on_screen)
    if not ar_lines:
        return _paginate_lines(tr_lines, duration, max_lines_on_screen)

    # 1 ligne reservee au separateur vide entre AR et FR/EN
    budget = max(2, max_lines_on_screen - 1)
    # Repartition visuelle : un peu plus d'arabe si possible
    ar_share = max(1, (budget + 1) // 2)
    tr_share = max(1, budget - ar_share)

    n_pages = max(
        (len(ar_lines) + ar_share - 1) // ar_share,
        (len(tr_lines) + tr_share - 1) // tr_share,
        1,
    )
    # Si la duree est courte, reduire le nombre de pages (lignes plus denses)
    if duration > 0:
        max_by_time = max(1, int(duration / 1.4))
        if n_pages > max_by_time:
            n_pages = max_by_time

    # Recalcule parts egales pour remplir n_pages
    ar_per = max(1, (len(ar_lines) + n_pages - 1) // n_pages)
    tr_per = max(1, (len(tr_lines) + n_pages - 1) // n_pages)
    # Si trop de lignes a l'ecran, ajoute des pages
    while ar_per + tr_per > budget and n_pages < 40:
        n_pages += 1
        ar_per = max(1, (len(ar_lines) + n_pages - 1) // n_pages)
        tr_per = max(1, (len(tr_lines) + n_pages - 1) // n_pages)

    pages: list[list[str]] = []
    for i in range(n_pages):
        ar_chunk = ar_lines[i * ar_per : (i + 1) * ar_per]
        tr_chunk = tr_lines[i * tr_per : (i + 1) * tr_per]
        if not ar_chunk and not tr_chunk:
            continue
        page: list[str] = []
        if ar_chunk:
            page.extend(ar_chunk)
        if ar_chunk and tr_chunk:
            page.append("")
        if tr_chunk:
            page.extend(tr_chunk)
        pages.append(page)

    return pages or [[]]


def construire_srt_et_audio(
    versets: list[tuple[int, str]],
    textes_arabes: dict[int, str],
    dossier_tmp: Path,
    chemin_srt: Path,
    chemin_audio_final: Path,
    traductions: dict[int, str] | None = None,
    translation_lang: str = "none",
    subtitle_style: str = "classic",
    subtitle_anim: str = "fade",
    long_verse_mode: str = "pages",
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
    has_tr = translation_lang != "none"

    for numero_verset, chemin in versets:
        duree = obtenir_duree(chemin)
        texte = (
            BISMILLAH_ARABE
            if numero_verset == 0
            else textes_arabes.get(numero_verset, "")
        )
        max_len = max(max_len, len(texte))
        ar_w, lat_w = _safe_line_widths(len(texte), has_tr)
        ar_lines = wrap_to_lines(texte, ar_w)

        tr_lines: list[str] = []
        if has_tr:
            if numero_verset == 0:
                tr = BISMILLAH_FR if translation_lang == "fr" else BISMILLAH_EN
            else:
                tr = traductions.get(numero_verset, "")
            if tr:
                max_len = max(max_len, len(tr))
                tr_lines = wrap_to_lines(tr, lat_w)

        # Pages bilingues (AR haut / TR bas) OU un seul bloc complet
        mode = (long_verse_mode or "pages").strip().lower()
        if mode == "block":
            page: list[str] = list(ar_lines)
            if tr_lines:
                if page:
                    page.append("")
                page.extend(tr_lines)
            pages = [page] if page else [[]]
        elif tr_lines:
            pages = _paginate_bilingual(
                ar_lines,
                tr_lines,
                duree,
                max_lines_on_screen=5,
            )
        else:
            pages = _paginate_lines(ar_lines, duree, max_lines_on_screen=6)
        page_dur = duree / len(pages) if pages else duree

        for page in pages:
            # Evite une page qui n'est qu'une ligne vide
            body = "\n".join(page).strip("\n")
            if not body.strip():
                t += page_dur
                continue
            texte_wrap = decorate_srt_text(body, subtitle_style, anim=subtitle_anim)
            debut = secondes_vers_srt_temps(t)
            fin = secondes_vers_srt_temps(t + page_dur)
            entrees_srt.append(f"{index_srt}\n{debut} --> {fin}\n{texte_wrap}\n")
            t += page_dur
            index_srt += 1

    chemin_srt.write_text("\n".join(entrees_srt), encoding="utf-8")
    return t, max_len


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
    has_translation: bool = False,
) -> None:
    srt_escaped = _escape_subtitles_path(chemin_srt)
    style = ass_force_style(
        subtitle_style,
        font_name,
        max_text_len=max_text_len,
        font_size_override=font_size,
        has_translation=has_translation,
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
        reciter_info=reciteur,
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
        subtitle_anim=cfg.subtitle_anim,
        long_verse_mode=cfg.long_verse_mode,
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
        has_translation=cfg.translation != "none",
    )

    # Sidecar for history / regenerate
    meta = {
        "reciter_id": cfg.reciter_id,
        "surah": cfg.surah,
        "ayah_from": cfg.ayah_from,
        "ayah_to": cfg.ayah_to,
        "subtitle_style": cfg.subtitle_style,
        "subtitle_anim": cfg.subtitle_anim,
        "long_verse_mode": cfg.long_verse_mode,
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
