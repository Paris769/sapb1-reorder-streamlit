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
from datetime import date

import streamlit as st

from .. import parsing, io_excel, rules, reporting


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
        start_date, end_date = parsing.extract_period_from_filename(uploaded_file.name)
        if start_date and end_date:
            st.info(f"Periodo individuato nel nome file: {start_date} → {end_date}")
        else:
            st.warning(
                "Non è stato possibile rilevare l'intervallo di date dal nome del file. "
                "Il periodo verrà assunto pari a 30 giorni."
            )

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
            ]
            st.dataframe(orders_df[preview_cols].sort_values(by="vendor_name").head(100))
        else:
            st.info("Nessun articolo necessita di riordino con i parametri selezionati.")

        # Esporta i risultati completi in un workbook Excel
        st.subheader("Download report")
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis_path = os.path.join(tmpdir, "analisi_riordino.xlsx")
            vendor_path = os.path.join(tmpdir, "ordini_per_fornitore.xlsx")
            vendors_csv_path = os.path.join(tmpdir, "vendors_template.csv")

            reporting.generate_analysis_xlsx(reorder_df, analysis_path)
            reporting.generate_orders_by_vendor_xlsx(reorder_df, vendor_path)
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
