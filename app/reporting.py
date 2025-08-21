"""Generazione di report ed esportazioni in formato Excel e CSV.

Questo modulo contiene funzioni per esportare i risultati dei calcoli di
riordino in file Excel (un workbook completo con diversi fogli e un workbook
separato con un foglio per ciascun fornitore) e per creare un template CSV
contenente le anagrafiche dei fornitori da arricchire con informazioni
supplementari come codici fornitore, MOQ e lead time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


def generate_analysis_xlsx(df: pd.DataFrame, output_path: str) -> str:
    """Esporta un workbook Excel con il dettaglio dei calcoli e i riepiloghi.

    Vengono creati diversi fogli:

    * ``Ordini_suggeriti``: contiene solo gli articoli per cui è prevista una
      quantità da ordinare maggiore di zero.
    * ``Dettaglio_calcoli``: mostra tutte le righe (anche quelle senza
      riordino) e tutte le colonne calcolate per audit completo.
    * ``Riepilogo_fornitori``: riepilogo del numero di articoli e della quantità
      totale da ordinare per ciascun fornitore.
    * ``Vicini_riordino``: articoli la cui disponibilità proiettata è inferiore
      al punto di riordino (potrebbero necessitare un riordino a breve).
    * ``Eccezioni``: articoli con domanda giornaliera nulla o altre
      anomalie (ad esempio pack size pari a zero).

    Args:
        df: DataFrame risultante da ``compute_reorder``.
        output_path: Percorso in cui salvare il file. Verrà sovrascritto se
            esiste.

    Returns:
        Il percorso del file generato.
    """
    path = Path(output_path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Ordini da emettere
        orders = df[df["qty_to_order"] > 0]
        orders.to_excel(writer, sheet_name="Ordini_suggeriti", index=False)
        # Dettaglio completo
        df.to_excel(writer, sheet_name="Dettaglio_calcoli", index=False)
        # Riepilogo per fornitore
        if not orders.empty:
            summary = (
                orders.groupby("vendor_name")
                .agg(
                    num_sku=("qty_to_order", "count"),
                    total_qty=("qty_to_order", "sum"),
                )
                .reset_index()
            )
        else:
            summary = pd.DataFrame(
                {"vendor_name": [], "num_sku": [], "total_qty": []}
            )
        summary.to_excel(writer, sheet_name="Riepilogo_fornitori", index=False)
        # Vicini al riordino: projected_available < reorder_point
        near = df[df["projected_available"] < df["reorder_point"]]
        near.to_excel(writer, sheet_name="Vicini_riordino", index=False)
        # Eccezioni: daily_demand <= 0 o pack_size <= 0
        exceptions = df[(df["daily_demand"] <= 0) | (df["pack_size"] <= 0)]
        exceptions.to_excel(writer, sheet_name="Eccezioni", index=False)
    return str(path)


def generate_orders_by_vendor_xlsx(
    df: pd.DataFrame,
    output_path: str,
    *,
    sort_by: str = "alphabetical",
) -> str:
    """Esporta un workbook con un foglio per ciascun fornitore.

    Per impostazione predefinita, le righe all'interno di ogni foglio sono
    ordinate alfabeticamente per ``product_code``. È possibile richiedere
    l'ordinamento per "rilevanza" specificando ``sort_by="relevance"``,
    nel qual caso le righe sono ordinate in base alla colonna ``relevance_score``
    decrescente (maggiore rilevanza in alto).  Se la colonna ``relevance_score``
    non è presente, l'ordinamento di ripiego resta alfabetico.

    Args:
        df: DataFrame risultante da ``compute_reorder``.
        output_path: Percorso di esportazione del file.
        sort_by: Modalità di ordinamento delle righe all'interno di ogni foglio.
            Può essere "alphabetical" (ordina per product_code) oppure
            "relevance" (ordina per relevance_score decrescente).

    Returns:
        Il percorso del file generato.
    """
    path = Path(output_path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        orders = df[df["qty_to_order"] > 0]
        if orders.empty:
            # Se non ci sono ordini, crea un foglio vuoto
            pd.DataFrame().to_excel(writer, sheet_name="Nessun_ordine", index=False)
        else:
            for vendor, subset in orders.groupby("vendor_name"):
                sheet_name = vendor if isinstance(vendor, str) and vendor else "Senza_nome"
                # Excel ha un limite di 31 caratteri per il nome del foglio
                sheet_name = sheet_name[:31]
                # Ordina il sotto-DataFrame secondo la modalità richiesta
                sorted_subset = subset.copy()
                if sort_by == "relevance" and "relevance_score" in sorted_subset.columns:
                    # Ordina per rilevanza discendente; a parità di punteggio usa il codice articolo per stabilità
                    sorted_subset = sorted_subset.sort_values(
                        by=["relevance_score", "product_code"], ascending=[False, True]
                    )
                else:
                    # Ordina alfabeticamente per codice articolo
                    sorted_subset = sorted_subset.sort_values(by="product_code", ascending=True)
                sorted_subset.to_excel(writer, sheet_name=sheet_name, index=False)
    return str(path)


def generate_vendors_template_csv(df: pd.DataFrame, output_path: str) -> str:
    """Crea un template CSV con l’elenco dei fornitori e alcune colonne da compilare.

    Args:
        df: DataFrame risultante da ``compute_reorder`` (serve solo per ottenere
            l’elenco dei fornitori).
        output_path: Percorso del file CSV da creare.

    Returns:
        Il percorso del file generato.
    """
    path = Path(output_path)
    unique_vendors = sorted(set(df["vendor_name"].dropna().astype(str)))
    template = pd.DataFrame(
        {
            "vendor_name": unique_vendors,
            "vendor_code": ["" for _ in unique_vendors],
            "moq": [0 for _ in unique_vendors],
            "default_lead_time": [10 for _ in unique_vendors],
            "currency": ["EUR" for _ in unique_vendors],
        }
    )
    template.to_csv(path, index=False)
    return str(path)