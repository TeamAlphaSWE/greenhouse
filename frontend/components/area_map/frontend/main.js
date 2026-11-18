// Renders the SVG markup Python sends (see area_map/__init__.py) and reports a clicked
// region's area_id back to Python via Streamlit.setComponentValue - no page navigation,
// so (unlike a plain <a href>) a click never drops the Streamlit session.

const root = document.getElementById("root");

function onClick(event) {
  const link = event.target.closest("[data-area-id]");
  if (!link) {
    return;
  }
  event.preventDefault();
  Streamlit.setComponentValue({ areaId: link.getAttribute("data-area-id"), clickedAt: Date.now() });
}

root.addEventListener("click", onClick);

function onRender(event) {
  const { svg } = event.detail.args;
  if (root.dataset.svg !== svg) {
    root.dataset.svg = svg;
    root.innerHTML = svg;
  }
  const el = root.querySelector("svg");
  const height = el ? el.getBoundingClientRect().height : root.getBoundingClientRect().height;
  Streamlit.setFrameHeight(height);
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
