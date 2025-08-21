"""Applicazione Streamlit per il calcolo degli ordini di riordino da file SAP B1.

L'applicazione permette di caricare un file Excel esportato da SAP Business One,
configurare alcuni parametri (lead time, copertura e scorta di sicurezza) e
ottenere automaticamente le quantità da ordinare per ciascun articolo e
fornitore. I risultati sono scaricabili come file Excel (analisi completa e
ordini suddivisi per fornitore) e come template CSV per l'anagrafica
fornitori.
"""

from __future__ import annotations

import io
import os
import tempfile
from datetime import date, timedelta

# --- Add parent folder to sys.path ----------------------------------------------------
# When this script is executed via `streamlit run`, Python does not treat the
# repository as an installable package. To make the top-level `app` package
# importable (for parsing, io_excel, rules, reporting), we append the parent
# directory of this file to `sys.path`. This resolves ModuleNotFoundError
# errors on Streamlit Cloud and when running locally outside of package context.
import sys
from pathlib import Path


# Append the repository root (the parent of the `app` package) to ``sys.path``
#
# When this script is executed via ``streamlit run``, Python evaluates it as a
# stand‑alone module rather than as part of an installed package.  In that
# context the ``app`` package (which lives inside the repository root) is not
# importable by default because its parent directory is not on ``sys.path``.
# To resolve this, compute the directory two levels above this file
# (i.e. the repository root) and add it to ``sys.path`` if it isn't already
# present.  This allows ``import app`` to succeed on Streamlit Cloud and when
# running locally outside of a package context.
parent_dir = Path(__file__).resolve().parents[2]
parent_str = str(parent_dir)
if parent_str not in sys.path:
    sys.path.append(parent_str)

import streamlit as st

# Absolute imports are required when running this module as a script via Streamlit.
# Using a package-relative import (from .. import ...) would fail because
# `streamlit run` executes this file outside of the package context. Referencing
# the top-level package `app` ensures the modules can be located regardless of
# how the application is executed.
from app import parsing, io_excel, rules, reporting


