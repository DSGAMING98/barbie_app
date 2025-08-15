from __future__ import annotations

import io, math, random
from typing import Tuple, List, Dict, Optional

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


st.set_page_config(page_title="Photo Booth", page_icon="📸", layout="wide")

CANVAS_PRESETS = {
    "Square 1080": (1080, 1080),
    "Story 1080×1920": (1080, 1920),
    "Post 1350×1080": (1350, 1080),
    "Banner 1600×900": (1600, 900),
}
DEFAULT_SIZE = "Square 1080"

def try_font(size: int):
    for cand in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except Exception:
            pass
    return ImageFont.load_default()

def hex_to_rgba(h: str, a: int = 255) -> Tuple[int,int,int,int]:
    s = h.strip().lstrip("#")
    if len(s)==3: s="".join(c*2 for c in s)
    return int(s[0:2],16), int(s[2:4],16), int(s[4:6],16), a

def clamp(v, a, b): return max(a, min(b, v))

def blank(w: int, h: int, color=(0,0,0,0)) -> Image.Image:
    return Image.new("RGBA", (w, h), color)

def center_paste(canvas: Image.Image, child: Image.Image, xy: Tuple[int,int]) -> Image.Image:
    """Paste child at xy *center* (child center at xy) with alpha."""
    x = int(xy[0] - child.width/2)
    y = int(xy[1] - child.height/2)
    layer = blank(*canvas.size)
    layer.paste(child, (x, y), child)
    return Image.alpha_composite(canvas, layer)

