import streamlit as st

# minimal “always works” helpers
DEFAULT_PALETTES = [
    {"name": "Barbie Classic", "primary": "#ff4fb7", "secondary": "#ffe6f3", "accent": "#ffffff"},
    {"name": "Dreamhouse Sunset", "primary": "#ff7aa9", "secondary": "#ffd1dc", "accent": "#fff4fa"},
    {"name": "Midnight Glam", "primary": "#1f1f1f", "secondary": "#ff4fb7", "accent": "#f5f5f5"},
]

def inject_css():
    st.markdown("""
    <style>
      :root{
        --p:#ff4fb7; --s:#ffe6f3; --a:#ffffff;
        --text:#1f1f1f; --muted:#6b6b6b; --radius:16px;
      }
      html,body,[data-testid="stApp"]{background:linear-gradient(180deg,#fff,#fff7fc 50%,#ffe6f3 120%);}
      .block-container{padding-top:1.2rem;}
      .section-header h2{
        margin:0 0 .25rem 0; font-size:1.6rem; line-height:1.1;
        background:linear-gradient(90deg,var(--p),#ff87c5);
        -webkit-background-clip:text; background-clip:text; color:transparent; font-weight:800;
      }
      .section-header .sub{color:var(--muted); margin:0 0 .75rem 0;}
      .card{border-radius:16px; padding:14px 16px; border:1px solid rgba(0,0,0,.06); background:#fff; margin-bottom:10px;}
      .hero-wrap{display:flex; gap:22px; align-items:stretch; background:linear-gradient(135deg, var(--s), #fff);
        padding:18px; border-radius:24px; border:1px solid rgba(0,0,0,.06);}
      .hero-left{flex:1 1 50%; display:flex; flex-direction:column; gap:8px;}
      .app-badge{display:inline-block; font-size:.8rem; padding:4px 10px; border-radius:999px; background: var(--p); color:#fff; font-weight:700;}
      .hero-title{font-size:2.2rem; margin:.2rem 0; line-height:1.05;}
      .hero-sub{color:var(--muted); margin:0;}
      .hero-right{flex:1 1 50%; display:flex; align-items:center; justify-content:center;
        background: conic-gradient(from 200deg at 50% 50%, #fff0f8, var(--s)); border-radius: 18px;}
      .hero-art{position:relative; width:100%; height:220px; border-radius:16px;
        background: radial-gradient(120px 90px at 40% 60%, var(--p), transparent),
                   radial-gradient(120px 90px at 70% 40%, #ff87c5, transparent),
                   radial-gradient(80px 60px at 55% 50%, var(--a), transparent);
        border:1px dashed rgba(0,0,0,.08);}
      .footer{margin-top:18px; padding:10px; text-align:center; color:var(--muted); font-size:.9rem;}
    </style>
    """, unsafe_allow_html=True)

def set_vars(p, s, a):
    st.markdown(f"""
    <style>
      :root {{ --p:{p}; --s:{s}; --a:{a}; }}
    </style>
    """, unsafe_allow_html=True)

# page setup
st.set_page_config(page_title="Barbie App — Home", page_icon="🩷", layout="wide")
inject_css()
st.markdown('<div style="height:6px;border-radius:999px;background:linear-gradient(90deg,#ff4fb7,#ffe6f3);margin:4px 0 12px 0;"></div>',
            unsafe_allow_html=True)

# keep palette in session
names = [p["name"] for p in DEFAULT_PALETTES]
if "palette_name" not in st.session_state:
    st.session_state["palette_name"] = names[0]

st.markdown("""
<div class="hero-wrap">
  <div class="hero-left">
    <div class="app-badge">v0.1.0</div>
    <h1 class="hero-title">Barbie Studio</h1>
    <p class="hero-sub">Create looks, design rooms, set goals — all in one place.</p>
  </div>
  <div class="hero-right"><div class="hero-art"></div></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-header"><h2>Theme</h2><p class="sub">Pick your palette — the app updates live.</p></div>', unsafe_allow_html=True)

choice = st.segmented_control("Palette", names, default=st.session_state["palette_name"], key="palette_control")
if choice != st.session_state["palette_name"]:
    st.session_state["palette_name"] = choice

selected = next(p for p in DEFAULT_PALETTES if p["name"] == st.session_state["palette_name"])
set_vars(selected["primary"], selected["secondary"], selected["accent"])

c1, c2, c3 = st.columns(3)
for col, title, val in ((c1, "Primary", selected["primary"]), (c2, "Secondary", selected["secondary"]), (c3, "Accent", selected["accent"])):
    with col:
        st.markdown(f"""
        <div class="card" style="border-color:{val}">
          <div style="font-weight:700; margin-bottom:6px;">{title}</div>
          <div style="color:#6b6b6b;">{val}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="section-header"><h2>Explore</h2><p class="sub">Jump into a feature.</p></div>', unsafe_allow_html=True)
cols = st.columns(3)
with cols[0]:
    st.page_link("pages/1_Style_Studio.py", label="👗 Style Studio", use_container_width=True)
with cols[1]:
    st.page_link("pages/2_Dreamhouse_Designer.py", label="🏠 Dreamhouse Designer", use_container_width=True)
with cols[2]:
    st.page_link("pages/3_Goals_Vision_Board.py", label="✨ Goals & Vision", use_container_width=True)

st.markdown('<div class="footer">Made with 🩷 — you can be anything.</div>', unsafe_allow_html=True)
