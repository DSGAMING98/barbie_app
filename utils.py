"""
Shared utilities for the Barbie Streamlit app.
Keep this file dependency-light and UI-agnostic.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import streamlit as st




APP_VERSION = "0.1.0"


def new_id(prefix: str = "id") -> str:
    """Generate a short unique id for UI elements or filenames."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"




def _looks_like_root(p: Path) -> bool:
    """Heuristic to detect the project root."""
    return (p / "assets").is_dir() and (p / "styles").is_dir() and (p / ".streamlit").is_dir()


@lru_cache(maxsize=1)
def project_root() -> Path:
    """
    Find the project root by walking up from this file.
    Assumes the root contains: /assets, /styles, /.streamlit
    """
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if _looks_like_root(candidate):
            return candidate

    return here.parent


@lru_cache(maxsize=1)
def paths() -> Dict[str, Path]:
    """Centralized path registry."""
    root = project_root()
    return {
        "root": root,
        "assets": root / "assets",
        "images": root / "assets" / "images",
        "stickers": root / "assets" / "stickers",
        "fonts": root / "assets" / "fonts",
        "styles": root / "styles",
        "data": root / "data",
        "pages": root / "pages",
        "components": root / "components",
        "streamlit": root / ".streamlit",
    }


def asset_path(*parts: str) -> Path:
    """Build a path under /assets safely."""
    return (paths()["assets"]).joinpath(*parts).resolve()


def data_path(*parts: str) -> Path:
    """Build a path under /data safely."""
    return (paths()["data"]).joinpath(*parts).resolve()


def style_path(*parts: str) -> Path:
    """Build a path under /styles safely."""
    return (paths()["styles"]).joinpath(*parts).resolve()




def get_state(key: str, default: Any = None) -> Any:
    """Read from st.session_state with a default."""
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def set_state(key: str, value: Any) -> None:
    """Write to st.session_state."""
    st.session_state[key] = value


def run_once(flag: str) -> bool:
    """
    Returns True the first time it's called per session for a given flag.
    Useful for one-time init.
    """
    fkey = f"__once_{flag}"
    if not get_state(fkey, False):
        set_state(fkey, True)
        return True
    return False




def load_json(relative_to_data: str, default: Any = None) -> Any:
    """
    Load JSON from /data/<relative_to_data>.
    If missing or invalid, returns `default` (defaults to empty list).
    """
    p = data_path(relative_to_data)
    if default is None:
        default = []
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return default
    except Exception:
        return default


def save_json(relative_to_data: str, obj: Any) -> bool:
    """
    Save JSON to /data/<relative_to_data>.
    Returns True on success, False on failure.
    """
    p = data_path(relative_to_data)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False




@dataclass(frozen=True)
class Theme:
    primary: str = "#ff4fb7"      # Barbie pink (adjustable)
    secondary: str = "#ffe6f3"    # Soft blush
    accent: str = "#ffffff"       # White
    text: str = "#1f1f1f"         # Dark text
    muted_text: str = "#6b6b6b"   # Secondary text
    success: str = "#34c759"
    warning: str = "#ffcc00"
    error: str = "#ff3b30"


@lru_cache(maxsize=1)
def theme() -> Theme:
    """Return app theme. Could be extended to read from config.toml later."""
    return Theme()


def hex_color_ok(hex_color: str) -> bool:
    """Basic validator for #RRGGBB or #RGB."""
    if not isinstance(hex_color, str):
        return False
    s = hex_color.strip()
    if not s.startswith("#"):
        return False
    length = len(s)
    return length in (4, 7) and all(c in "0123456789abcdefABCDEF" for c in s[1:])


def contrast_text_for(bg_hex: str) -> str:
    """
    Return '#000000' or '#ffffff' for readable text over a given bg color.
    Uses luminance heuristic.
    """
    if not hex_color_ok(bg_hex):
        return "#000000"
    h = bg_hex.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    # Relative luminance approximation
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance > 160 else "#ffffff"


