from __future__ import annotations

import io, math, random, csv
from datetime import date, timedelta
from typing import List, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont
import streamlit as st


st.set_page_config(page_title="Goals & Vision Board", page_icon="✨", layout="wide")


def try_font(size: int):
    for cand in ("arial.ttf", "DejaVuSans.ttf"):
        try: return ImageFont.truetype(cand, size)
        except Exception: pass
    return ImageFont.load_default()

def hex_to_rgb(h: str) -> Tuple[int,int,int]:
    s = h.strip().lstrip("#")
    if len(s)==3: s="".join(c*2 for c in s)
    return int(s[0:2],16), int(s[2:4],16), int(s[4:6],16)

def contrast_text_for(h: str) -> str:
    r,g,b = hex_to_rgb(h)
    lum = 0.2126*r + 0.7152*g + 0.0722*b
    return "#000000" if lum > 165 else "#ffffff"

def rr(draw: ImageDraw.ImageDraw, box, radius: int, fill=None, outline=None, width: int = 1):
    try: draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception: draw.rectangle(box, fill=fill, outline=outline, width=width)

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


if "goals" not in st.session_state:
    st.session_state.goals = []
if "habit_log" not in st.session_state:
    # last 60 days of 3 habits
    today = date.today()
    st.session_state.habit_log = {
        "Move": {today - timedelta(d): False for d in range(60)},
        "Focus": {today - timedelta(d): False for d in range(60)},
        "Recharge": {today - timedelta(d): False for d in range(60)},
    }

#palettes
DEFAULT_PALETTES = [
    {"name": "Barbie Classic", "primary": "#ff4fb7", "secondary": "#ffe6f3", "accent": "#ffffff"},
    {"name": "Dreamhouse Sunset", "primary": "#ff7aa9", "secondary": "#ffd1dc", "accent": "#fff4fa"},
    {"name": "Midnight Glam", "primary": "#1f1f1f", "secondary": "#ff4fb7", "accent": "#f5f5f5"},
    {"name": "Ocean Glow", "primary": "#00d1ff", "secondary": "#e9fbff", "accent": "#ffffff"},
]

# sync from Home if set
palette_name = st.session_state.get("palette_name", DEFAULT_PALETTES[0]["name"])
palette = next((p for p in DEFAULT_PALETTES if p["name"] == palette_name), DEFAULT_PALETTES[0])
PRIMARY, SECONDARY, ACCENT = palette["primary"], palette["secondary"], palette["accent"]

#  sidebar controls
with st.sidebar:
    st.header("Board Settings")
    palette_name = st.selectbox("Palette", [p["name"] for p in DEFAULT_PALETTES], index=[p["name"] for p in DEFAULT_PALETTES].index(palette_name))
    palette = next(p for p in DEFAULT_PALETTES if p["name"] == palette_name)
    PRIMARY, SECONDARY, ACCENT = palette["primary"], palette["secondary"], palette["accent"]
    bg = st.color_picker("Background", SECONDARY)
    grid_cols = st.slider("Grid Columns", 2, 5, 3)
    tile_round = st.slider("Tile Roundness", 6, 40, 18)
    gap = st.slider("Tile Gap (px)", 8, 40, 16)
    quote = st.text_input("Big Quote", "You can be anything.")
    subtext = st.text_input("Subtitle", "soft life era, main character energy ✨")
    sticker = st.text_input("Sticker/Word", "GLOW")
    watermark = st.toggle("Add date watermark", True)

    st.divider()
    st.header("Upload Images")
    uploads = st.file_uploader("Add mood pics (PNG/JPG)", accept_multiple_files=True, type=["png","jpg","jpeg"])

    st.divider()
    st.header("Export")
    board_w = st.select_slider("Board Width", options=[900, 1200, 1600], value=1200)
    export_scale = st.select_slider("Export Scale", options=[1,2,3], value=2)

#  Goals Manager
st.markdown("###  Goals")
cols = st.columns([3,2,1,2,1,1])
with cols[0]:
    new_title = st.text_input("Goal", placeholder="Launch capsule collection…")
with cols[1]:
    new_area = st.selectbox("Area", ["Career","Wealth","Health","Style","Love","Fun"], index=0)
with cols[2]:
    new_emoji = st.text_input("Emoji", value="💖")
with cols[3]:
    new_due = st.date_input("Due", value=date.today()+timedelta(days=30))
with cols[4]:
    new_prog = st.slider("%", 0, 100, 20)
