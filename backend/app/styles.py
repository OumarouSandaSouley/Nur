"""Presets de sous-titres (ASS) et de rendu video."""

from __future__ import annotations

# Animations ASS (1080x1920, alignement bas centre approx.)
SUBTITLE_ANIMS: dict[str, dict] = {
    "none": {
        "id": "none",
        "name": "Statique",
        "description": "Sans animation",
        "tag": "",
    },
    "fade": {
        "id": "fade",
        "name": "Fondu",
        "description": "Apparition / disparition douce",
        "tag": r"{\fad(420,520)}",
    },
    "rise": {
        "id": "rise",
        "name": "Montee",
        "description": "Glisse legerement vers le haut",
        # Pas de \move en Y absolu : casse Meditation/centre et pousse le texte hors cadre
        # (libass reclasse alors le bloc en haut). Effet doux compatible tous alignements.
        "tag": r"{\fad(300,420)\fscy108\t(0,480,\fscy100)}",
    },
    "soft": {
        "id": "soft",
        "name": "Pop doux",
        "description": "Leger zoom a l'apparition",
        "tag": r"{\fad(280,420)\fscx92\fscy92\t(0,420,\fscx100\fscy100)}",
    },
    "blur": {
        "id": "blur",
        "name": "Reveal",
        "description": "Apparait en fondu alpha",
        "tag": r"{\alpha&HFF&\t(0,480,\alpha&H00&)\fad(0,450)}",
    },
}

SUBTITLE_STYLES: dict[str, dict] = {
    "classic": {
        "id": "classic",
        "name": "Classique",
        "description": "Blanc, contour noir, bas",
        "preview": {"color": "#FFFFFF", "outline": "#000000", "align": "bottom"},
        "font_size": 26,
        "primary": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "outline": 3,
        "alignment": 2,
        "margin_v": 140,
        "border_style": 1,
        "shadow": 1,
        "fade": False,
    },
    "gold": {
        "id": "gold",
        "name": "Or",
        "description": "Dore elegant, contour sombre",
        "preview": {"color": "#E8C547", "outline": "#1A1208", "align": "bottom"},
        "font_size": 24,
        "primary": "&H0047C5E8",
        "outline_colour": "&H0008121A",
        "outline": 2,
        "alignment": 2,
        "margin_v": 120,
        "border_style": 1,
        "shadow": 0,
        "fade": False,
    },
    "center": {
        "id": "center",
        "name": "Meditation",
        "description": "Blanc centre au milieu",
        "preview": {"color": "#F5F0E8", "outline": "#0D1F1A", "align": "center"},
        "font_size": 28,
        "primary": "&H00E8F0F5",
        "outline_colour": "&H001A1F0D",
        "outline": 3,
        "alignment": 5,
        "margin_v": 0,
        "border_style": 1,
        "shadow": 1,
        "fade": False,
    },
    "soft": {
        "id": "soft",
        "name": "Doux",
        "description": "Blanc creme, contour fin",
        "preview": {"color": "#F2EDE4", "outline": "#2A3530", "align": "bottom"},
        "font_size": 20,
        "primary": "&H00E4EDF2",
        "outline_colour": "&H0030352A",
        "outline": 1,
        "alignment": 2,
        "margin_v": 140,
        "border_style": 1,
        "shadow": 0,
        "fade": False,
    },
    "large": {
        "id": "large",
        "name": "Grand",
        "description": "Texte large pour Reels",
        "preview": {"color": "#FFFFFF", "outline": "#000000", "align": "bottom"},
        "font_size": 32,
        "primary": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "outline": 3,
        "alignment": 2,
        "margin_v": 100,
        "border_style": 1,
        "shadow": 0,
        "fade": False,
    },
    "shadow": {
        "id": "shadow",
        "name": "Ombre",
        "description": "Blanc avec ombre portee",
        "preview": {"color": "#FFFFFF", "outline": "#000000", "align": "bottom"},
        "font_size": 24,
        "primary": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "outline": 1,
        "alignment": 2,
        "margin_v": 120,
        "border_style": 1,
        "shadow": 3,
        "fade": False,
    },
    "banner": {
        "id": "banner",
        "name": "Bandeau",
        "description": "Boite sombre derriere le texte",
        "preview": {"color": "#FFFFFF", "outline": "#0A1612", "align": "bottom"},
        "font_size": 22,
        "primary": "&H00FFFFFF",
        "outline_colour": "&H001A1208",
        "outline": 0,
        "alignment": 2,
        "margin_v": 110,
        "border_style": 3,  # opaque box
        "shadow": 0,
        "fade": False,
        "back_colour": "&H990A1612",
    },
    "fade": {
        "id": "fade",
        "name": "Fade",
        "description": "Apparition / disparition animee",
        "preview": {"color": "#F5F0E8", "outline": "#0D1F1A", "align": "bottom"},
        "font_size": 24,
        "primary": "&H00E8F0F5",
        "outline_colour": "&H001A1F0D",
        "outline": 2,
        "alignment": 2,
        "margin_v": 120,
        "border_style": 1,
        "shadow": 1,
        "fade": True,
    },
}

