"""Presentation-only helpers. User supplied text stays in Streamlit widgets."""
from pathlib import Path
from base64 import b64encode
from functools import lru_cache

import streamlit as st


_CSS = Path(__file__).resolve().parents[1] / "assets" / "base.css"


@lru_cache(maxsize=1)
def _font_css() -> str:
    rules = []
    for weight, name in ((400, "Regular"), (700, "Bold")):
        data = b64encode((_CSS.parent / f"LiberationSans-{name}.ttf").read_bytes()).decode()
        rules.append(f"@font-face{{font-family:'Project Sans';src:url(data:font/ttf;base64,{data}) format('truetype');font-weight:{weight};font-display:swap;}}")
    return "".join(rules)


def load_theme() -> None:
    css = _CSS.read_text(encoding='utf-8') + (_CSS.parent / 'sapphire.css').read_text(encoding='utf-8')
    st.markdown(f"<style>{_font_css()}{css}</style>", unsafe_allow_html=True)


def money(value: float | None) -> str:
    return "Chưa đủ dữ liệu" if value is None else f"{value:,.0f}".replace(",", ".") + " ₫"


def percent(value: float | None) -> str:
    return "Chưa đủ dữ liệu" if value is None else f"{value * 100:.1f}".replace(".", ",") + "%"