with cols[5]:
    if st.button("Add", type="primary", use_container_width=True, help="Add goal"):
        if new_title.strip():
            st.session_state.goals.append({
                "title": new_title.strip(),
                "area": new_area,
                "emoji": new_emoji.strip()[:2] or "✨",
                "due": new_due.isoformat(),
                "progress": int(new_prog),
            })

# Goals table-y vibe
if st.session_state.goals:
    for i, g in enumerate(list(st.session_state.goals)):
        c = st.columns([0.5, 4, 2, 2, 2, 1])
        with c[0]:
            st.write(g["emoji"])
        with c[1]:
            st.write(f"**{g['title']}**")
            st.progress(g["progress"] / 100)
        with c[2]:
            st.caption(g["area"])
        with c[3]:
            st.caption(f"Due: {g['due']}")
        with c[4]:
            newv = st.slider(f"Update {i}", 0, 100, g["progress"], key=f"prog_{i}")
            g["progress"] = newv
        with c[5]:
            if st.button("✖", key=f"del_{i}"):
                st.session_state.goals.pop(i)
                st.rerun()
else:
    st.caption("no goals yet — add one above")

# Habit mini tracker
st.markdown("### Habit Streaks (last 60 days)")
hab_cols = st.columns(3)
today = date.today()
for hname, col in zip(st.session_state.habit_log.keys(), hab_cols):
    with col:
        st.write(f"**{hname}**")
        row = st.columns(10)
        # mark today quickly
        did_today = st.toggle("done today", value=st.session_state.habit_log[hname][today], key=f"{hname}_today")
        st.session_state.habit_log[hname][today] = did_today
        # streak calc
        d = today; streak = 0
        while d in st.session_state.habit_log[hname] and st.session_state.habit_log[hname][d]:
            streak += 1; d -= timedelta(days=1)
        st.caption(f"🔥 {streak} day streak")
        # tiny heat grid
        days = list(reversed(sorted(st.session_state.habit_log[hname].keys())))[0:60]
        blocks = ""
        for idx, dd in enumerate(reversed(days)):
            on = st.session_state.habit_log[hname][dd]
            colr = PRIMARY if on else "#e9e9ef"
            blocks += f"<span style='display:inline-block;width:10px;height:10px;border-radius:3px;margin:2px;background:{colr}'></span>"
            if (idx+1) % 20 == 0: blocks += "<br/>"
        st.markdown(blocks, unsafe_allow_html=True)

st.divider()

# Vision board preview builder
st.markdown("### Vision Board")

# layout: simple Masonry-ish grid -> deterministic order
thumb_cols = st.columns(grid_cols)
images: List[Image.Image] = []
if uploads:
    for i, up in enumerate(uploads):
        try:
            img = Image.open(up).convert("RGB")
            images.append(img)
            with thumb_cols[i % grid_cols]:
                st.image(img, use_container_width=True)
        except Exception:
            st.warning(f"Could not read {up.name}")

