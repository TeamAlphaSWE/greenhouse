"""Shared branding so every page looks like the same app, not just the dashboard.

Each piece sets its own background and text color together (like the dashboard's own
hero banner already did), so it reads correctly regardless of the viewer's light/dark
theme - unlike forcing the whole page to one background, which fights the real theme.
"""
import streamlit as st

DARK_GREEN = "#123d2d"
GOLD = "#d4af37"
CREAM = "#fffdf4"


def inject_sidebar():
    """Dark-green sidebar with cream nav text, consistent on every page."""
    st.markdown(f"""
    <style>
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] {{
        background:{DARK_GREEN} !important;
    }}
    [data-testid="stSidebarNav"] * {{
        color:{CREAM};
    }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title, subtitle=None):
    """A page's title as a branded hero banner, matching the dashboard's. Call once per
    page in place of st.title(); includes the shared sidebar styling."""
    inject_sidebar()
    subtitle_html = f'<p class="gh-page-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <style>
    .gh-page-hero {{ background:{DARK_GREEN}; color:{CREAM}; padding:24px 30px;
     border-radius:20px; margin-bottom:24px; }}
    .gh-page-hero h1 {{ color:{CREAM}; font-size:clamp(26px,4vw,38px);
     margin:0; padding:0; line-height:1.2; }}
    .gh-page-sub {{ color:{GOLD}; font-size:14px; margin:8px 0 0; }}
    </style>
    <div class="gh-page-hero"><h1>{title}</h1>{subtitle_html}</div>
    """, unsafe_allow_html=True)
