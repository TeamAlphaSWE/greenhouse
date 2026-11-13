from pathlib import Path

import streamlit.components.v1 as components

_frontend_dir = (Path(__file__).parent / "frontend").resolve()
_component_func = components.declare_component("area_map", path=str(_frontend_dir))


def area_map(svg, key=None):
    """Render `svg` (a string of SVG markup, see landing.py's render_map) and return the
    last-clicked region as {"areaId": ..., "clickedAt": ...}, or None before any click.

    A real component, not a page link: clicking a region reports back over the same
    Streamlit session (a normal rerun), so it never drops the session the way a plain
    SVG `<a href>` does (that forces a full page navigation, which starts a brand new,
    logged-out session).
    """
    return _component_func(svg=svg, key=key, default=None)