#  Board render function
def render_board(width: int, palette: Dict, bg_hex: str, cols: int, round_px: int, gap_px: int,
                 imgs: List[Image.Image], big_quote: str, sub: str, sticker: str,
                 goals: List[Dict], add_date: bool) -> Image.Image:
    # board dims
    W = width
    H = int(width * 0.65)  # cinematic banner vibe
    board = Image.new("RGBA", (W, H), (255,255,255,0))
    d = ImageDraw.Draw(board, "RGBA")

    # gradient bg from palette + chosen bg
    p = palette["primary"]; s = bg_hex
    r1,g1,b1 = hex_to_rgb(s); r2,g2,b2 = hex_to_rgb(p)
    for y in range(H):
        t = y/(H-1)
        r = int(r1*(1-t) + r2*t); g = int(g1*(1-t) + g2*t); b = int(b1*(1-t) + b2*t)
        d.line([(0,y),(W,y)], fill=(r,g,b,255))

    # tile grid area
    pad = 28
    grid_top = 100
    grid_h = H - grid_top - 110
    grid_w = W - pad*2
    cell_w = (grid_w - gap_px*(cols-1)) // cols

    # draw image tiles
    if imgs:
        y_cursor = grid_top
        i = 0
        rows = math.ceil(len(imgs)/cols)
        row_h = (grid_h - gap_px*(rows-1)) // max(1, rows)
        for r in range(rows):
            x_cursor = pad
            for c in range(cols):
                if i >= len(imgs): break
                tile = imgs[i].copy()
                tile.thumbnail((cell_w, row_h))
                # place with rounded mask
                w,h = tile.size
                mask = Image.new("L", (w,h), 0); dm = ImageDraw.Draw(mask)
                rr(dm, (0,0,w,h), round_px, fill=255)
                board.paste(tile, (x_cursor, y_cursor), mask)
                x_cursor += cell_w + gap_px
                i += 1
            y_cursor += row_h + gap_px

    # top header glass
    header_h = 78
    d.rounded_rectangle((pad, 22, W-pad, 22+header_h), radius=22, fill=(255,255,255,80), outline=(255,255,255,160), width=1)

    # big quote + sub
    f1 = try_font(44); f2 = try_font(20)
    q_color = contrast_text_for("#ffffff" if hex_to_rgb(palette["primary"]) < hex_to_rgb("#888888") else palette["primary"])
    d.text((pad+16, 28), big_quote, fill=(0,0,0,230), font=f1)
    d.text((pad+18, 28+48), sub, fill=(20,20,20,200), font=f2)

    # sticker chip
    if sticker.strip():
        f3 = try_font(18)
        tw, th = d.textbbox((0,0), sticker, font=f3)[2:]
        chip_w = tw + 22
        rr(d, (W - pad - chip_w, 32, W - pad, 32 + th + 14), 999, fill=hex_to_rgb(palette["primary"])+ (255,))
        d.text((W - pad - chip_w + 11, 39), sticker.upper(), fill=hex_to_rgb(contrast_text_for(palette["primary"]))+(255,), font=f3)

    # goals badges at bottom
    if goals:
        gx = pad; gy = H - 70
        for g in goals[:6]:
            tag = f"{g['emoji']} {g['title']} · {g['progress']}%"
            f = try_font(18)
            tw, th = d.textbbox((0,0), tag, font=f)[2:]
            box = (gx, gy, gx+tw+22, gy+th+12)
            rr(d, box, 14, fill=(255,255,255,200))
            d.text((gx+11, gy+6), tag, fill=(10,10,10,230), font=f)
            gx += tw + 28
            if gx > W - 260:  # wrap
                gx = pad; gy -= th + 18

    # watermark
    if add_date:
        f = try_font(14)
        txt = date.today().strftime("%b %d, %Y")
        tw, th = d.textbbox((0,0), txt, font=f)[2:]
        d.text((W - tw - 16, H - th - 12), txt, fill=(30,30,30,160), font=f)

    return board.convert("RGB")

# affirmation
def affirmation(goals: List[Dict]) -> str:
    if not goals:
        return "I’m glowing up daily — soft, steady, unstoppable."
    vibes = []
    for g in goals[:4]:
        area = g["area"]
        if area == "Career": vibes.append("I create, I lead, I win.")
        if area == "Wealth": vibes.append("Money flows to me easily.")
        if area == "Health": vibes.append("My body is strong & kind.")
        if area == "Style":  vibes.append("I’m the blueprint.")
        if area == "Love":   vibes.append("I give and receive big love.")
        if area == "Fun":    vibes.append("Joy finds me everywhere.")
    return " ".join(vibes)

# left: live board; right: actions
left, right = st.columns([3,2], gap="large")

with left:
    board = render_board(
        width=board_w, palette=palette, bg_hex=bg, cols=grid_cols, round_px=tile_round, gap_px=gap,
        imgs=images, big_quote=quote, sub=subtext, sticker=sticker,
        goals=st.session_state.goals, add_date=watermark
    )
    st.image(board, caption="Vision Board Preview", use_container_width=True)

with right:
    st.markdown("#### ✨ Daily Affirmation")
    st.info(affirmation(st.session_state.goals))

    # export PNG
    buf = io.BytesIO()
    export_img = board if export_scale == 1 else board.resize((board.width*export_scale, board.height*export_scale), Image.LANCZOS)
    export_img.save(buf, format="PNG")
    st.download_button("Download Board (PNG)", data=buf.getvalue(), file_name="vision_board.png", mime="image/png", use_container_width=True)

    # export goals CSV
    if st.session_state.goals:
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=["emoji","title","area","progress","due"])
        writer.writeheader()
        for g in st.session_state.goals:
            writer.writerow(g)
        st.download_button("Export Goals (CSV)", data=csv_buf.getvalue().encode("utf-8"), file_name="goals.csv", mime="text/csv", use_container_width=True)

    st.markdown("---")
    st.caption("Tip: upload 6–12 images for a balanced grid. Tweak columns + roundness for the vibe.")