def inject_css() -> None:
    """
    Safely inject /styles/base.css and /styles/barbie.css if present.
    No-op if styles are missing.
    """
    base = style_path("base.css")
    barbie = style_path("barbie.css")
    css_chunks: List[str] = []
    if base.exists():
        css_chunks.append(base.read_text(encoding="utf-8"))
    if barbie.exists():
        css_chunks.append(barbie.read_text(encoding="utf-8"))
    if css_chunks:
        st.markdown(f"<style>\n{'\n'.join(css_chunks)}\n</style>", unsafe_allow_html=True)




DEFAULT_PALETTES: List[Dict[str, str]] = [
    {"name": "Barbie Classic", "primary": "#ff4fb7", "secondary": "#ffe6f3", "accent": "#ffffff"},
    {"name": "Dreamhouse Sunset", "primary": "#ff7aa9", "secondary": "#ffd1dc", "accent": "#fff4fa"},
    {"name": "Midnight Glam", "primary": "#1f1f1f", "secondary": "#ff4fb7", "accent": "#f5f5f5"},
]

DEFAULT_QUOTES: List[str] = [
    "You can be anything.",
    "Play like a legend.",
    "Owned, not borrowed confidence.",
    "Dream it. Plan it. Do it.",
]


@lru_cache(maxsize=1)
def palettes() -> List[Dict[str, str]]:
    """Load palettes from /data/palettes.json or fall back to defaults."""
    data = load_json("palettes.json", default=DEFAULT_PALETTES)
    # sanitize
    clean: List[Dict[str, str]] = []
    for p in data:
        primary = p.get("primary", "#ff4fb7")
        secondary = p.get("secondary", "#ffe6f3")
        accent = p.get("accent", "#ffffff")
        if not hex_color_ok(primary) or not hex_color_ok(secondary) or not hex_color_ok(accent):
            continue
        clean.append({"name": p.get("name", "Custom"), "primary": primary, "secondary": secondary, "accent": accent})
    return clean or DEFAULT_PALETTES


@lru_cache(maxsize=1)
def quotes() -> List[str]:
    """Load affirmations/quotes from /data/quotes.json or fall back to defaults."""
    data = load_json("quotes.json", default=DEFAULT_QUOTES)
    if isinstance(data, list) and data:
        # Deduplicate and strip
        dedup = list(dict.fromkeys(s.strip() for s in data if isinstance(s, str) and s.strip()))
        return dedup or DEFAULT_QUOTES
    return DEFAULT_QUOTES




def now_iso() -> str:
    """Current timestamp in ISO format."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def slugify(text: str) -> str:
    """Simple slugify for filenames/ids."""
    keep = "".join(c if c.isalnum() else "-" for c in text.strip().lower())
    slim = "-".join(part for part in keep.split("-") if part)
    return slim or "untitled"


def safe_toast(msg: str) -> None:
    """
    Show a non-blocking toast if available.
    Fall back to st.info if the Streamlit version lacks st.toast.
    """
    try:
        st.toast(msg)
    except Exception:
        st.info(msg)


def download_bytes(label: str, data: bytes, file_name: str, mime: str) -> None:
    """Convenience wrapper for a download button."""
    st.download_button(
        label=label,
        data=data,
        file_name=file_name,
        mime=mime,
        use_container_width=True,
    )




def bootstrap_page(title: str, page_icon: str = "👛", layout: str = "wide") -> None:
    """
    Standard page setup: config + CSS + header line.
    Keep the icon minimal; pages can override if desired.
    """
    st.set_page_config(page_title=title, page_icon=page_icon, layout=layout)
    inject_css()
    # Top header spacer (optional, light visual rhythm; can be removed if undesired)
    st.markdown(
        """
        <div style="height: 6px; border-radius: 999px; background: linear-gradient(90deg, #ff4fb7, #ffe6f3); margin: 4px 0 12px 0;"></div>
        """,
        unsafe_allow_html=True,
    )
