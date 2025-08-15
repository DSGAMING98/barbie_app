from __future__ import annotations

import io, json, math, random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageFont


st.set_page_config(page_title="Dreamhouse Designer", page_icon="🏡", layout="wide")

CANVAS_W, CANVAS_H = 1400, 900
GRID = 20


def try_font(size: int):
    for cand in ("arial.ttf", "DejaVuSans.ttf"):
        try: return ImageFont.truetype(cand, size)
        except Exception: pass
    return ImageFont.load_default()

def hex_to_rgb(h: str) -> Tuple[int,int,int]:
    s = h.strip().lstrip("#")
    if len(s)==3: s = "".join(c*2 for c in s)
    return int(s[0:2],16), int(s[2:4],16), int(s[4:6],16)

def clamp(v,a,b): return max(a, min(b, v))

def blank(size=(CANVAS_W, CANVAS_H), color=(0,0,0,0)) -> Image.Image:
    return Image.new("RGBA", size, color)

def rr(draw: ImageDraw.ImageDraw, box, radius: int, fill=None, outline=None, width: int = 1):
    try: draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception: draw.rectangle(box, fill=fill, outline=outline, width=width)

def snap(val: int, enabled: bool) -> int:
    return (val//GRID)*GRID if enabled else val

def rotate_paste(base: Image.Image, item: Image.Image, center_xy: Tuple[int,int], deg: float):
    rotated = item.rotate(deg, expand=True)
    x = int(center_xy[0] - rotated.width/2)
    y = int(center_xy[1] - rotated.height/2)
    layer = blank(base.size)
    layer.paste(rotated, (x,y), rotated)
    return Image.alpha_composite(base, layer)


def floor_pattern(size: Tuple[int,int], mode: str, c1: str, c2: str) -> Image.Image:
    w,h = size
    img = Image.new("RGBA", size, c2)
    d = ImageDraw.Draw(img)
    if mode == "Herringbone":
        tile_w, tile_h = 120, 40
        for y in range(-tile_h, h+tile_h, tile_h):
            for x in range(-tile_w, w+tile_w, tile_w):
                xo = x + (0 if (y//tile_h)%2==0 else tile_w//2)
                pts = [(xo, y),(xo+tile_w, y),(xo+tile_w-tile_h, y+tile_h),(xo-tile_h, y+tile_h)]
                d.polygon(pts, fill=c1)
    elif mode == "Checker":
        sz = 90
        for yy in range(0,h,sz):
            for xx in range(0,w,sz):
                if ((xx//sz)+(yy//sz))%2==0:
                    d.rectangle((xx,yy,xx+sz,yy+sz), fill=c1)
    elif mode == "Terrazzo":
        rng = random.Random(9)
        base = Image.new("RGBA", size, c2)
        d = ImageDraw.Draw(base, "RGBA")
        chips = int((w*h)/12000)
        options = [
            (*hex_to_rgb(c1), 255),
            (*hex_to_rgb("#ffd1dc"), 255),
            (*hex_to_rgb("#c1fff4"), 255),
            (*hex_to_rgb("#ffe28a"), 255),
        ]
        for _ in range(chips):
            rx,ry = rng.randint(0,w), rng.randint(0,h)
            rw,rh = rng.randint(10,40), rng.randint(10,40)
            col = options[rng.randint(0,len(options)-1)]
            d.polygon([(rx,ry),(rx+rw,ry+rh//3),(rx+rw//2,ry+rh)], fill=col)
        img = base
    else:
        # Wood planks
        plank_h = 70
        for i,y in enumerate(range(0,h,plank_h)):
            d.rectangle((0,y,w,y+plank_h), fill=c2 if i%2 else c1)
            for x in range(0,w,260):
                d.line((x,y,x,y+plank_h), fill=(0,0,0,30), width=2)
    return img

def wall_pattern(size: Tuple[int,int], mode: str, c: str) -> Image.Image:
    w,h = size
    img = Image.new("RGBA", size, c)
    d = ImageDraw.Draw(img, "RGBA")
    if mode == "Wainscot":
        d.rectangle((0, int(h*0.55), w, h), fill=(255,255,255,80), outline=None)
        for x in range(40, w, 180):
            rr(d, (x, int(h*0.55)+20, x+120, h-30), 12, fill=(255,255,255,50), outline=(255,255,255,140), width=2)
    elif mode == "Panel":
        for y in range(40, h-40, 140):
            for x in range(40, w-40, 200):
                rr(d, (x,y,x+160,y+100), 12, fill=None, outline=(255,255,255,160), width=2)
    elif mode == "Stripes":
        for x in range(0,w,60):
            col = (255,255,255,40) if (x//60)%2==0 else (255,255,255,0)
            d.rectangle((x,0,x+60,h), fill=col)
    return img

def render_room(bg_hex: str, wall_hex: str, wall_mode: str, floor_mode: str,
                floor_c1: str, floor_c2: str, skirting_hex: str) -> Image.Image:
    # full-size base
    room = blank((CANVAS_W, CANVAS_H), (*hex_to_rgb(bg_hex), 255))

    #  WALL (compose as full canvas)
    wall_h = int(CANVAS_H * 0.62)
    wall_tex = wall_pattern((CANVAS_W, wall_h), wall_mode, wall_hex)  # (W, wall_h)
    wall_full = blank((CANVAS_W, CANVAS_H))
    wall_full.paste(wall_tex, (0, 0), wall_tex)
    room = Image.alpha_composite(room, wall_full)

    #  FLOOR (compose as full canvas)
    floor = blank((CANVAS_W, CANVAS_H))
    floor_tex = floor_pattern((CANVAS_W, int(CANVAS_H * 0.5)), floor_mode, floor_c1, floor_c2)
    floor_tex = floor_tex.resize((CANVAS_W, int(CANVAS_H * 0.45)))
    floor.paste(floor_tex, (0, int(CANVAS_H * 0.55)), floor_tex)

    #  Horizon shadow
    sh_full = Image.new("L", (CANVAS_W, CANVAS_H), 0)  # full canvas
    ds = ImageDraw.Draw(sh_full)
    y0 = int(CANVAS_H * 0.55) - 80
    y1 = int(CANVAS_H * 0.55)
    span = max(1, y1 - y0)
    for i, y in enumerate(range(y0, y1)):
        ds.rectangle((0, y, CANVAS_W, y + 1), fill=int(120 * (i / span)))
    shadow_rgba = Image.merge("RGBA", (sh_full, sh_full, sh_full, sh_full))
    floor = Image.alpha_composite(floor, shadow_rgba)

    # apply floor onto room
    room = Image.alpha_composite(room, floor)

    # skirting board
    d = ImageDraw.Draw(room, "RGBA")
    d.rectangle((0, int(CANVAS_H * 0.55) - 6, CANVAS_W, int(CANVAS_H * 0.55)),
                fill=(*hex_to_rgb(skirting_hex), 255))
    return room



def draw_window(w: int, h: int, mullions: int, frame_hex: str, glass_tint: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,0,w,h), 14, fill=(*hex_to_rgb(glass_tint),160), outline=(*hex_to_rgb(frame_hex),255), width=6)
    # mullions
    for i in range(1, mullions):
        x = int(w * i/mullions)
        d.line((x,8,x,h-8), fill=(*hex_to_rgb(frame_hex),200), width=4)
    d.line((8,h//2,w-8,h//2), fill=(*hex_to_rgb(frame_hex),200), width=4)
    # simple light streak
    d.polygon([(8,8),(int(w*0.45),8),(8,int(h*0.22))], fill=(255,255,255,70))
    return img

def draw_door(w: int, h: int, hex_color: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,0,w,h), 10, fill=hex_to_rgb(hex_color)+(255,), outline=(0,0,0,40), width=3)
    rr(d, (10,12,w-10,h-12), 10, fill=None, outline=(255,255,255,160), width=2)
    # handle
    d.rounded_rectangle((w-26,h//2-4,w-12,h//2+4), 3, fill=(230,230,230,255))
    return img

def draw_wall_art(w: int, h: int, hex_frame: str, hex_art1: str, hex_art2: str, style: str="Abstract") -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,0,w,h), 14, fill=(255,255,255,240), outline=(*hex_to_rgb(hex_frame),255), width=6)
    if style == "Abstract":
        for _ in range(7):
            x1,y1 = random.randint(10,w-10), random.randint(10,h-10)
            x2,y2 = random.randint(10,w-10), random.randint(10,h-10)
            col = hex_to_rgb(hex_art1) if random.random()<0.5 else hex_to_rgb(hex_art2)
            d.line((x1,y1,x2,y2), fill=col+(200,), width=random.randint(4,12))
    else:
        # geometric
        d.rectangle((10,10,w-10,h-10), outline=hex_to_rgb(hex_art1)+(200,), width=6)
        d.ellipse((w*0.25,h*0.25,w*0.75,h*0.75), outline=hex_to_rgb(hex_art2)+(220,), width=10)
    return img


def f_sofa(w: int, h: int, base_hex: str, cushion_hex: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,int(h*0.25),w,h), 26, fill=hex_to_rgb(base_hex)+(255,), outline=(0,0,0,40), width=3)
    rr(d, (0,0,int(w*0.3),int(h*0.5)), 22, fill=hex_to_rgb(base_hex)+(255,))
    rr(d, (int(w*0.7),0,w,int(h*0.5)), 22, fill=hex_to_rgb(base_hex)+(255,))
    # cushions
    for i in range(2):
        rr(d, (int(w*0.25)+i*int(w*0.24), int(h*0.28), int(w*0.45)+i*int(w*0.24), int(h*0.6)), 16, fill=hex_to_rgb(cushion_hex)+(255,))
    # feet
    for x in (int(w*0.08), int(w*0.88)):
        d.rectangle((x-12,h-6,x+12,h), fill=(60,60,60,180))
    return img

def f_armchair(w: int, h: int, hex_color: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,int(h*0.25),w,h), 26, fill=hex_to_rgb(hex_color)+(255,), outline=(0,0,0,40), width=3)
    rr(d, (0,0,int(w*0.32),int(h*0.52)), 22, fill=hex_to_rgb(hex_color)+(255,))
    rr(d, (int(w*0.68),0,w,int(h*0.52)), 22, fill=hex_to_rgb(hex_color)+(255,))
    d.rectangle((w*0.48,h-6,w*0.52,h), fill=(60,60,60,180))
    return img

def f_table(w: int, h: int, top_hex: str, leg_hex: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,int(h*0.15),w,int(h*0.5)), 18, fill=hex_to_rgb(top_hex)+(255,), outline=(0,0,0,30), width=2)
    d.rectangle((w*0.48,int(h*0.5),w*0.52,h), fill=hex_to_rgb(leg_hex)+(255,))
    return img

def f_plant(w: int, h: int, pot_hex: str, leaf_hex: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    # pot
    rr(d, (int(w*0.3), int(h*0.7), int(w*0.7), h), 10, fill=hex_to_rgb(pot_hex)+(255,), outline=(0,0,0,40), width=2)
    # stems & leaves
    for i in range(6):
        cx = int(w*0.5)
        x = cx + int((i-3)*10)
        d.line((cx,int(h*0.7), x, int(h*0.25)), fill=(60,120,60,150), width=3)
        for t in range(3):
            ex = x + random.randint(-30,30); ey = int(h*0.25)+random.randint(-20,20)
            rr(d, (ex-18, ey-8, ex+18, ey+8), 8, fill=hex_to_rgb(leaf_hex)+(220,))
    return img

def f_bed(w: int, h: int, frame_hex: str, sheet_hex: str, pillow_hex: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,int(h*0.4),w,h), 18, fill=hex_to_rgb(sheet_hex)+(255,), outline=(0,0,0,40), width=2)
    rr(d, (0,0,w,int(h*0.45)), 14, fill=hex_to_rgb(frame_hex)+(255,))
    # pillows
    rr(d, (int(w*0.18), int(h*0.1), int(w*0.42), int(h*0.28)), 10, fill=hex_to_rgb(pillow_hex)+(255,))
    rr(d, (int(w*0.58), int(h*0.1), int(w*0.82), int(h*0.28)), 10, fill=hex_to_rgb(pillow_hex)+(255,))
    return img

def f_rug(w: int, h: int, hex_color: str, pattern: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0,0,w,h), 24, fill=hex_to_rgb(hex_color)+(220,))
    if pattern == "Stripes":
        for x in range(10,w,40): d.line((x,10,x,h-10), fill=(255,255,255,90), width=6)
    elif pattern == "Check":
        for y in range(10,h,40):
            for x in range(10,w,40):
                if ((x//40)+(y//40))%2==0: d.rectangle((x,y,x+28,y+28), fill=(255,255,255,90))
    elif pattern == "Dots":
        for y in range(20,h,40):
            for x in range(20,w,40):
                d.ellipse((x-6,y-6,x+6,y+6), fill=(255,255,255,120))
    return img

def f_lamp(w: int, h: int, shade_hex: str, pole_hex: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (int(w*0.45), int(h*0.2), int(w*0.55), int(h*0.9)), 6, fill=hex_to_rgb(pole_hex)+(255,))
    rr(d, (int(w*0.25), 0, int(w*0.75), int(h*0.25)), 16, fill=hex_to_rgb(shade_hex)+(255,))
    return img

def f_shelf(w: int, h: int, hex_color: str) -> Image.Image:
    img = blank((w,h))
    d = ImageDraw.Draw(img, "RGBA")
    for i,y in enumerate((int(h*0.15), int(h*0.45), int(h*0.75))):
        rr(d, (int(w*0.1), y, int(w*0.9), y+18), 6, fill=hex_to_rgb(hex_color)+(255,))
    return img

CATALOG = {
    "Sofa": lambda a,b,c1,c2: f_sofa(a,b,c1,c2),
    "Armchair": lambda a,b,c1,c2: f_armchair(a,b,c1),
    "Coffee Table": lambda a,b,c1,c2: f_table(a,b,c1,c2),
    "Plant": lambda a,b,c1,c2: f_plant(a,b,c2,c1),
    "Bed": lambda a,b,c1,c2: f_bed(a,b,c2,c1,"#ffffff"),
    "Rug": lambda a,b,c1,c2: f_rug(a,b,c1,c2),
    "Lamp": lambda a,b,c1,c2: f_lamp(a,b,c1,c2),
    "Shelf": lambda a,b,c1,c2: f_shelf(a,b,c1),
    "Wall Art": lambda a,b,c1,c2: draw_wall_art(a,b,"#222222",c1,c2,"Abstract"),
    "Window": lambda a,b,c1,c2: draw_window(a,b,4,"#ffffff",c2),
    "Door": lambda a,b,c1,c2: draw_door(a,b,c1),
}

DEFAULT_COLORS = {
    "Sofa": ("#ff7aa9","#ffe6f3"),
    "Armchair": ("#9b5de5","#f7d6ff"),
    "Coffee Table": ("#c8a27e","#6e4f3a"),
    "Plant": ("#78d380","#5b8a5b"),
    "Bed": ("#e7e7e7","#ff4fb7"),
    "Rug": ("#ffe6f3","Stripes"),
    "Lamp": ("#fff2a8","#6e6e6e"),
    "Shelf": ("#d9d9d9","#d9d9d9"),
    "Wall Art": ("#ff4fb7","#00d1ff"),
    "Window": ("#ccccff","#aee3ff"),
    "Door": ("#b57a4a","#b57a4a"),
}


@dataclass
class Item:
    kind: str
    x: int
    y: int
    w: int
    h: int
    rot: float
    c1: str
    c2: str
    extra: str = ""

def ensure_state():
    if "dh_items" not in st.session_state: st.session_state.dh_items: List[Dict] = []
    if "dh_settings" not in st.session_state:
        st.session_state.dh_settings = {
            "bg": "#ffffff",
            "wall": "#ffd1dc",
            "wall_mode": "Wainscot",
            "floor_mode": "Herringbone",
            "floor1": "#e8d4c5",
            "floor2": "#f4eee9",
            "skirting": "#ffffff",
            "snap": True,
            "ambient": "#ffd1dc",
            "ambient_power": 0.18,
            "spot_lights": 2,
        }

ensure_state()


with st.sidebar:
    st.header("Room")
    colR1, colR2 = st.columns(2)
    with colR1: st.session_state.dh_settings["bg"] = st.color_picker("Background", st.session_state.dh_settings["bg"])
    with colR2: st.session_state.dh_settings["wall"] = st.color_picker("Wall", st.session_state.dh_settings["wall"])
    wall_mode = st.selectbox("Wall Style", ["Wainscot","Panel","Stripes","Plain"], index=0)
    st.session_state.dh_settings["wall_mode"] = wall_mode
    floor_mode = st.selectbox("Floor", ["Herringbone","Checker","Terrazzo","Planks"], index=0)
    st.session_state.dh_settings["floor_mode"] = floor_mode
    colF1, colF2 = st.columns(2)
    with colF1: st.session_state.dh_settings["floor1"] = st.color_picker("Floor Primary", st.session_state.dh_settings["floor1"])
    with colF2: st.session_state.dh_settings["floor2"] = st.color_picker("Floor Secondary", st.session_state.dh_settings["floor2"])
    st.session_state.dh_settings["skirting"] = st.color_picker("Skirting", st.session_state.dh_settings["skirting"])
    st.session_state.dh_settings["snap"] = st.toggle("Snap to Grid", st.session_state.dh_settings["snap"], help=f"{GRID}px grid")

    st.divider()
    st.header("Lighting")
    st.session_state.dh_settings["ambient"] = st.color_picker("Ambient Tint", st.session_state.dh_settings["ambient"])
    st.session_state.dh_settings["ambient_power"] = st.slider("Ambient Strength", 0.0, 0.6, st.session_state.dh_settings["ambient_power"], 0.01)
    st.session_state.dh_settings["spot_lights"] = st.slider("Spotlights", 0, 4, st.session_state.dh_settings["spot_lights"])

    st.divider()
    st.header("Presets")
    def apply_preset(p):
        presets = {
            "Cozy Pink": dict(bg="#fff8fb", wall="#ffd1dc", wall_mode="Wainscot",
                              floor_mode="Herringbone", floor1="#e8d4c5", floor2="#f4eee9",
                              ambient="#ffd1dc", ambient_power=0.18),
            "Minimal Noir": dict(bg="#f3f3f3", wall="#e8e8e8", wall_mode="Panel",
                                 floor_mode="Checker", floor1="#1f1f1f", floor2="#f2f2f2",
                                 ambient="#d9d9d9", ambient_power=0.10),
            "Coastal Breeze": dict(bg="#f4feff", wall="#e9fbff", wall_mode="Stripes",
                                   floor_mode="Planks", floor1="#dbe6ea", floor2="#eaf2f5",
                                   ambient="#aee3ff", ambient_power=0.14),
        }
        st.session_state.dh_settings.update(presets[p])
    cA,cB,cC = st.columns(3)
    with cA:
        if st.button("💗 Cozy Pink", use_container_width=True): apply_preset("Cozy Pink")
    with cB:
        if st.button("⬛ Minimal Noir", use_container_width=True): apply_preset("Minimal Noir")
    with cC:
        if st.button("🌊 Coastal Breeze", use_container_width=True): apply_preset("Coastal Breeze")

    st.divider()
    st.header("Save / Load")
    # Export JSON
    schema = {
        "settings": st.session_state.dh_settings,
        "items": st.session_state.dh_items,
    }
    json_bytes = json.dumps(schema, indent=2).encode("utf-8")
    st.download_button("Download Scene (.json)", data=json_bytes, file_name="dreamhouse_scene.json", use_container_width=True)
    up = st.file_uploader("Import Scene (.json)", type=["json"])
    if up is not None:
        try:
            data = json.load(up)
            st.session_state.dh_settings.update(data.get("settings", {}))
            st.session_state.dh_items = data.get("items", [])
            st.success("Scene imported ✨")
        except Exception as e:
            st.error(f"Import failed: {e}")


st.markdown("## 🏡 Dreamhouse Designer")
left, right = st.columns([2,1], gap="large")

with right:
    st.markdown("### 🪑 Add Furniture")
    kind = st.selectbox("Type", list(CATALOG.keys()), index=0)
    # defaults per item
    c1_default, c2_default = DEFAULT_COLORS.get(kind, ("#ff4fb7","#ffe6f3"))
    c1 = st.color_picker("Color / Primary", c1_default)
    c2 = st.color_picker("Accent / Secondary", c2_default)
    iw = st.slider("Width", 80, 700, 340, 10)
    ih = st.slider("Height", 60, 400, 180, 10)
    irot = st.slider("Rotate°", -30.0, 30.0, 0.0, 0.5)
    extra = ""
    if kind == "Rug":
        extra = st.selectbox("Rug Pattern", ["Plain","Stripes","Check","Dots"], index=1)
    if st.button("➕ Add to Room", type="primary", use_container_width=True):
        st.session_state.dh_items.append(asdict(Item(
            kind=kind, x=CANVAS_W//2, y=int(CANVAS_H*0.7),
            w=iw, h=ih, rot=irot, c1=c1, c2=c2, extra=extra
        )))

    st.divider()
    st.markdown("### ✏️ Edit Selection")
    if not st.session_state.dh_items:
        st.caption("No items yet. Add something from the catalog.")
    else:
        idx = st.number_input("Item #", 1, len(st.session_state.dh_items), value=1, step=1) - 1
        item = st.session_state.dh_items[idx]
        st.write(f"**{item['kind']}**")
        colP1, colP2 = st.columns(2)
        with colP1:
            item["x"] = snap(st.slider("X", 0, CANVAS_W, item["x"], 1), st.session_state.dh_settings["snap"])
            item["y"] = snap(st.slider("Y", 0, CANVAS_H, item["y"], 1), st.session_state.dh_settings["snap"])
            item["rot"] = st.slider("Rotate° (sel)", -45.0, 45.0, float(item["rot"]), 0.5)
        with colP2:
            item["w"] = st.slider("Width (sel)", 40, 800, int(item["w"]), 5)
            item["h"] = st.slider("Height (sel)", 40, 500, int(item["h"]), 5)
        item["c1"] = st.color_picker("Primary / Shade", item["c1"])
        item["c2"] = st.color_picker("Secondary / Shadow", item["c2"])
        if item["kind"] == "Rug":
            item["extra"] = st.selectbox("Rug Pattern (sel)", ["Plain","Stripes","Check","Dots"],
                                         index=["Plain","Stripes","Check","Dots"].index(item.get("extra","Plain")))
        # actions
        cX,cY,cZ,cW = st.columns(4)
        with cX:
            if st.button("⬆ Layer Up", use_container_width=True) and idx < len(st.session_state.dh_items)-1:
                st.session_state.dh_items[idx], st.session_state.dh_items[idx+1] = st.session_state.dh_items[idx+1], st.session_state.dh_items[idx]
        with cY:
            if st.button("⬇ Layer Down", use_container_width=True) and idx > 0:
                st.session_state.dh_items[idx], st.session_state.dh_items[idx-1] = st.session_state.dh_items[idx-1], st.session_state.dh_items[idx]
        with cZ:
            if st.button("🧬 Duplicate", use_container_width=True):
                clone = dict(item); clone["x"] += 40; clone["y"] += 20
                st.session_state.dh_items.insert(idx+1, clone)
        with cW:
            if st.button("🗑️ Delete", use_container_width=True):
                st.session_state.dh_items.pop(idx)

        st.divider()
        st.markdown("### ✨ Auto Arrange")
        if st.button("Smart Layout (Gridline flow)", use_container_width=True):
            # place from back to front along golden-ratio rows
            rows = [int(CANVAS_H*0.62), int(CANVAS_H*0.70), int(CANVAS_H*0.78)]
            x_cursor = [160, 180, 200]
            for i, it in enumerate(st.session_state.dh_items):
                row = i % 3
                it["y"] = rows[row]
                it["x"] = x_cursor[row]
                x_cursor[row] += int(it["w"]*0.9) + 80

with left:
    #  Render room base
    settings = st.session_state.dh_settings
    room = render_room(settings["bg"], settings["wall"], settings["wall_mode"],
                       settings["floor_mode"], settings["floor1"], settings["floor2"], settings["skirting"])

    #  Architectural extras pass (shadow behind objects)
    scene = room.copy()
    # draw items in order
    for it in st.session_state.dh_items:
        kind,x,y,w,h,rot,c1,c2,extra = it["kind"], it["x"], it["y"], it["w"], it["h"], it["rot"], it["c1"], it["c2"], it.get("extra","")
        # render sprite
        if kind == "Rug":
            sprite = f_rug(w,h,c1,extra if extra in ("Stripes","Check","Dots") else "Plain")
        else:
            sprite = CATALOG[kind](w,h,c1,c2)
        # soft drop shadow
        shadow = sprite.copy().convert("L").point(lambda p:int(p*0.6))
        shadow = Image.merge("RGBA",(shadow,shadow,shadow, shadow))
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        scene = rotate_paste(scene, shadow, (x+16, y+10), rot)
        # item itself
        scene = rotate_paste(scene, sprite, (x, y), rot)

    #  Ambient light overlay
    if settings["ambient_power"] > 0:
        amb = blank()
        da = ImageDraw.Draw(amb, "RGBA")
        r,g,b = hex_to_rgb(settings["ambient"])
        # gentle top sunlight gradient
        for i,yy in enumerate(range(0, int(CANVAS_H*0.6))):
            alpha = int(settings["ambient_power"]*255 * (1 - yy/(CANVAS_H*0.6)))
            da.line([(0,yy),(CANVAS_W,yy)], fill=(r,g,b, alpha))
        # spotlights (ceiling)
        for i in range(settings["spot_lights"]):
            cx = int(CANVAS_W*(i+1)/(settings["spot_lights"]+1))
            cy = int(CANVAS_H*0.10)
            rad = int(CANVAS_H*0.66)
            grad = Image.new("L",(rad*2, rad*2),0)
            dg = ImageDraw.Draw(grad)
            for rr_ in range(rad,0,-6):
                val = int(settings["ambient_power"]*200 * rr_/rad)
                dg.ellipse((rad-rr_,rad-rr_,rad+rr_,rad+rr_), fill=val)
            cone = Image.merge("RGBA",(Image.new("L",grad.size, r),)*3 + (grad,))
            amb = rotate_paste(amb, cone, (cx, cy+int(rad*0.2)), 90)
        scene = Image.alpha_composite(scene, amb)

    #  Foreground guides (grid toggle)
    guides = blank()
    if settings["snap"]:
        dg = ImageDraw.Draw(guides, "RGBA")
        for x in range(0, CANVAS_W, GRID):
            dg.line((x,0,x,CANVAS_H), fill=(255,255,255,20))
        for y in range(0, CANVAS_H, GRID):
            dg.line((0,y,CANVAS_W,y), fill=(255,255,255,20))
    scene = Image.alpha_composite(scene, guides)

    #  Title chip
    chip = blank()
    dc = ImageDraw.Draw(chip, "RGBA")
    title = "Dreamhouse Designer"
    f1 = try_font(26)
    tw,th = dc.textbbox((0,0), title, font=f1)[2:]
    rr(dc, (14,14, 14+tw+20, 14+th+14), 999, fill=(255,255,255,160))
    dc.text((24,18), title, font=f1, fill=(20,20,20,220))
    scene = Image.alpha_composite(scene, chip)

    #  Preview
    st.image(scene, caption="Room Preview", use_container_width=True)

    #  Export
    colX, colY = st.columns(2)
    with colX:
        scale = st.select_slider("Export Scale", [1,2,3], value=2)
    with colY:
        fname = st.text_input("Filename", "dreamhouse.png")
    out = scene if scale==1 else scene.resize((CANVAS_W*scale, CANVAS_H*scale), Image.LANCZOS)
    buf = io.BytesIO(); out.save(buf, format="PNG")
    st.download_button("Download PNG", data=buf.getvalue(), file_name=fname, mime="image/png", use_container_width=True)
