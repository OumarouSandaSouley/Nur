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
from .styles import (
    SUBTITLE_STYLES,
    VIDEO_STYLES,
    ass_force_style,
    decorate_srt_text,
    font_size_for_length,
    ui_font_to_ass,
    _center_alignment,
)

ProgressCallback = Callable[[str, int, str], None]

ROOT = Path(__file__).resolve().parents[2]
CACHE_AUDIO = ROOT / "cache" / "audio"
OUTPUTS = ROOT / "outputs"
ASSETS_FONDS = ROOT / "assets" / "fonds"
FONTS_DIR = ROOT / "assets" / "fonts"


def _windows_fonts_dir() -> Path | None:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    return windir if windir.is_dir() else None


def resolve_arabic_font_name() -> str:
    """Police presente sur la machine (Traditional Arabic souvent absent sous Windows)."""
    fonts = _windows_fonts_dir()
    if fonts:
        candidates = [
            ("Segoe UI", "segoeui.ttf"),
            ("Nirmala UI", "NIRMALA.TTF"),
            ("Nirmala UI", "nirmala.ttf"),
            ("Traditional Arabic", "trado.ttf"),
            ("Traditional Arabic", "tradbdo.ttf"),
            ("Arial", "arial.ttf"),
        ]
        for family, filename in candidates:
            if (fonts / filename).is_file():
                return family
    return "Arial"


def _fontsdir_arg() -> str:
    """Expose les polices systeme a libass (requis pour \\fnArial et Segoe UI)."""
    dirs: list[Path] = []
    if FONTS_DIR.is_dir() and any(FONTS_DIR.glob("*.ttf")):
        dirs.append(FONTS_DIR)
    win = _windows_fonts_dir()
    if win:
        dirs.append(win)
    if not dirs:
        return ""
    # Un seul fontsdir : priorite au dossier systeme (Arial + Segoe)
    chosen = dirs[-1] if win else dirs[0]
    escaped = str(chosen.resolve()).replace("\\", "/").replace(":", "\\:")
    return f":fontsdir='{escaped}'"


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
    font_name: str = ""  # resolu au runtime si vide
    translation: str = "none"  # none | fr | en
    font_size: int | None = None
    subtitle_anim: str = "fade"  # none | fade | rise | soft | blur
    long_verse_mode: str = "pages"  # pages | block
    show_credits: bool = False  # sourate+versets / recitateur en bas
    watermark_mode: str = "logo"  # toujours logo Nur
    watermark_text: str = ""
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


# Mots outils : ne pas laisser seuls en fin de ligne (FR/EN)
_LATIN_GLUE = frozenset(
    {
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "du",
        "de",
        "d'",
        "l'",
        "et",
        "ou",
        "à",
        "au",
        "aux",
        "en",
        "ce",
        "ces",
        "se",
        "sa",
        "son",
        "the",
        "a",
        "an",
        "of",
        "and",
        "or",
        "to",
        "in",
        "on",
        "for",
    }
)

# Cue FR separee : Arial suffit, pas de marques BiDi (elles decalaient le texte a gauche)
_LATIN_FONT_TAG = r"{\fnArial}"


def wrap_to_lines(text: str, width: int, *, glue_short: bool = False) -> list[str]:
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
                parts = current.split(" ")
                # Evite "… et la" / "… the" seuls en fin de ligne
                if (
                    glue_short
                    and len(parts) > 1
                    and parts[-1].lower().rstrip(",;:.") in _LATIN_GLUE
                ):
                    stem = " ".join(parts[:-1])
                    lines.append(stem)
                    current = f"{parts[-1]} {word}"
                    if len(current) > width:
                        lines.append(parts[-1])
                        current = word
                else:
                    lines.append(current)
                    current = word
            else:
                current = word
    if current:
        lines.append(current)
    return lines


