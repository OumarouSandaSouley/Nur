"""Presets de sous-titres (ASS) et de rendu video."""

from __future__ import annotations

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


def font_size_for_length(base: int, max_chars: int) -> int:
    if max_chars > 200:
        return max(14, base - 12)
    if max_chars > 140:
        return max(15, base - 10)
    if max_chars > 90:
        return max(16, base - 6)
    if max_chars > 55:
        return max(18, base - 3)
    return base


def ass_force_style(
    style_id: str,
    font_name: str = "Traditional Arabic",
    max_text_len: int = 0,
    font_size_override: int | None = None,
) -> str:
    style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
    base = int(font_size_override or style["font_size"])
    size = font_size_for_length(base, max_text_len)
    alignment = style["alignment"]
    margin_v = style["margin_v"]
    if max_text_len > 70 and alignment == 5:
        alignment = 2
        margin_v = max(margin_v, 140)
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
        "MarginL=70",
        "MarginR=70",
        "WrapStyle=2",
    ]
    if style.get("back_colour"):
        parts.append(f"BackColour={style['back_colour']}")
    return ",".join(parts)


def decorate_srt_text(text: str, style_id: str) -> str:
    """Ajoute tags ASS inline (fade) si le style l'exige."""
    style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
    if style.get("fade"):
        # fade in 400ms / fade out 500ms
        return "{\\fad(400,500)}" + text
    return text


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


def liste_styles_video():
    return [
        {"id": s["id"], "name": s["name"], "description": s["description"]}
        for s in VIDEO_STYLES.values()
    ]
