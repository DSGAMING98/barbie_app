from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional
from PIL import Image

def load_image(path: Path | str, fallback_color: str = "#ffffff", size: tuple[int,int] | None = None) -> Image.Image:
    """Load an image if present; otherwise return a plain fallback canvas."""
    p = Path(path)
    if p.exists():
        img = Image.open(p).convert("RGBA")
        return img.resize(size, Image.LANCZOS) if size else img
    # fallback canvas
    w, h = size or (800, 600)
    bg = Image.new("RGBA", (w, h), fallback_color)
    return bg

def compose(base: Image.Image, layers: Iterable[Image.Image]) -> Image.Image:
    """Alpha-composite a stack of RGBA layers onto base."""
    out = base.copy()
    for layer in layers:
        out.alpha_composite(layer)
    return out

def to_png_bytes(img: Image.Image) -> bytes:
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