def wrap_latin_text(text: str, width: int = 30, max_lines: int = 0) -> str:
    lines = wrap_to_lines(text, width, glue_short=True)
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
    """Largeurs pour FontSize ASS ~60-70 sur 1080 (sinon debordement)."""
    if text_len > 160:
        ar, lat = 14, 18
    elif text_len > 100:
        ar, lat = 16, 20
    elif text_len > 60:
        ar, lat = 17, 22
    else:
        ar, lat = 18, 24
    if has_translation:
        ar = max(12, ar - 1)
        lat = max(18, lat - 1)
    return ar, lat


def _style_latin_line(line: str, fs: int | None = None) -> str:
    """Police Arial pour la traduction (cue dediee)."""
    if not line:
        return line
    if line.startswith("{") and "\\fn" in line[:24]:
        return line
    fs_tag = f"\\fs{fs}" if fs else ""
    return f"{{\\fnArial{fs_tag}}}{line}"


def _mark_translation_lines(page: list[str], fs: int | None = None) -> list[str]:
    """Apres le separateur vide, les lignes sont de la traduction."""
    if not page:
        return page
    try:
        sep = page.index("")
    except ValueError:
        return [_style_latin_line(ln, fs) if ln else ln for ln in page]
    out = list(page[: sep + 1])
    out.extend(_style_latin_line(ln, fs) if ln else ln for ln in page[sep + 1 :])
    return out