def fit_cover(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Scale/crop to completely cover target box (like CSS background-size: cover)."""
    w, h = img.size
    scale = max(box_w / w, box_h / h)
    nw, nh = int(w*scale), int(h*scale)
    im = img.resize((nw, nh), Image.LANCZOS)
    x = (nw - box_w) // 2
    y = (nh - box_h) // 2
    return im.crop((x, y, x + box_w, y + box_h)).convert("RGBA")


def apply_basic_adjust(img: Image.Image, bright=1.0, contrast=1.0, color=1.0, sharp=1.0) -> Image.Image:
    out = ImageEnhance.Brightness(img).enhance(float(bright))
    out = ImageEnhance.Contrast(out).enhance(float(contrast))
    out = ImageEnhance.Color(out).enhance(float(color))
    out = ImageEnhance.Sharpness(out).enhance(float(sharp))
    return out

def temperature_tint(img: Image.Image, temp: float = 0.0) -> Image.Image:
    """temp in [-1..+1]: negative=cool, positive=warm."""
    if abs(temp) < 1e-3: return img
    r, g, b, a = img.split()
    t = clamp(temp, -1, 1)
    r = r.point(lambda p: clamp(int(p * (1 + 0.15*t)), 0, 255))
    b = b.point(lambda p: clamp(int(p * (1 - 0.15*t)), 0, 255))
    return Image.merge("RGBA", (r, g, b, a))

def bloom(img: Image.Image, strength: float = 0.0, radius: int = 10) -> Image.Image:
    """Soft glow bloom."""
    if strength <= 0: return img
    blur = img.filter(ImageFilter.GaussianBlur(radius=max(2, radius)))
    return Image.blend(img, blur, alpha=float(clamp(strength, 0, 1)))

def vignette(img: Image.Image, strength: float = 0.0) -> Image.Image:
    if strength <= 0: return img
    w, h = img.size
    mask = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(mask)
    d.ellipse((-int(w*0.35), -int(h*0.35), int(w*1.35), int(h*1.35)), fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h)*0.12)))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, int(220*strength)))
    return Image.composite(Image.alpha_composite(img, dark), img, mask)  # dark corners

def film_grain(img: Image.Image, amount: float = 0.0) -> Image.Image:
    if amount <= 0: return img
    w, h = img.size
    noise = (np.random.random((h, w))*255).astype(np.uint8)
    n = Image.fromarray(noise, mode="L").filter(ImageFilter.GaussianBlur(0.6))
    alpha = n.point(lambda p: int(p * clamp(amount, 0, 0.25)))
    grain = Image.merge("RGBA", (n, n, n, alpha))
    return Image.alpha_composite(img, grain)

def matte_fade(img: Image.Image, lift: int = 0) -> Image.Image:
    """Lift blacks for a matte/retro vibe. lift 0..80."""
    if lift <= 0: return img
    r, g, b, a = img.split()
    def f(p): return clamp(int((p/255)**0.9 * (255 - lift) + lift), 0, 255)
    return Image.merge("RGBA", (r.point(f), g.point(f), b.point(f), a))

# LUT-ish presets built from the above
def apply_preset(img: Image.Image, name: str) -> Image.Image:
    name = (name or "").lower()
    if name == "" or name == "none": return img
    out = img
    if name == "barbie glam":
        out = apply_basic_adjust(out, 1.06, 1.08, 1.18, 1.02)
        out = temperature_tint(out, +0.25)
        out = bloom(out, 0.18, 12)
        out = vignette(out, 0.15)
    elif name == "retro film":
        out = apply_basic_adjust(out, 0.98, 1.04, 0.92, 0.9)
        out = temperature_tint(out, -0.08)
        out = matte_fade(out, 36)
        out = film_grain(out, 0.18)
        out = vignette(out, 0.22)
    elif name == "dreamy pastel":
        out = apply_basic_adjust(out, 1.04, 0.96, 1.25, 0.9)
        out = bloom(out, 0.28, 18)
        out = temperature_tint(out, +0.18)
    elif name == "noir":
        # convert to monochrome with contrast boost
        r, g, b, a = out.split()
        gray = Image.merge("RGB", (r, g, b)).convert("L")
        gray = ImageEnhance.Contrast(gray).enhance(1.35)
        out = Image.merge("RGBA", (gray, gray, gray, a))
        out = vignette(out, 0.25)
        out = matte_fade(out, 28)
    else:
        return img
    return out


def frame_none(canvas: Image.Image) -> Image.Image:
    return canvas

def frame_glass(canvas: Image.Image) -> Image.Image:
    w, h = canvas.size
    overlay = blank(w, h)
    d = ImageDraw.Draw(overlay, "RGBA")
    d.rounded_rectangle((12, 12, w-12, h-12), radius=28, outline=(255,255,255,200), width=2)
    d.rounded_rectangle((24, 24, w-24, h-24), radius=24, fill=(255,255,255,70))
    shine = blank(w, h)
    ds = ImageDraw.Draw(shine)
    ds.polygon([(0,0),(int(w*0.55),0),(0,int(h*0.25))], fill=(255,255,255,50))
    return Image.alpha_composite(Image.alpha_composite(canvas, overlay), shine)

def frame_polaroid(canvas: Image.Image) -> Image.Image:
    w, h = canvas.size
    pad = int(min(w,h)*0.06)
    bottom = int(pad*2.6)
    frame = blank(w, h)
    d = ImageDraw.Draw(frame, "RGBA")
    d.rounded_rectangle((pad, pad, w-pad, h-pad), radius=28, fill=(255,255,255,255))
    # window cut
    win = (pad+int(pad*0.6), pad+int(pad*0.6), w-pad-int(pad*0.6), h-pad-bottom)
    mask = Image.new("L", (w, h), 255); dm = ImageDraw.Draw(mask)
    dm.rounded_rectangle(win, radius=18, fill=0)
    frame.putalpha(mask.point(lambda p: 255 - p))
    return Image.alpha_composite(frame, canvas)

def frame_film(canvas: Image.Image) -> Image.Image:
    w, h = canvas.size
    overlay = blank(w, h)
    d = ImageDraw.Draw(overlay, "RGBA")
    d.rectangle((0, 0, w, h), outline=(25,25,25,255), width=46)
    hole_w, hole_h, gap = 36, 22, 100
    for x in range(70, w-70, gap):
        d.rounded_rectangle((x, 22, x+hole_w, 22+hole_h), 6, fill=(230,230,230,220))
        d.rounded_rectangle((x, h-22-hole_h, x+hole_w, h-22), 6, fill=(230,230,230,220))
    return Image.alpha_composite(canvas, overlay)

def frame_glitter(canvas: Image.Image, color="#ff4fb7") -> Image.Image:
    w, h = canvas.size
    overlay = blank(w, h)
    d = ImageDraw.Draw(overlay, "RGBA")
    d.rounded_rectangle((10, 10, w-10, h-10), radius=26, outline=hex_to_rgba(color, 255), width=6)
    rng = random.Random(21)
    for _ in range(int((w+h)*0.6)):
        x, y = rng.randint(12, w-12), rng.randint(12, h-12)
        r = rng.randint(1, 3)
        a = rng.randint(120, 220)
        d.ellipse((x-r, y-r, x+r, y+r), fill=hex_to_rgba(color, a))
    return Image.alpha_composite(canvas, overlay)

FRAME_STYLES = {
    "None": frame_none,
    "Glass": frame_glass,
    "Polaroid": frame_polaroid,
    "Film": frame_film,
    "Glitter": frame_glitter,
}


def sticker_shape(name: str, size: int, color_hex: str) -> Image.Image:
    s = int(size)
    col = hex_to_rgba(color_hex, 255)
    layer = blank(s, s)
    d = ImageDraw.Draw(layer, "RGBA")
    if name == "Heart":
        r = s//2
        d.pieslice((0,0,r,r), 180, 360, fill=col)
        d.pieslice((r,0,s,r), 180, 360, fill=col)
        d.polygon([(0,r//2),(s,r//2),(r,s)], fill=col)
    elif name == "Star":
        cx, cy = s/2, s/2
        pts=[]
        for i in range(10):
            ang = math.pi/2 + i*math.pi/5
            rad = s*0.48 if i%2==0 else s*0.2
            pts.append((cx+rad*math.cos(ang), cy-rad*math.sin(ang)))
        d.polygon(pts, fill=col)
    elif name == "Sparkle":
        d.ellipse((s*0.42, 0, s*0.58, s*0.8), fill=col)
        d.ellipse((0, s*0.42, s*0.8, s*0.58), fill=col)
        d.ellipse((s*0.2, s*0.2, s*0.8, s*0.8), outline=col, width=4)
    elif name == "Bubble":
        d.rounded_rectangle((6,6,s-6,s-22), radius=20, fill=col)
        d.polygon([(s*0.3,s-22),(s*0.46,s-6),(s*0.54,s-24)], fill=col)
    elif name == "Sunnies":
        d.rounded_rectangle((s*0.1,s*0.4,s*0.42,s*0.65), 10, fill=col)
        d.rounded_rectangle((s*0.58,s*0.4,s*0.9,s*0.65), 10, fill=col)
        d.rectangle((s*0.42,s*0.48,s*0.58,s*0.56), fill=col)
        d.rectangle((0,s*0.49,s*0.1,s*0.55), fill=col)
        d.rectangle((s*0.9,s*0.49,s*1.0,s*0.55), fill=col)
    else:  # Dot
        d.ellipse((6,6,s-6,s-6), fill=col)
    return layer

def rotate_scale(img: Image.Image, deg: float, scale: float) -> Image.Image:
    s = max(0.05, float(scale))
    new = img.resize((max(1,int(img.width*s)), max(1,int(img.height*s))), Image.LANCZOS)
    return new.rotate(float(deg), expand=True)

# Keep sticker state
if "pb_stickers" not in st.session_state:
    st.session_state.pb_stickers: List[Dict] = []  # {name,color,size,deg,scale,x,y,caption,cap_color,cap_size}


with st.sidebar:
    st.header("Canvas")
    preset = st.selectbox("Preset", list(CANVAS_PRESETS.keys()), index=list(CANVAS_PRESETS.keys()).index(DEFAULT_SIZE))
    CANVAS_W, CANVAS_H = CANVAS_PRESETS[preset]
    bg_color = st.color_picker("Background", "#fff4fa")
    frame_style = st.selectbox("Frame", list(FRAME_STYLES.keys()), index=1)
    st.divider()

    st.header("Photo")
    src = st.radio("Source", ["Upload", "Camera"], index=0, horizontal=True)
    file = st.file_uploader("Image (PNG/JPG)", type=["png","jpg","jpeg"]) if src=="Upload" else None
    shot = st.camera_input("Take a photo") if src=="Camera" else None
    fill_mode = st.radio("Fit Mode", ["Cover (fill)", "Contain (fit)"], index=0, horizontal=True)
    padding = st.slider("Padding", 0, int(min(CANVAS_W, CANVAS_H)*0.3), 40)
    st.divider()

    st.header("Looks")
    preset_name = st.selectbox("Preset", ["None","Barbie Glam","Retro Film","Dreamy Pastel","Noir"], index=1)
    bright = st.slider("Brightness", 0.3, 1.7, 1.0, 0.01)
    contrast = st.slider("Contrast", 0.3, 1.7, 1.0, 0.01)
    saturation = st.slider("Saturation", 0.3, 1.7, 1.0, 0.01)
    sharpness = st.slider("Sharpness", 0.3, 2.0, 1.0, 0.01)
    temp = st.slider("Temperature", -1.0, 1.0, 0.0, 0.01)
    bloom_amt = st.slider("Bloom", 0.0, 1.0, 0.2, 0.01)
    vign = st.slider("Vignette", 0.0, 0.6, 0.18, 0.01)
    grain = st.slider("Film Grain", 0.0, 0.25, 0.10, 0.01)
    matte = st.slider("Matte Fade", 0, 80, 24, 1)
    st.divider()

    st.header("Caption")
    caption = st.text_input("Text", "living my dream ✨")
    cap_color = st.color_picker("Text Color", "#1b1b1b")
    cap_size = st.slider("Size", 14, 128, 48)
    cap_x = st.slider("X", 0, CANVAS_W, CANVAS_W//2)
    cap_y = st.slider("Y", 0, CANVAS_H, CANVAS_H-90)
    st.divider()

    st.header("Stickers")
    s_name = st.selectbox("Style", ["Heart","Star","Sparkle","Bubble","Sunnies","Dot"])
    s_color = st.color_picker("Color", "#ff4fb7")
    s_size  = st.slider("Base Size", 40, 400, 160)
    s_rot   = st.slider("Rotate°", -180, 180, 0)
    s_scale = st.slider("Scale %", 10, 300, 100) / 100.0
    s_x     = st.slider("X ", 0, CANVAS_W, CANVAS_W//2)
    s_y     = st.slider("Y ", 0, CANVAS_H, CANVAS_H//2)
    colA, colB = st.columns(2)
    with colA:
        if st.button("➕ Add Sticker", use_container_width=True):
            st.session_state.pb_stickers.append({
                "name": s_name, "color": s_color, "size": int(s_size),
                "deg": float(s_rot), "scale": float(s_scale), "x": int(s_x), "y": int(s_y)
            })
    with colB:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.pb_stickers = []
    st.divider()

    st.header("Export")
    export_scale = st.select_slider("Scale", [1,2,3], value=2)


# base canvas
canvas = blank(CANVAS_W, CANVAS_H, hex_to_rgba(bg_color))

# bring in photo
photo: Optional[Image.Image] = None
if file is not None:
    try:
        photo = Image.open(file).convert("RGBA")
    except Exception:
        st.error("Could not read the uploaded image.")
elif shot is not None:
    try:
        photo = Image.open(shot).convert("RGBA")
    except Exception:
        st.error("Could not read the camera shot.")

if photo is not None:
    box_w = CANVAS_W - padding*2
    box_h = CANVAS_H - padding*2
    if fill_mode.startswith("Cover"):
        fitted = fit_cover(photo, box_w, box_h)
    else:
        # Contain: keep whole image inside, letterbox transparent
        img = photo.copy()
        img.thumbnail((box_w, box_h), Image.LANCZOS)
        fitted = blank(box_w, box_h)
        fitted.paste(img, ((box_w - img.width)//2, (box_h - img.height)//2), img)
    # apply looks
    fx = apply_basic_adjust(fitted, bright, contrast, saturation, sharpness)
    fx = temperature_tint(fx, temp)
    fx = bloom(fx, bloom_amt, 14)
    fx = matte_fade(fx, matte)
    fx = vignette(fx, vign)
    fx = film_grain(fx, grain)
    fx = apply_preset(fx, preset_name)
    # paste centered box
    layer = blank(CANVAS_W, CANVAS_H)
    layer.paste(fx, (padding, padding), fx)
    canvas = Image.alpha_composite(canvas, layer)

# caption
if caption.strip():
    f = try_font(int(cap_size))
    txt = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    d = ImageDraw.Draw(txt)
    shadow = (0,0,0,90)
    d.text((cap_x+2, cap_y+2), caption, font=f, fill=shadow)
    d.text((cap_x, cap_y), caption, font=f, fill=hex_to_rgba(cap_color))
    canvas = Image.alpha_composite(canvas, txt)

# stickers
for s in st.session_state.pb_stickers:
    base = sticker_shape(s["name"], s["size"], s["color"])
    sticker_img = rotate_scale(base, s["deg"], s["scale"])
    layer = blank(CANVAS_W, CANVAS_H)
    x = clamp(s["x"] - sticker_img.width//2, 0, CANVAS_W - sticker_img.width)
    y = clamp(s["y"] - sticker_img.height//2, 0, CANVAS_H - sticker_img.height)
    layer.paste(sticker_img, (x, y), sticker_img)
    canvas = Image.alpha_composite(canvas, layer)

# frame last
canvas = FRAME_STYLES[frame_style](canvas)


st.markdown("### 🎛️ Scene Presets")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("💗 Glam Portrait", use_container_width=True):
        st.session_state.update(dict(pb_stickers=[]))
        st.session_state["__preset_fill"] = ("Cover", 60, "Barbie Glam", 1.06, 1.1, 1.2, 1.02, 0.25, 0.25, 0.12, 18)
with c2:
    if st.button("🪩 Retro Film", use_container_width=True):
        st.session_state.update(dict(pb_stickers=[]))
        st.session_state["__preset_fill"] = ("Cover", 40, "Retro Film", 0.98, 1.04, 0.92, 0.9, -0.08, 0.18, 0.22, 36)
with c3:
    if st.button("🌫 Dreamy Pastel", use_container_width=True):
        st.session_state.update(dict(pb_stickers=[]))
        st.session_state["__preset_fill"] = ("Contain (fit)", 80, "Dreamy Pastel", 1.04, 0.96, 1.25, 0.9, 0.18, 0.28, 0.12, 12)
with c4:
    if st.button("🖤 Noir", use_container_width=True):
        st.session_state.update(dict(pb_stickers=[]))
        st.session_state["__preset_fill"] = ("Cover", 40, "Noir", 1.0, 1.1, 0.0, 1.0, 0.0, 0.0, 0.25, 28)

# Helper to apply scene preset immediately
if "__preset_fill" in st.session_state:
    fm, pad, pn, br, ct, sat, sh, tp, blm, vg, mt = st.session_state["__preset_fill"]

    st.session_state["padding"] = pad
    st.session_state["preset_name"] = pn
    st.session_state["bright"] = br
    st.session_state["contrast"] = ct
    st.session_state["saturation"] = sat
    st.session_state["sharpness"] = sh
    st.session_state["temp"] = tp
    st.session_state["bloom_amt"] = blm
    st.session_state["vign"] = vg
    st.session_state["matte"] = mt
    # visual feedback chip
    st.info(f"Preset applied: {pn}")
    del st.session_state["__preset_fill"]


st.image(canvas, caption="Photo Booth Preview", use_container_width=True)

out = canvas if export_scale == 1 else canvas.resize((CANVAS_W*export_scale, CANVAS_H*export_scale), Image.LANCZOS)
buf = io.BytesIO(); out.save(buf, format="PNG")
st.download_button("Download PNG", data=buf.getvalue(), file_name="photo_booth.png", mime="image/png", use_container_width=True)
