"""Greenhouse credits page. Run with: python -m streamlit run Credits.py."""

from html import escape

import streamlit as st


# Names transcribed from the supplied Alpha Group roster. No roles inferred.
CONTRIBUTORS = (
    "Brian Shepard",
    "Gursimar Singh",
    "Henry Campbell",
    "Humayra Hoque Shara",
    "Jakub Keller",
    "Khalia Dogan",
    "Nathan Yoak",
    "Niesha McCrory",
    "Samuel Covey",
    "Sumedh Joshi",
    "Utkarsh Tripathi",
)

CSS = """
<style>
.gh-credits { max-width: 1080px; margin: 0 auto; font-family: inherit; }
.gh-credits * { box-sizing: border-box; }
.gh-credits .hero { background: #123d2d; color: #fffdf4;
    padding: clamp(28px, 5vw, 58px); border-radius: 24px; }
.gh-credits .eyebrow { color: #c7e5aa; font-size: 12px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin: 0 0 20px; }
.gh-credits h1 { color: #fffdf4; font-size: clamp(36px, 6vw, 62px);
    line-height: 1.1; letter-spacing: -2px; margin: 0 0 20px; padding: 0; }
.gh-credits .intro { color: #e1ece3; max-width: 620px; font-size: 17px;
    line-height: 1.7; margin: 0; }
.gh-credits .tags { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 30px; }
.gh-credits .tag { border: 1px solid #668675; border-radius: 30px;
    padding: 7px 14px; color: #f0f7e9; font-size: 13px; }
.gh-credits .team { background: #f6f7ef; color: #18372a; border-radius: 24px;
    padding: clamp(24px, 4vw, 42px); margin-top: 20px; }
.gh-credits .section-head { display: flex; align-items: baseline;
    justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
.gh-credits h2 { color: #18372a; margin: 0; padding: 0; font-size: 27px; }
.gh-credits .note { color: #526352; font-size: 14px; margin: 0; }
.gh-credits .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px; list-style: none; padding: 0; margin: 0; }
.gh-credits .person { display: flex; align-items: center; gap: 12px;
    background: #fff; border: 1px solid #dce4d6; border-radius: 14px;
    padding: 20px 16px; margin: 0; min-width: 0; }
.gh-credits .avatar { width: 42px; height: 42px; flex-shrink: 0;
    border-radius: 50%; background: #e7efdc; color: #284a30;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; }
.gh-credits .name { font-size: 15px; font-weight: 600; overflow-wrap: anywhere; }
.gh-credits .thanks { margin: 26px 0 0; padding-top: 24px;
    border-top: 1px solid #d5dfcd; color: #475b48; line-height: 1.7; font-size: 14px; }
.gh-credits footer { color: inherit; opacity: .75; text-align: center;
    font-size: 12px; padding: 24px 8px; }
@media (max-width: 850px) {
    .gh-credits .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 540px) {
    .gh-credits .grid { grid-template-columns: 1fr; }
}
</style>
"""


def render_credits():
    """Render without database, API, image, or external font dependencies."""
    cards = []
    for name in CONTRIBUTORS:
        initials = "".join(part[0] for part in name.split())
        cards.append(
            '<li class="person">'
            f'<span class="avatar" aria-hidden="true">{escape(initials)}</span>'
            f'<span class="name">{escape(name)}</span></li>'
        )

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<main class="gh-credits">'
        '<header class="hero">'
        '<p class="eyebrow">Greenhouse Project Credits</p>'
        '<h1>Grown together.</h1>'
        '<p class="intro">Behind every improvement is a team. Meet the people '
        'helping the Greenhouse Project grow through shared ideas, thoughtful '
        'development, and collaboration.</p>'
        '<div class="tags"><span class="tag">Alpha Group</span>'
        '<span class="tag">Fall 2026</span>'
        f'<span class="tag">{len(CONTRIBUTORS)} contributors</span></div>'
        '</header><section class="team" aria-labelledby="gh-team-title">'
        '<div class="section-head"><h2 id="gh-team-title">The people behind the project</h2>'
        '<p class="note"></p></div>'
        f'<ul class="grid">{"".join(cards)}</ul>'

        '</main>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    st.set_page_config(page_title="Credits | Greenhouse", page_icon="🌱", layout="wide")
    render_credits()
