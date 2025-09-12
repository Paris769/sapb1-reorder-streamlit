"""Modulo di utilità per l'applicazione di riordino.

Questo modulo rende disponibili le funzioni principali all'avvio dell'app Streamlit.
"""

__all__ = [
    "parsing",
    "io_excel",
    "rules",
    "reporting",
]
# Extra tabs (safe import)
import app.web.extensions  # noqa: F401
