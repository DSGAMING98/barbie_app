from __future__ import annotations

import io
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter


st.set_page_config(page_title="Party Playlist", page_icon="🎉", layout="wide")

# utils tiny
def try_font(size: int):
    """Return a truetype font if available; fall back to default."""
    for cand in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except Exception:
            pass
    return ImageFont.load_default()

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    s = h.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c*2 for c in s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

def contrast_text_for(h: str) -> str:
    r, g, b = hex_to_rgb(h)
    lum = 0.2126*r + 0.7152*g + 0.0722*b
    return "#000000" if lum > 160 else "#ffffff"

def rr(draw: ImageDraw.ImageDraw, box, radius: int, fill=None, outline=None, width: int = 1):
    try:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception:
        draw.rectangle(box, fill=fill, outline=outline, width=width)

def as_time(minutes: int, seconds: int) -> int:
    """Duration in seconds from m:s."""
    minutes = max(0, int(minutes))
    seconds = max(0, int(seconds))
    return minutes * 60 + seconds

def pretty_dur(total_seconds: int) -> str:
    m, s = divmod(int(max(0, total_seconds)), 60)
    return f"{m}:{s:02d}"

def safe_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


if "party_tracks" not in st.session_state:
    # track: dict(title, artist, link, mood, energy, bpm, key, duration, tag)
    st.session_state.party_tracks: List[Dict] = []

if "party_meta" not in st.session_state:
    st.session_state.party_meta = {
        "name": "Barbie Dream Party",
        "host": "Hosted by You",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "venue": "Dreamhouse",
        "emoji": "🎀",
        "primary": "#ff4fb7",
        "secondary": "#ffe6f3",
        "accent": "#ffffff",
    }


with st.sidebar:
    st.header("🎉 Event Details")
    st.session_state.party_meta["name"] = st.text_input("Party Name", st.session_state.party_meta["name"])
    st.session_state.party_meta["host"] = st.text_input("Host", st.session_state.party_meta["host"])
    st.session_state.party_meta["date"] = st.text_input("Date", st.session_state.party_meta["date"])
    st.session_state.party_meta["venue"] = st.text_input("Venue", st.session_state.party_meta["venue"])
    st.session_state.party_meta["emoji"] = st.text_input("Vibe Emoji", st.session_state.party_meta["emoji"][:2] if st.session_state.party_meta["emoji"] else "🎀")

    st.header("🎨 Palette")
    c1, c2, c3 = st.columns(3)
    with c1: st.session_state.party_meta["primary"] = st.color_picker("Primary", st.session_state.party_meta["primary"])
    with c2: st.session_state.party_meta["secondary"] = st.color_picker("Secondary", st.session_state.party_meta["secondary"])
    with c3: st.session_state.party_meta["accent"] = st.color_picker("Accent", st.session_state.party_meta["accent"])

    st.header("⬇ Export")
    export_scale = st.select_slider("Cover/Poster Scale", options=[1, 2, 3], value=2)


meta = st.session_state.party_meta
PRIMARY, SECONDARY, ACCENT = meta["primary"], meta["secondary"], meta["accent"]

