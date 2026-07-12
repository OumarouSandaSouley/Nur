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
        "tag": r"{\move(540,1780,540,1680,0,520)\fad(280,420)}",
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
        "font_size": 22,
        "primary": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "outline": 2,
        "alignment": 2,
        "margin_v": 120,
        "border_style": 1,
        "shadow": 0,
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
        "font_size": 26,
        "primary": "&H00E8F0F5",
        "outline_colour": "&H001A1F0D",
        "outline": 2,
        "alignment": 5,
        "margin_v": 0,
        "border_style": 1,
        "shadow": 0,
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


def font_size_for_length(base: int, max_chars: int, has_translation: bool = False) -> int:
    """Taille adaptive pour rester dans le cadre vertical 1080px."""
    size = base
    if has_translation:
        size = min(size, base - 2)
    if max_chars > 220:
        size = min(size, 15)
    elif max_chars > 150:
        size = min(size, 16)
    elif max_chars > 100:
        size = min(size, 18)
    elif max_chars > 60:
        size = min(size, 20)
    elif max_chars > 40:
        size = min(size, max(18, base - 2))
    return max(13, size)


def ass_force_style(
    style_id: str,
    font_name: str = "Traditional Arabic",
    max_text_len: int = 0,
    font_size_override: int | None = None,
    has_translation: bool = False,
) -> str:
    style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
    base = int(font_size_override or style["font_size"])
    size = font_size_for_length(base, max_text_len, has_translation=has_translation)
    alignment = style["alignment"]
    margin_v = style["margin_v"]
    # Long text: always bottom, more vertical room
    if max_text_len > 50 and alignment == 5:
        alignment = 2
    if max_text_len > 80 or has_translation:
        margin_v = max(margin_v, 160)
    if max_text_len > 140:
        margin_v = max(margin_v, 180)
    parts = [
        f"FontName={font_name}",
        f"FontSize={size}",
        f"PrimaryColour={style['primary']}",
        f"OutlineColour={style['outline_colour']}",
        f"BorderStyle={style['border_style']}",
        f"Outline={style['outline']}",
        f"Shadow={style.get('shadow', 0)}",
        f"Alignment={alignment}",
        f"MarginV={margin_v}",
        "MarginL=100",
        "MarginR=100",
        "WrapStyle=2",
    ]
    if style.get("back_colour"):
        parts.append(f"BackColour={style['back_colour']}")
    return ",".join(parts)


def decorate_srt_text(text: str, style_id: str, anim: str = "none") -> str:
    """Ajoute tags ASS d'animation (ou fade legacy du style)."""
    anim_key = (anim or "none").strip().lower()
    tag = SUBTITLE_ANIMS.get(anim_key, SUBTITLE_ANIMS["none"])["tag"]
    if not tag:
        style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
        if style.get("fade"):
            tag = SUBTITLE_ANIMS["fade"]["tag"]
    return f"{tag}{text}" if tag else text


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
