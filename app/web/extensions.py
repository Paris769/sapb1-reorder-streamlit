# Extensions module for Streamlit app
# This file registers additional tabs (Cross-sell and Import Ordine) safely.
import streamlit as st

# Attempt to import optional dependencies
def _lazy_imports():
    missing = []
    try:
        import pandas as pd  # noqa
    except Exception:
        missing.append("pandas")
    try:
        import pdfplumber  # noqa
    except Exception:
        missing.append("pdfplumber")
    try:
        from rapidfuzz import fuzz  # noqa
    except Exception:
        missing.append("rapidfuzz")
    return missing

# Placeholder for Cross-sell tab
def cross_sell_tab():
    st.subheader("Cross-sell")
    st.info("Questa è una scheda segnaposto per la funzionalità di Cross-sell. Implementa qui la logica di suggerimento.")

# Placeholder for Import Ordine tab
def import_order_tab():
    st.subheader("Import Ordine Cliente (PDF/Excel)")
    st.info("Questa è una scheda segnaposto per l'importazione dell'ordine del cliente e l'esportazione verso SAP.")

# Test connection UI for PrestaShop (placeholder)
def prestashop_test_ui():
    with st.sidebar.expander("PrestaShop (test connessione)", expanded=False):
        st.write("Questa sezione consentirà di testare la connessione API a PrestaShop.")

# Register tabs in Streamlit app
def _register_extended_tabs():
    missing = _lazy_imports()
    if missing:
        # Show a warning in the sidebar if dependencies are missing
        with st.sidebar.expander("Dipendenze mancanti", expanded=False):
            st.warning("Installa le seguenti dipendenze per abilitare le funzionalità: " + ", ".join(missing))
        return
    prestashop_test_ui()
    tab1, tab2 = st.tabs(["Cross-sell", "Import Ordine Cliente"])
    with tab1:
        cross_sell_tab()
    with tab2:
        import_order_tab()

# Inject tabs if not already injected
def _auto_inject_tabs():
    try:
        if st.session_state.get("_extended_tabs_injected") is None:
            _register_extended_tabs()
            st.session_state["_extended_tabs_injected"] = True
    except Exception:
        pass

# Call auto injection on import
_auto_inject_tabs()