st.markdown(
    f"""
    <div style="padding:12px 0 4px 0">
      <h2 style="margin:0">{meta['emoji']} {meta['name']}</h2>
      <p style="margin:0;color:#444">{meta['host']} · {meta['date']} · {meta['venue']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown("### ➕ Add Track")

colA, colB, colC, colD = st.columns([3,3,3,2])
with colA:
    title = st.text_input("Title", placeholder="e.g., Pink Fantasy")
with colB:
    artist = st.text_input("Artist", placeholder="e.g., DJ Dream")
with colC:
    link = st.text_input("Link (Spotify/YouTube/etc.)", placeholder="https://...")
with colD:
    mood = st.selectbox("Mood", ["Warmup", "Pop", "Dance/EDM", "Bollywood", "Retro", "Peak", "Afterglow", "Chill"], index=1)

colE, colF, colG, colH, colI = st.columns([2,2,2,2,2])
with colE:
    energy = st.slider("Energy (0–10)", 0, 10, 7)
with colF:
    bpm = st.number_input("BPM (optional)", min_value=0, max_value=300, value=0, step=1)
with colG:
    camelot_key = st.selectbox("Key (opt.)", ["", "1A","2A","3A","4A","5A","6A","7A","8A","9A","10A","11A","12A","1B","2B","3B","4B","5B","6B","7B","8B","9B","10B","11B","12B"], index=0)
with colH:
    dur_m = st.number_input("Min", min_value=0, max_value=30, value=3, step=1)
with colI:
    dur_s = st.number_input("Sec", min_value=0, max_value=59, value=15, step=5)

colJ, colK = st.columns([2,1])
with colJ:
    tag = st.selectbox("Tag", ["Clean", "Explicit", "Remix", "Mashup", "Live"], index=0)
with colK:
    if st.button("Add", type="primary", use_container_width=True):
        if title.strip():
            st.session_state.party_tracks.append({
                "title": title.strip(),
                "artist": artist.strip() or "Unknown",
                "link": link.strip(),
                "mood": mood,
                "energy": int(energy),
                "bpm": int(bpm) if bpm else None,
                "key": camelot_key or None,
                "duration": as_time(dur_m, dur_s),
                "tag": tag,
            })
            st.success("Added! 💿")
        else:
            st.warning("Title required.")

st.divider()


st.markdown("### One-Click Mood Packs")
packs_col1, packs_col2, packs_col3 = st.columns(3)

SEED_PACKS: Dict[str, List[Dict]] = {
    "Warmup Pop": [
        {"title":"Gloss Up", "artist":"Lou Lou", "mood":"Warmup", "energy":4, "bpm":100, "key":"8B", "duration":as_time(3,5), "tag":"Clean", "link":""},
        {"title":"Candy Heart", "artist":"Nova", "mood":"Pop", "energy":5, "bpm":102, "key":"9B", "duration":as_time(3,12), "tag":"Clean", "link":""},
        {"title":"Dreamlane", "artist":"Ariana Q", "mood":"Pop", "energy":5, "bpm":104, "key":"9A", "duration":as_time(3,35), "tag":"Clean", "link":""},
    ],
    "EDM Peak": [
        {"title":"Neon Drip", "artist":"K-Zero", "mood":"Dance/EDM", "energy":9, "bpm":128, "key":"8A", "duration":as_time(3,45), "tag":"Remix", "link":""},
        {"title":"Starlit Rush", "artist":"Minae", "mood":"Dance/EDM", "energy":9, "bpm":126, "key":"9A", "duration":as_time(3,20), "tag":"Remix", "link":""},
        {"title":"Pink Thunder", "artist":"V!BE", "mood":"Peak", "energy":10, "bpm":130, "key":"8B", "duration":as_time(2,58), "tag":"Mashup", "link":""},
    ],
    "Bollywood Sparkle": [
        {"title":"Dil Ki Rani", "artist":"Arav & Siya", "mood":"Bollywood", "energy":8, "bpm":126, "key":"10A", "duration":as_time(3,18), "tag":"Remix", "link":""},
        {"title":"Rangeen Raat", "artist":"Maya Beats", "mood":"Bollywood", "energy":7, "bpm":122, "key":"9B", "duration":as_time(3,40), "tag":"Clean", "link":""},
        {"title":"Jhilmil", "artist":"DJ Aman", "mood":"Bollywood", "energy":8, "bpm":128, "key":"9A", "duration":as_time(2,54), "tag":"Remix", "link":""},
    ],
    "Retro Cute": [
        {"title":"Disco Pink", "artist":"The Grooves", "mood":"Retro", "energy":6, "bpm":118, "key":"7A", "duration":as_time(3,22), "tag":"Clean", "link":""},
        {"title":"Vinyl Crush", "artist":"Jasmine J", "mood":"Retro", "energy":6, "bpm":115, "key":"6B", "duration":as_time(3,10), "tag":"Clean", "link":""},
        {"title":"Roller Rink", "artist":"Cass & Co", "mood":"Retro", "energy":7, "bpm":120, "key":"8B", "duration":as_time(3,5), "tag":"Clean", "link":""},
    ],
    "Afterglow Chill": [
        {"title":"Soft Moon", "artist":"Cloud 9", "mood":"Afterglow", "energy":4, "bpm":100, "key":"4B", "duration":as_time(3,12), "tag":"Clean", "link":""},
        {"title":"Glow Down", "artist":"Tess", "mood":"Chill", "energy":3, "bpm":94, "key":"3A", "duration":as_time(3,44), "tag":"Clean", "link":""},
        {"title":"Cotton Candy Sky", "artist":"Nae", "mood":"Chill", "energy":3, "bpm":92, "key":"3B", "duration":as_time(3,8), "tag":"Clean", "link":""},
    ],
}

def add_pack(name: str):
    for t in SEED_PACKS.get(name, []):
        st.session_state.party_tracks.append(t.copy())

with packs_col1:
    if st.button("💗 Warmup Pop", use_container_width=True): add_pack("Warmup Pop")
    if st.button("🪩 Retro Cute", use_container_width=True): add_pack("Retro Cute")
with packs_col2:
    if st.button("⚡ EDM Peak", use_container_width=True): add_pack("EDM Peak")
    if st.button("🌙 Afterglow Chill", use_container_width=True): add_pack("Afterglow Chill")
with packs_col3:
    if st.button("💃 Bollywood Sparkle", use_container_width=True): add_pack("Bollywood Sparkle")

st.divider()


st.markdown("### 📝 Your Playlist")

def tracks_df() -> pd.DataFrame:
    df = pd.DataFrame(st.session_state.party_tracks)
    if df.empty:
        return pd.DataFrame(columns=["title","artist","mood","energy","bpm","key","duration","tag","link"])
    df = df[["title","artist","mood","energy","bpm","key","duration","tag","link"]]
    df["length"] = df["duration"].apply(pretty_dur)
    return df

df = tracks_df()
if df.empty:
    st.caption("No tracks yet — add songs above or drop in a mood pack!")
else:
    edited = st.data_editor(
        df.drop(columns=["duration"]),  # show friendly "length" not raw seconds
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "title": st.column_config.TextColumn("Title", width="medium"),
            "artist": st.column_config.TextColumn("Artist", width="medium"),
            "mood": st.column_config.SelectboxColumn("Mood", options=["Warmup","Pop","Dance/EDM","Bollywood","Retro","Peak","Afterglow","Chill"]),
            "energy": st.column_config.NumberColumn("Energy", min_value=0, max_value=10, step=1),
            "bpm": st.column_config.NumberColumn("BPM", min_value=0, max_value=300, step=1),
            "key": st.column_config.TextColumn("Key"),
            "tag": st.column_config.SelectboxColumn("Tag", options=["Clean","Explicit","Remix","Mashup","Live"]),
            "link": st.column_config.LinkColumn("Link"),
            "length": st.column_config.TextColumn("Length"),
        },
        key="editor_tracks",
    )
    # sync back to session (preserve raw duration seconds via old df (hash to remind my dumb brain))
    if isinstance(edited, pd.DataFrame):
        merged = edited.copy()
        merged["duration"] = df["duration"].values  # keep original seconds
        st.session_state.party_tracks = merged.to_dict(orient="records")

colAA, colBB, colCC, colDD = st.columns([1,1,1,2])
with colAA:
    if st.button("🔀 Shuffle", use_container_width=True):
        random.shuffle(st.session_state.party_tracks)
with colBB:
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.party_tracks = []
with colCC:
    if st.button("🧠 Smart Order", type="primary", use_container_width=True):
        # warmup -> build -> peak -> afterglow based on energy & mood
        tr = st.session_state.party_tracks
        def weight(t):
            mood_boost = {
                "Warmup": -2, "Pop": 0, "Retro": -1, "Dance/EDM": +1, "Bollywood": +1,
                "Peak": +3, "Afterglow": -2, "Chill": -3
            }.get(t.get("mood",""), 0)
            return (t.get("energy",5) or 5) + mood_boost
        ordered = sorted(tr, key=weight)
        # gently “arc” energies (low→high→low)
        n = len(ordered)
        if n > 3:
            left = ordered[: n//2]
            right = list(reversed(ordered[n//2:]))
            st.session_state.party_tracks = left + right
        else:
            st.session_state.party_tracks = ordered
with colDD:
    if st.button("🎊 Confetti", use_container_width=True):
        st.balloons()

st.divider()


st.markdown("###  DJ Timeline & Energy Curve")

if not st.session_state.party_tracks:
    st.caption("Add a few tracks to see the energy and timeline")
else:
    # Build timeline with start times
    start_time_str = st.text_input("Set Start Time (HH:MM, 24h)", "21:00")
    try:
        base_time = datetime.strptime(start_time_str.strip(), "%H:%M")
    except Exception:
        base_time = datetime.strptime("21:00", "%H:%M")

    # compute schedule
    times = []
    t_cursor = base_time
    for t in st.session_state.party_tracks:
        times.append(t_cursor.strftime("%H:%M"))
        t_cursor += timedelta(seconds=int(t.get("duration", 180)))

    # energy curve
    energies = [int(t.get("energy", 5)) for t in st.session_state.party_tracks]
    curve = pd.DataFrame({"Energy": energies})
    st.line_chart(curve, height=180)

    # show compact schedule table
    sched = pd.DataFrame({
        "#": list(range(1, len(st.session_state.party_tracks)+1)),
        "Time": times,
        "Title": [t["title"] for t in st.session_state.party_tracks],
        "Artist": [t["artist"] for t in st.session_state.party_tracks],
        "BPM": [t.get("bpm") or "" for t in st.session_state.party_tracks],
        "Key": [t.get("key") or "" for t in st.session_state.party_tracks],
        "Len": [pretty_dur(t.get("duration", 0)) for t in st.session_state.party_tracks],
        "Tag": [t.get("tag","") for t in st.session_state.party_tracks],
    })
    st.dataframe(sched, use_container_width=True, hide_index=True)

    # transition tips
    st.markdown("#### Transition Tips")
    tips = []
    for i in range(len(st.session_state.party_tracks)-1):
        a = st.session_state.party_tracks[i]
        b = st.session_state.party_tracks[i+1]
        tip = []
        if a.get("bpm") and b.get("bpm"):
            diff = abs(int(a["bpm"]) - int(b["bpm"]))
            if diff <= 2:
                tip.append("tempo match ✅")
            elif diff <= 6:
                tip.append("tempo nudge")
            else:
                tip.append("half-time/double-time swap")
        if a.get("key") and b.get("key") and a["key"] == b["key"]:
            tip.append("same key (smooth)")
        if a.get("energy") is not None and b.get("energy") is not None:
            if b["energy"] < a["energy"] - 2:
                tip.append("energy dip — use FX")
            elif b["energy"] > a["energy"] + 2:
                tip.append("big riser!")
        tips.append(f"{i+1} → {i+2}: " + (", ".join(tip) if tip else "freestyle"))
    st.write("\n".join([f"- {t}" for t in tips]) or "Looks smooth all the way ✨")

st.divider()


st.markdown("### 🖼️ Generate Party Cover")

def render_cover(size: Tuple[int,int]=(1080,1080), bg1: str = SECONDARY, bg2: str = PRIMARY, title: str = "", subtitle: str = "", sticker: str = "GLOW") -> Image.Image:
    W,H = size
    img = Image.new("RGBA", size, (255,255,255,0))
    d = ImageDraw.Draw(img, "RGBA")


    r1,g1,b1 = hex_to_rgb(bg1); r2,g2,b2 = hex_to_rgb(bg2)
    for y in range(H):
        t = y/(H-1)
        r = int(r1*(1-t) + r2*t); g = int(g1*(1-t) + g2*t); b = int(b1*(1-t) + b2*t)
        d.line([(0,y),(W,y)], fill=(r,g,b,255))


    rr(d, (60, 80, W-60, H-80), 40, fill=(255,255,255,90), outline=(255,255,255,180), width=2)


    rng = random.Random(42)
    for _ in range(150):
        x = rng.randint(60, W-60)
        y = rng.randint(80, H-80)
        r = rng.randint(2,6)
        col = (255,255,255, rng.randint(60,150))
        d.ellipse((x-r,y-r,x+r,y+r), fill=col)


    f1 = try_font(82)
    f2 = try_font(28)
    tcolor = (10,10,10,230)
    # center title
    tw, th = d.textbbox((0,0), title, font=f1)[2:]
    d.text(((W - tw)//2, int(H*0.28)), title, font=f1, fill=tcolor)
    # sub
    sw, sh = d.textbbox((0,0), subtitle, font=f2)[2:]
    d.text(((W - sw)//2, int(H*0.28) + th + 16), subtitle, font=f2, fill=(20,20,20,200))


    if sticker.strip():
        s = sticker.strip().upper()[:10]
        f3 = try_font(22)
        cw, ch = d.textbbox((0,0), s, font=f3)[2:]
        chip_w = cw + 26
        rr(d, (W - 60 - chip_w, 96, W - 60, 96 + ch + 18), 999, fill=hex_to_rgb(PRIMARY)+(255,))
        d.text((W - 60 - chip_w + 13, 96 + 9), s, font=f3, fill=hex_to_rgb(contrast_text_for(PRIMARY))+(255,))

    # footer
    f3 = try_font(22)
    info = f"{meta['host']} • {meta['date']} • {meta['venue']}"
    iw, ih = d.textbbox((0,0), info, font=f3)[2:]
    d.text(((W - iw)//2, H - ih - 48), info, font=f3, fill=(30,30,30,220))

    return img.convert("RGB")

cover = render_cover(
    size=(1080,1080),
    bg1=SECONDARY,
    bg2=PRIMARY,
    title=f"{meta['emoji']} {meta['name']}",
    subtitle="official playlist",
    sticker="party"
)
st.image(cover, caption="Cover Art Preview (1080×1080)", use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    buf = io.BytesIO()
    out = cover if export_scale == 1 else cover.resize((cover.width*export_scale, cover.height*export_scale), Image.LANCZOS)
    out.save(buf, format="PNG")
    st.download_button("Download Cover (PNG)", data=buf.getvalue(), file_name="party_cover.png", mime="image/png", use_container_width=True)

with c2:

    poster = render_cover(size=(1600, 1000), bg1=SECONDARY, bg2=PRIMARY, title=f"{meta['emoji']} {meta['name']}", subtitle="tonight's soundtrack", sticker="vibes")
    pbuf = io.BytesIO()
    pout = poster if export_scale == 1 else poster.resize((poster.width*export_scale, poster.height*export_scale), Image.LANCZOS)
    pout.save(pbuf, format="PNG")
    st.download_button("Download Poster (PNG)", data=pbuf.getvalue(), file_name="party_poster.png", mime="image/png", use_container_width=True)

st.divider()


st.markdown("###  Export Playlist")

if not st.session_state.party_tracks:
    st.caption("Add tracks to enable exports.")
else:
    # CSV
    csv_df = pd.DataFrame(st.session_state.party_tracks)
    csv_df["length"] = csv_df["duration"].apply(pretty_dur)
    csv_buf = io.StringIO()
    csv_df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", data=csv_buf.getvalue().encode("utf-8"), file_name="party_playlist.csv", mime="text/csv", use_container_width=True)


    lines = ["#EXTM3U"]
    for t in st.session_state.party_tracks:
        duration = t.get("duration", 0)
        artist = t.get("artist","Unknown")
        title = t.get("title","Untitled")
        lines.append(f"#EXTINF:{int(duration)},{artist} - {title}")
        lines.append(t.get("link","") or f"{artist} - {title}")
    m3u_buf = "\n".join(lines).encode("utf-8")
    st.download_button("Download M3U", data=m3u_buf, file_name="party_playlist.m3u", mime="audio/x-mpegurl", use_container_width=True)

st.divider()


st.markdown("### Totals & Phases")

if st.session_state.party_tracks:
    total_sec = sum(int(t.get("duration", 0)) for t in st.session_state.party_tracks)
    total_str = pretty_dur(total_sec)
    avg_bpm = np.mean([t["bpm"] for t in st.session_state.party_tracks if t.get("bpm")]) if any(t.get("bpm") for t in st.session_state.party_tracks) else None
    st.write(f"**Total runtime:** {total_str}" + (f" · **Avg BPM:** {avg_bpm:.0f}" if avg_bpm else ""))


    energies = np.array([int(t.get("energy",5)) for t in st.session_state.party_tracks], dtype=int)
    q = np.quantile(energies, [0.25, 0.5, 0.75]) if len(energies) >= 4 else [4,6,8]
    phases = {"Warmup": [], "Build": [], "Peak": [], "Afterglow": []}
    for t in st.session_state.party_tracks:
        e = int(t.get("energy",5))
        if e <= q[0]: phases["Warmup"].append(t)
        elif e <= q[1]: phases["Build"].append(t)
        elif e <= q[2]: phases["Peak"].append(t)
        else: phases["Afterglow"].append(t)

    col1, col2, col3, col4 = st.columns(4)
    for (name, tracks), col in zip(phases.items(), [col1,col2,col3,col4]):
        with col:
            st.write(f"**{name}**")
            if tracks:
                st.write("\n".join([f"- {t['title']} — {t['artist']}" for t in tracks]))
            else:
                st.caption("—")