VIDEO_STYLES: dict[str, dict] = {
    "clean": {
        "id": "clean",
        "name": "Epure",
        "description": "Recadrage vertical net",
    },
    "blur": {
        "id": "blur",
        "name": "Flou cine",
        "description": "Fond flou + assombrissement leger",
    },
    "dark": {
        "id": "dark",
        "name": "Nuit",
        "description": "Vignette et tons sombres",
    },
    "kenburns": {
        "id": "kenburns",
        "name": "Zoom lent",
        "description": "Leger zoom progressif (Ken Burns)",
    },
    "split": {
        "id": "split",
        "name": "Bande basse",
        "description": "Bande semi-opaque pour les sous-titres",
    },
    "cinematic": {
        "id": "cinematic",
        "name": "Cinema",
        "description": "Contraste doux + vignette + zoom",
    },
}


def font_size_for_length(
    base: int,
    max_chars: int,
    has_translation: bool = False,
    line_count: int = 0,
) -> int:
    """Ajuste legerement la taille ASS ; plancher confort Reels."""
    size = base
    if has_translation:
        size = max(int(base * 0.92), base - 4)
    if line_count > 14:
        size = min(size, max(42, int(base * 0.72)))
    elif line_count > 10:
        size = min(size, max(48, int(base * 0.82)))
    elif line_count > 7:
        size = min(size, max(52, int(base * 0.90)))
    if max_chars > 260:
        size = min(size, max(42, size - 10))
    elif max_chars > 180:
        size = min(size, max(48, size - 6))
    return max(36, size)


def ui_font_to_ass(ui_size: int | None, style_default: int = 26) -> int:
    """Slider UI 14-36 → FontSize ASS lisible en vertical 1080x1920.

    Avec PlayRes correct, 1 point ASS ≈ 1 px : le slider UI doit etre
    amplifie pour du Reels (ex. 14→42, 22→66, 28→84, 36→100).
    """
    raw = int(ui_size) if ui_size and ui_size > 0 else int(style_default)
    raw = max(12, min(48, raw))
    return max(36, min(100, int(round(raw * 3.0))))


def _center_alignment(alignment: int) -> int:
    """Force la colonne centrale ASS (2 bas / 5 milieu / 8 haut)."""
    if alignment in (7, 8, 9):
        return 8
    if alignment in (4, 5, 6):
        return 5
    return 2


def ass_force_style(
    style_id: str,
    font_name: str = "Segoe UI",
    max_text_len: int = 0,
    font_size_override: int | None = None,
    has_translation: bool = False,
    line_count: int = 0,
    reserve_bottom: int = 0,
) -> str:
    style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
    base = int(font_size_override or style["font_size"])
    size = font_size_for_length(
        base, max_text_len, has_translation=has_translation, line_count=line_count
    )
    alignment = _center_alignment(int(style["alignment"]))
    margin_v = int(style["margin_v"])
    if has_translation:
        margin_v = max(margin_v, 160)
    if base >= 30:
        margin_v = max(margin_v, 170)
        if alignment == 5:
            alignment = 2
            margin_v = max(margin_v, 190)
    if line_count > 8:
        alignment = 2
        margin_v = max(margin_v, 180)
    if reserve_bottom:
        margin_v = max(margin_v, reserve_bottom)
    # Contour plus marque pour fonds clairs (flou cine / coucher de soleil)
    outline = max(int(style["outline"]), 2 if size >= 20 else 1)
    parts = [
        f"FontName={font_name}",
        f"FontSize={size}",
        f"PrimaryColour={style['primary']}",
        f"OutlineColour={style['outline_colour']}",
        f"BorderStyle={style['border_style']}",
        f"Outline={outline}",
        f"Shadow={max(int(style.get('shadow', 0)), 1)}",
        f"Alignment={alignment}",
        f"MarginV={margin_v}",
        "MarginL=80",
        "MarginR=80",
        "WrapStyle=2",
    ]
    if style.get("back_colour"):
        parts.append(f"BackColour={style['back_colour']}")
    return ",".join(parts)


def decorate_srt_text(
    text: str,
    style_id: str,
    anim: str = "none",
    align_an: int = 2,
) -> str:
    """Ajoute tags ASS (centrage + animation)."""
    an = align_an if align_an in (2, 5, 8) else 2
    anim_key = (anim or "none").strip().lower()
    tag = SUBTITLE_ANIMS.get(anim_key, SUBTITLE_ANIMS["none"])["tag"]
    if not tag:
        style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
        if style.get("fade"):
            tag = SUBTITLE_ANIMS["fade"]["tag"]
    # Fusionne \anX dans le bloc d'override existant
    if tag.startswith("{") and tag.endswith("}"):
        inner = tag[1:-1]
        if "\\an" not in inner:
            tag = "{\\an" + str(an) + inner + "}"
    else:
        tag = "{\\an" + str(an) + "}"
    return f"{tag}{text}"


def liste_styles_sous_titres():
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "preview": s["preview"],
        }
        for s in SUBTITLE_STYLES.values()
    ]


def liste_anims_sous_titres():
    return [
        {"id": a["id"], "name": a["name"], "description": a["description"]}
        for a in SUBTITLE_ANIMS.values()
    ]


def liste_styles_video():
    return [
        {"id": s["id"], "name": s["name"], "description": s["description"]}
        for s in VIDEO_STYLES.values()
    ]
