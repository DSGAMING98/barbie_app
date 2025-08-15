from __future__ import annotations
import streamlit as st
from typing import List, Dict

def section_header(title: str, subtitle: str | None = None):
    st.markdown(f"""
    <div class="section-header">
      <h2>{title}</h2>
      {f"<p class='sub'>{subtitle}</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def card(title: str, body: str, tone: str = "primary"):
    st.markdown(f"""
    <div class="card card-{tone}">
      <div class="card-title">{title}</div>
      <div class="card-body">{body}</div>
    </div>
    """, unsafe_allow_html=True)

def gradient_button(label: str, key: str | None = None) -> bool:
    return st.button(label, use_container_width=True, key=key)

def page_link_grid(items: List[Dict[str, str]]):
    cols = st.columns(3)
    for i, item in enumerate(items):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="nav-card">
              <div class="nav-emoji">{item.get('emoji','💖')}</div>
              <div class="nav-title">{item['title']}</div>
              <div class="nav-desc">{item['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            # Streamlit-native page link where supported
            try:
                st.page_link(item["href"], label="Open", use_container_width=True)
            except Exception:
                st.link_button("Open", item["href"], use_container_width=True)