def _split_ar_tr_page(page: list[str]) -> tuple[list[str], list[str]]:
    """Separe arabe / traduction d'une page (separateur ligne vide)."""
    try:
        sep = page.index("")
    except ValueError:
        ar, tr = [], []
        for ln in page:
            if "\\fnArial" in ln:
                tr.append(ln)
            else:
                ar.append(ln)
        return ar, tr
    return list(page[:sep]), [ln for ln in page[sep + 1 :] if ln]


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
    ar_per_page: int | None = None,
    tr_per_page: int | None = None,
) -> list[list[str]]:
    """Pages avec arabe en haut + traduction en bas (jamais sequentiel)."""
    if not tr_lines:
        return _paginate_lines(ar_lines, duration, max_lines_on_screen)
    if not ar_lines:
        return _paginate_lines(tr_lines, duration, max_lines_on_screen)

    # 1 ligne reservee au separateur vide entre AR et FR/EN
    budget = max(2, max_lines_on_screen - 1)
    if ar_per_page is None:
        ar_per_page = max(1, (budget + 1) // 2)
    if tr_per_page is None:
        tr_per_page = max(1, budget - ar_per_page)
    # Ne jamais depasser le budget ecran
    while ar_per_page + tr_per_page > budget and ar_per_page > 1:
        ar_per_page -= 1
    while ar_per_page + tr_per_page > budget and tr_per_page > 1:
        tr_per_page -= 1

    n_pages = max(
        (len(ar_lines) + ar_per_page - 1) // ar_per_page,
        (len(tr_lines) + tr_per_page - 1) // tr_per_page,
        1,
    )
    # Evite des pages trop courtes (<0.85s), sans re-densifier trop
    if duration > 0:
        max_by_time = max(1, int(duration / 0.85))
        if n_pages > max_by_time:
            n_pages = max_by_time
            ar_per_page = max(1, (len(ar_lines) + n_pages - 1) // n_pages)
            tr_per_page = max(1, (len(tr_lines) + n_pages - 1) // n_pages)
            while ar_per_page + tr_per_page > budget and n_pages < 60:
                n_pages += 1
                ar_per_page = max(1, (len(ar_lines) + n_pages - 1) // n_pages)
                tr_per_page = max(1, (len(tr_lines) + n_pages - 1) // n_pages)

    pages: list[list[str]] = []
    for i in range(n_pages):
        ar_chunk = ar_lines[i * ar_per_page : (i + 1) * ar_per_page]
        tr_chunk = tr_lines[i * tr_per_page : (i + 1) * tr_per_page]
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
) -> tuple[float, int, int]:
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
    max_lines = 0
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
        mode = (long_verse_mode or "pages").strip().lower()
        # D'un coup: lignes plus larges = moins de hauteur. Petits blocs: plus etroites.
        if mode == "block":
            ar_w, lat_w = _safe_line_widths(max(40, len(texte) // 2), has_tr)
            ar_w = min(34, ar_w + 8)
            lat_w = min(42, lat_w + 10)
        else:
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
                tr_lines = wrap_to_lines(tr, lat_w, glue_short=True)

        # Deux modes :
        # - pages  = petits blocs (AR + TR)
        # - block  = tout le verset d'un coup
        if mode == "block":
            if tr_lines:
                fr_styled = [_style_latin_line(ln) for ln in tr_lines]
                page = list(ar_lines) + [""] + fr_styled
            else:
                page = list(ar_lines)
            pages = [page] if page else [[]]
        elif tr_lines:
            pages = _paginate_bilingual(
                ar_lines,
                tr_lines,
                duree,
                max_lines_on_screen=4,
                ar_per_page=2,
                tr_per_page=2,
            )
            pages = [_mark_translation_lines(p) for p in pages]
        else:
            pages = _paginate_lines(ar_lines, duree, max_lines_on_screen=3)
        page_dur = duree / len(pages) if pages else duree

        for page in pages:
            if not any(ln.strip() for ln in page):
                t += page_dur
                continue
            anim = subtitle_anim
            nlines = sum(1 for ln in page if ln.strip())
            if nlines >= 3 and anim in ("rise", "soft"):
                anim = "fade"
            if anim == "rise" and (subtitle_style == "center" or mode == "block"):
                anim = "fade"

            debut = secondes_vers_srt_temps(t)
            fin = secondes_vers_srt_temps(t + page_dur)
            ar_part, tr_part = _split_ar_tr_page(page)

            # Deux cues superposes : arabe (centre) + FR (bas centre)
            if ar_part and tr_part:
                ar_body = "\n".join(ar_part).strip()
                # Une seule balise Arial pour tout le bloc FR (evite artefacts)
                plain_fr = [
                    re.sub(r"^\{\\fnArial(?:\\fs\d+)?\}", "", ln) for ln in tr_part
                ]
                tr_body = r"{\fnArial}" + "\n".join(plain_fr)
                texte_ar = decorate_srt_text(
                    ar_body, subtitle_style, anim=anim, align_an=5
                )
                tr_fade = r"\fad(420,520)" if anim != "none" else ""
                texte_tr = "{\\an2\\pos(540,1520)" + tr_fade + "}" + tr_body
                entrees_srt.append(f"{index_srt}\n{debut} --> {fin}\n{texte_ar}\n")
                index_srt += 1
                entrees_srt.append(f"{index_srt}\n{debut} --> {fin}\n{texte_tr}\n")
                index_srt += 1
                max_lines = max(max_lines, len(ar_part), len(tr_part))
                max_len = max(max_len, len(ar_body), len(tr_body))
            else:
                body = "\n".join(ln for ln in page if ln is not None).strip("\n")
                if not body.strip():
                    t += page_dur
                    continue
                align_an = 5 if (mode == "block" or subtitle_style == "center") else 2
                if nlines > 6:
                    align_an = 2
                texte_wrap = decorate_srt_text(
                    body, subtitle_style, anim=anim, align_an=align_an
                )
                entrees_srt.append(f"{index_srt}\n{debut} --> {fin}\n{texte_wrap}\n")
                index_srt += 1
                max_len = max(max_len, len(body))
                max_lines = max(max_lines, body.count("\n") + 1)

            t += page_dur

    chemin_srt.write_text("\n".join(entrees_srt), encoding="utf-8")
    return t, max_len, max_lines


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
    if millis >= 1000:
        millis = 999
    return f"{heures:02d}:{minutes:02d}:{sec:02d},{millis:03d}"


def secondes_vers_ass_temps(secondes: float) -> str:
    heures = int(secondes // 3600)
    minutes = int((secondes % 3600) // 60)
    sec = int(secondes % 60)
    cs = int(round((secondes - int(secondes)) * 100))
    if cs >= 100:
        cs = 99
    return f"{heures}:{minutes:02d}:{sec:02d}.{cs:02d}"


def _parse_srt_events(chemin_srt: Path) -> list[tuple[float, float, str]]:
    """Parse SRT (texte pouvant contenir des tags ASS) → (debut, fin, texte)."""
    raw = chemin_srt.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    events: list[tuple[float, float, str]] = []
    blocks = re.split(r"\n\s*\n", raw)
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        # saute l'index numerique si present
        idx = 0
        if lines[0].strip().isdigit():
            idx = 1
        if idx >= len(lines) or "-->" not in lines[idx]:
            continue
        timing = lines[idx]
        left, _, right = timing.partition("-->")
        text = "\n".join(lines[idx + 1 :]).strip()
        if not text:
            continue

        def _to_sec(ts: str) -> float:
            ts = ts.strip().replace(",", ".")
            parts = ts.split(":")
            if len(parts) != 3:
                return 0.0
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])

        events.append((_to_sec(left), _to_sec(right), text))
    return events


def ecrire_ass(
    chemin_ass: Path,
    events: list[tuple[float, float, str]],
    *,
    font_name: str,
    font_size: int,
    primary: str,
    outline_colour: str,
    outline: int,
    shadow: int,
    alignment: int,
    margin_v: int,
    border_style: int = 1,
    back_colour: str | None = None,
) -> None:
    """ASS natif PlayRes 1080x1920 — indispensable pour une taille correcte."""
    back = back_colour or "&H00000000"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {LARGEUR_SORTIE}
PlayResY: {HAUTEUR_SORTIE}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary},&H000000FF,{outline_colour},{back},0,0,0,0,100,100,0,0,{border_style},{outline},{shadow},{alignment},80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in events:
        # ASS utilise \N pour les sauts de ligne
        body = text.replace("\n", r"\N")
        lines.append(
            f"Dialogue: 0,{secondes_vers_ass_temps(start)},{secondes_vers_ass_temps(end)},"
            f"Default,,0,0,0,,{body}"
        )
    chemin_ass.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


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


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "")
        .replace("%", "%%")
    )


def _drawtext_font_opt() -> str:
    """Police systeme pour drawtext (obligatoire sous Windows sinon texte fantome)."""
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        windir / "Fonts" / "arial.ttf",
        windir / "Fonts" / "segoeui.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for font in candidates:
        if font.is_file():
            escaped = str(font.resolve()).replace("\\", "/").replace(":", "\\:")
            return f":fontfile='{escaped}'"
    return ""


def _append_credits_to_srt(
    chemin_srt: Path,
    duration: float,
    line1: str,
    line2: str = "",
    font_size: int = 48,
) -> None:
    """Ajoute une cue credits en bas (sera convertie en ASS ensuite)."""
    if not line1 or duration <= 0:
        return
    raw = chemin_srt.read_text(encoding="utf-8")
    next_idx = 1
    for line in raw.splitlines():
        if line.strip().isdigit():
            next_idx = max(next_idx, int(line.strip()) + 1)
    fs1 = max(28, int(font_size * 0.72))
    fs2 = max(24, int(font_size * 0.58))
    bord = max(3, fs1 // 14)
    body = (
        f"{{\\an2\\pos(540,1760)\\fnArial\\fs{fs1}\\bord{bord}\\shad2"
        r"\1c&H00FFFFFF&\3c&H00000000&}"
        f"{line1}"
    )
    if line2:
        body += f"\\N{{\\fs{fs2}}}{line2}"
    debut = secondes_vers_srt_temps(0)
    fin = secondes_vers_srt_temps(duration)
    block = f"{next_idx}\n{debut} --> {fin}\n{body}\n"
    chemin_srt.write_text(raw.rstrip() + "\n\n" + block, encoding="utf-8")


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
    has_translation: bool = False,
    line_count: int = 0,
    show_credits: bool = False,
    credit_line1: str = "",
    credit_line2: str = "",
) -> None:
    if not font_name:
        font_name = resolve_arabic_font_name()

    reserve = 300 if show_credits and credit_line1 else (200 if has_translation else 0)
    style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["classic"])

    # Slider UI → taille ASS reelle (22 UI ≈ 53 ASS sur 1080x1920)
    base = ui_font_to_ass(font_size, style_default=int(style["font_size"]))
    size = font_size_for_length(
        base, max_text_len, has_translation=has_translation, line_count=line_count
    )
    alignment = _center_alignment(int(style["alignment"]))
    margin_v = int(style["margin_v"])
    if has_translation:
        margin_v = max(margin_v, 200)
    if size >= 60 and alignment == 5:
        alignment = 2
        margin_v = max(margin_v, 220)
    if line_count > 8:
        alignment = 2
        margin_v = max(margin_v, 220)
    if reserve:
        margin_v = max(margin_v, reserve)
    outline = max(2, min(5, size // 18))
    shadow = max(1, int(style.get("shadow", 0)) or 1)

    if show_credits and credit_line1 and audio_duration:
        _append_credits_to_srt(
            chemin_srt,
            float(audio_duration),
            credit_line1,
            credit_line2 or "",
            font_size=size,
        )

    events = _parse_srt_events(chemin_srt)
    fr_y = 1650 if show_credits else 1700
    fr_fs = max(28, int(size * 0.88))
    fixed_events: list[tuple[float, float, str]] = []
    for start, end, text in events:
        if r"\pos(540,1520)" in text:
            text = text.replace(r"\pos(540,1520)", rf"\pos(540,{fr_y})")
        if r"{\fnArial}" in text:
            text = text.replace(r"{\fnArial}", rf"{{\fnArial\fs{fr_fs}}}", 1)
        fixed_events.append((start, end, text))

    chemin_ass = chemin_srt.with_suffix(".ass")
    ecrire_ass(
        chemin_ass,
        fixed_events,
        font_name=font_name,
        font_size=size,
        primary=style["primary"],
        outline_colour=style["outline_colour"],
        outline=outline,
        shadow=shadow,
        alignment=alignment,
        margin_v=margin_v,
        border_style=int(style["border_style"]),
        back_colour=style.get("back_colour"),
    )

    ass_escaped = _escape_subtitles_path(chemin_ass)
    fonts_arg = _fontsdir_arg()
    filtre = f"ass='{ass_escaped}'{fonts_arg}"

    fade_out_start = max(0.0, (audio_duration or 10.0) - 1.5)
    audio_filter = f"afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start:.2f}:d=1.5"

    logo = ROOT / "assets" / "nur-logo.png"
    cmd = ["ffmpeg", "-y", "-i", str(chemin_video_fond), "-i", str(chemin_audio)]

    if logo.is_file():
        cmd += ["-i", str(logo)]
        fc = (
            f"[0:v]{filtre}[base];"
            f"[2:v]format=rgba,colorchannelmixer=aa=0.45,scale=72:-1[lg];"
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
    duree, max_text_len, max_lines = construire_srt_et_audio(
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
    if cfg.ayah_from == cfg.ayah_to:
        credit_l1 = f"{surah_name} - {cfg.ayah_from}"
    else:
        credit_l1 = f"{surah_name} - {cfg.ayah_from}-{cfg.ayah_to}"
    credit_l2 = reciteur["nom"]
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
        has_translation=cfg.translation != "none",
        line_count=max_lines,
        show_credits=cfg.show_credits,
        credit_line1=credit_l1,
        credit_line2=credit_l2,
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
        "show_credits": cfg.show_credits,
        "watermark_mode": "logo",
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