def main() -> None:
    st.set_page_config(page_title="Riordino SAP B1", layout="wide")
    st.title("Calcolo automatico dei riordini da SAP Business One")

    st.write(
        """
        Carica un file Excel esportato da SAP Business One contenente le vendite e le
        giacenze. L'applicazione determinerà la domanda giornaliera e calcolerà
        automaticamente le quantità da ordinare ai fornitori, in base ai parametri
        configurati.
        """
    )

    # Caricamento del file
    uploaded_file = st.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])

    # Parametri configurabili
    col1, col2, col3 = st.columns(3)
    with col1:
        lead_time = st.number_input(
            "Lead time (giorni)", min_value=0, value=10, step=1, help="Tempo medio di consegna dai fornitori"
        )
    with col2:
        coverage = st.number_input(
            "Giorni di copertura", min_value=0, value=45, step=1, help="Giorni aggiuntivi oltre il lead time per cui si vuole avere copertura"
        )
    with col3:
        safety = st.number_input(
            "Scorta di sicurezza (giorni)", min_value=0, value=15, step=1, help="Giorni di scorta da mantenere come margine di sicurezza"
        )

    if uploaded_file is not None:
        # Mostra il nome del file
        st.success(f"File caricato: {uploaded_file.name}")

        # Estrae l'intervallo di date dal nome del file
        # Se il parsing non riesce, start_date e end_date sono None.
        start_date, end_date = parsing.extract_period_from_filename(uploaded_file.name)
        if start_date and end_date:
            st.info(f"Periodo individuato nel nome file: {start_date} → {end_date}")
        else:
            st.warning(
                "Non è stato possibile rilevare l'intervallo di date dal nome del file. "
                "Puoi impostare manualmente il periodo nelle caselle qui sotto."
            )

        # Permette all'utente di impostare manualmente il periodo di analisi.
        # Se il parsing automatico non ha trovato le date, utilizza gli ultimi 30 giorni come default.
        if not start_date or not end_date:
            default_start = date.today() - timedelta(days=30)
            default_end = date.today()
        else:
            default_start = start_date
            default_end = end_date

        # Interfaccia per selezionare il periodo: data inizio e data fine.
        # Le date selezionate sovrascrivono eventuali date rilevate dal nome file.
        col_period_start, col_period_end = st.columns(2)
        with col_period_start:
            manual_start = st.date_input(
                "Data inizio periodo",
                value=default_start,
                help="Seleziona la data di inizio del periodo da analizzare",
            )
        with col_period_end:
            manual_end = st.date_input(
                "Data fine periodo",
                value=default_end,
                help="Seleziona la data di fine del periodo da analizzare",
            )
        # Aggiorna start_date e end_date con le scelte dell'utente
        start_date = manual_start
        end_date = manual_end

        # Lettura del file Excel
        try:
            df_raw = io_excel.read_sales_excel(uploaded_file)
        except Exception as exc:
            st.error(f"Errore nella lettura del file: {exc}")
            return

        # Calcolo del riordino
        reorder_df = rules.compute_reorder(
            df_raw,
            start_date=start_date,
            end_date=end_date,
            lead_time=int(lead_time),
            coverage=int(coverage),
            safety=int(safety),
        )

        orders_df = reorder_df[reorder_df["qty_to_order"] > 0].copy()

        # Riepilogo
        st.subheader("Riepilogo risultati")
        total_items = len(reorder_df)
        items_to_order = len(orders_df)
        total_qty_to_order = int(orders_df["qty_to_order"].sum()) if not orders_df.empty else 0
        st.write(f"Articoli totali analizzati: **{total_items}**")
        st.write(f"Articoli con ordine suggerito: **{items_to_order}**")
        st.write(f"Quantità totale da ordinare: **{total_qty_to_order}**")

        # Opzioni di ordinamento per l'esportazione e l'anteprima
        sort_option = st.selectbox(
            "Ordina righe degli ordini per:",
            (
                "Alfabetico (codice prodotto)",
                "Rilevanza (urgenza × domanda)",
            ),
            index=0,
            help="Seleziona l'ordinamento delle righe negli ordini per fornitore e nell'anteprima",
        )
        sort_by = "relevance" if sort_option.startswith("Rilevanza") else "alphabetical"

        # Mostra i primi 100 ordini per anteprima
        if not orders_df.empty:
            st.subheader("Anteprima ordini")
            preview_cols = [
                "product_code",
                "product_description",
                "vendor_name",
                "qty_to_order",
                "reorder_point",
                "projected_available",
                "target_level",
                "coverage_days",
                "relevance_score",
            ]
            # Ordina le righe in base alla scelta dell'utente
            preview_df = orders_df.copy()
            if sort_by == "relevance" and "relevance_score" in preview_df.columns:
                preview_df = preview_df.sort_values(
                    by=["relevance_score", "product_code"], ascending=[False, True]
                )
            else:
                preview_df = preview_df.sort_values(by="product_code", ascending=True)
            st.dataframe(preview_df[preview_cols].head(100))
        else:
            st.info("Nessun articolo necessita di riordino con i parametri selezionati.")

        # Esporta i risultati completi in un workbook Excel
        st.subheader("Download report")
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis_path = os.path.join(tmpdir, "analisi_riordino.xlsx")
            vendor_path = os.path.join(tmpdir, "ordini_per_fornitore.xlsx")
            vendors_csv_path = os.path.join(tmpdir, "vendors_template.csv")

            reporting.generate_analysis_xlsx(reorder_df, analysis_path)
            # Passa la modalità di ordinamento alla funzione di esportazione degli ordini
            reporting.generate_orders_by_vendor_xlsx(
                reorder_df, vendor_path, sort_by=sort_by
            )
            reporting.generate_vendors_template_csv(reorder_df, vendors_csv_path)

            # Leggi i file in memoria e crea i pulsanti di download
            with open(analysis_path, "rb") as f:
                st.download_button(
                    "Scarica workbook analisi (xlsx)",
                    f,
                    file_name="Analisi_riordino.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with open(vendor_path, "rb") as f:
                st.download_button(
                    "Scarica ordini per fornitore (xlsx)",
                    f,
                    file_name="Ordini_per_fornitore.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with open(vendors_csv_path, "rb") as f:
                st.download_button(
                    "Scarica template fornitori (csv)",
                    f,
                    file_name="vendors_template.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    main()