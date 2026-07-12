"""Presets de sous-titres (ASS) et de rendu vidéo."""

from __future__ import annotations

SUBTITLE_STYLES: dict[str, dict] = {
    "classic": {
        "id": "classic",
        "name": "Classique",
        "description": "Blanc, contour noir, bas de l'écran",
        "preview": {"color": "#FFFFFF", "outline": "#000000", "align": "bottom"},
        "font_size": 22,
        "primary": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "outline": 2,
        "alignment": 2,
        "margin_v": 120,
        "border_style": 1,
    },
    "gold": {
        "id": "gold",
        "name": "Or",
        "description": "Doré élégant, contour sombre",
        "preview": {"color": "#E8C547", "outline": "#1A1208", "align": "bottom"},
        "font_size": 24,
        "primary": "&H0047C5E8",  # BGR
        "outline_colour": "&H0008121A",
        "outline": 2,
        "alignment": 2,
        "margin_v": 120,
        "border_style": 1,
    },
    "center": {
        "id": "center",
        "name": "Méditation",
        "description": "Blanc centré au milieu",
        "preview": {"color": "#F5F0E8", "outline": "#0D1F1A", "align": "center"},
        "font_size": 26,
        "primary": "&H00E8F0F5",
        "outline_colour": "&H001A1F0D",
        "outline": 2,
        "alignment": 5,
        "margin_v": 0,
        "border_style": 1,
    },
    "soft": {
        "id": "soft",
        "name": "Doux",
        "description": "Blanc crème, contour fin",
        "preview": {"color": "#F2EDE4", "outline": "#2A3530", "align": "bottom"},
        "font_size": 20,
        "primary": "&H00E4EDF2",
        "outline_colour": "&H0030352A",
        "outline": 1,
        "alignment": 2,
        "margin_v": 140,
        "border_style": 1,
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
    },
}

VIDEO_STYLES: dict[str, dict] = {
    "clean": {
        "id": "clean",
        "name": "Épuré",
        "description": "Recadrage vertical net",
    },
    "blur": {
        "id": "blur",
        "name": "Flou ciné",
        "description": "Fond flou + assombrissement léger",
    },
    "dark": {
        "id": "dark",
        "name": "Nuit",
        "description": "Vignette et tons sombres",
    },
    "kenburns": {
        "id": "kenburns",
        "name": "Zoom lent",
        "description": "Léger zoom progressif (Ken Burns)",
    },
    "split": {
        "id": "split",
        "name": "Bande basse",
        "description": "Bande semi-opaque pour les sous-titres",
    },
}


def font_size_for_length(base: int, max_chars: int) -> int:
    """Réduit la taille si le verset est long (évite de remplir tout l'écran)."""
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
) -> str:
    style = SUBTITLE_STYLES.get(style_id, SUBTITLE_STYLES["classic"])
    size = font_size_for_length(int(style["font_size"]), max_text_len)
    # Longs versets : forcer bas d'écran même en mode "center"
    alignment = style["alignment"]
    margin_v = style["margin_v"]
    if max_text_len > 70 and alignment == 5:
        alignment = 2
        margin_v = max(margin_v, 140)
    return (
        f"FontName={font_name},"
        f"FontSize={size},"
        f"PrimaryColour={style['primary']},"
        f"OutlineColour={style['outline_colour']},"
        f"BorderStyle={style['border_style']},"
        f"Outline={style['outline']},"
        f"Alignment={alignment},"
        f"MarginV={margin_v},"
        f"MarginL=70,MarginR=70,"
        f"WrapStyle=2"
    )


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
