"""Algoritmi di calcolo dei fabbisogni di riordino.

Questo modulo contiene le funzioni che, a partire da un DataFrame normalizzato
contenente le informazioni sui movimenti di magazzino e vendite, calcolano
quantità da ordinare ai fornitori secondo logiche configurabili.

Principi del calcolo:

* **Domanda giornaliera**: è determinata come il massimo tra la quota giornaliera
  delle quantità spedite nel periodo analizzato e la media mensile di vendita
  negli ultimi 6 mesi divisa per 30. Ciò evita di sottostimare la domanda in
  caso di periodi di bassa attività o di sovrastimarla se la media a 6 mesi è
  troppo bassa.
* **Scorta di sicurezza**: definita in giorni, viene moltiplicata per la
  domanda giornaliera.
* **Punto di riordino (ROP)**: la domanda giornaliera moltiplicata per il
  lead time (giorni necessari per ricevere il materiale) più la scorta di
  sicurezza.
* **Livello target**: la domanda giornaliera moltiplicata per la somma di
  lead time e coverage (copertura desiderata), più la scorta di sicurezza. È
  il livello di stock che vogliamo raggiungere.
* **Disponibilità proiettata**: giacenza totale meno l’impegnato su ordini
  clienti più le quantità già ordinate ai fornitori.
* **Fabbisogno**: se la disponibilità proiettata scende sotto il ROP,
  ordinare la differenza fra il target e la disponibilità proiettata;
  altrimenti nessun ordine. La quantità viene arrotondata al multiplo del
  collo (pack size) quando disponibile.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd



def _safe_numeric(series: pd.Series) -> pd.Series:
    """Converte una serie in numerico sostituendo i NaN con 0.

    Args:
        series: La serie da convertire.

    Returns:
        Una serie con valori numerici dove i NaN sono sostituiti con 0.
    """
    return pd.to_numeric(series.fillna(0), errors="coerce").fillna(0)



def compute_reorder(
    df: pd.DataFrame,
    start_date: Optional[date],
    end_date: Optional[date],
    lead_time: int = 10,
    coverage: int = 45,
    safety: int = 15,
) -> pd.DataFrame:
    """Calcola le quantità da ordinare per ciascuna combinazione articolo/fornitore.

    Args:
        df: DataFrame contenente le colonne normalizzate. Devono essere presenti
            almeno `product_code`, `vendor_name`, `qty_shipped_period`,
            `qty_already_ordered_suppliers`, `qty_committed_open_customer_orders`,
            `stock_on_hand_total` e `avg_sales_last_6_months`. Le eventuali
            colonne mancanti vengono gestite assumendo 0.
        start_date: Data di inizio del periodo analizzato.
        end_date: Data di fine del periodo analizzato.
        lead_time: Giorni di approvvigionamento.
        coverage: Giorni di copertura desiderati oltre il lead time.
        safety: Giorni di scorta di sicurezza.

    Returns:
        DataFrame con una riga per ciascun articolo/fornitore e colonne
        aggiuntive (domanda giornaliera, scorta di sicurezza, punti di riordino,
        quantità da ordinare, etc.).
    """
    df = df.copy()
    # Garantisce la presenza delle colonne richieste, inizializzandole con 0 se assenti
    for col in [
        "qty_shipped_period",
        "qty_ordered_period",
        "qty_already_ordered_suppliers",
        "qty_committed_open_customer_orders",
        "stock_on_hand_total",
        "avg_sales_last_6_months",
        "pack_size",
    ]:
        if col not in df.columns:
            df[col] = 0
    if "vendor_name" not in df.columns:
        df["vendor_name"] = ""
    if "product_description" not in df.columns:
        df["product_description"] = ""

    # Assicura che le colonne numeriche siano effettivamente numeriche
    num_cols = [
        "qty_shipped_period",
        "qty_ordered_period",
        "qty_already_ordered_suppliers",
        "qty_committed_open_customer_orders",
        "stock_on_hand_total",
        "avg_sales_last_6_months",
        "pack_size",
    ]
    df[num_cols] = df[num_cols].apply(_safe_numeric)

    # Determina la durata in giorni del periodo
    if start_date and end_date:
        period_days = max((end_date - start_date).days + 1, 1)
    else:
        # Se non specificato, assume un periodo di 30 giorni
        period_days = 30

    # Raggruppa per articolo e fornitore
    group_cols = ["product_code", "vendor_name"]
    agg = df.groupby(group_cols).agg(
        qty_shipped_period=("qty_shipped_period", "sum"),
        qty_already_ordered_suppliers=("qty_already_ordered_suppliers", "sum"),
        qty_committed_open_customer_orders=("qty_committed_open_customer_orders", "sum"),
        stock_on_hand_total=("stock_on_hand_total", "max"),
        avg_sales_last_6_months=("avg_sales_last_6_months", "max"),
        pack_size=("pack_size", "max"),
        product_description=("product_description", "first"),
    ).reset_index()

    # Domanda giornaliera
    shipments_daily = agg["qty_shipped_period"] / period_days
    avg_month = agg["avg_sales_last_6_months"] / 30.0
    agg["daily_demand"] = np.where(shipments_daily > avg_month, shipments_daily, avg_month)

    # Scorta di sicurezza, ROP e target
    agg["safety_stock_qty"] = agg["daily_demand"] * safety
    agg["reorder_point"] = agg["daily_demand"] * lead_time + agg["safety_stock_qty"]
    agg["target_level"] = agg["daily_demand"] * (lead_time + coverage) + agg["safety_stock_qty"]

    # Disponibilità proiettata
    agg["projected_available"] = (
        agg["stock_on_hand_total"]
        - agg["qty_committed_open_customer_orders"]
        + agg["qty_already_ordered_suppliers"]
    )

    # Fabbisogno grezzo
    raw_need = agg["target_level"] - agg["projected_available"]
    raw_need[raw_need < 0] = 0

    # Arrotondamento al multiplo del collo
    def _apply_pack_size(qty: float, pack: float) -> int:
        if pack is None or pack == 0 or math.isnan(pack):
            return int(math.ceil(qty))
        return int(math.ceil(qty / pack) * pack)

    agg["qty_to_order"] = [
        _apply_pack_size(qty, pack) for qty, pack in zip(raw_need, agg["pack_size"])
    ]

    # Calcola la copertura residua in giorni sulla base della disponibilità proiettata
    agg["coverage_days"] = np.where(
        agg["daily_demand"] > 0,
        agg["projected_available"] / agg["daily_demand"],
        np.nan,
    )

    # Scarta colonne non più necessarie per la restituzione finale? Manteniamo tutte per audit
    return agg
