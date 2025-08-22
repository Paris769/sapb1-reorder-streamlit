"""Funzioni di input/output per i file Excel provenienti da SAP B1.

Questo modulo contiene utilità per leggere un file Excel esportato da SAP Business One
e normalizzarne i nomi di colonna in un formato omogeneo utilizzato nelle
successive fasi di calcolo del riordino. Gestisce alcune varianti comuni
degli header generati dal gestionale.
"""

from __future__ import annotations

import re
from typing import Dict, IO, Optional

import pandas as pd

# Dizionario di mapping tra nomi interni e possibili varianti delle colonne
_COLUMN_SYNONYMS: Dict[str, list[str]] = {
    "customer_code": ["codicecliente", "codiceclientefornitore", "cliente"],
    "product_code": ["codicearticolo", "articolo", "codprod", "codice"],
    "product_description": ["descrizionearticolo", "descrizione", "descr"],
    "qty_shipped_period": ["qtasped", "quantit\xc3\xa0spedita", "qta sped", "spedite", "quantit\xc3\xa0 spedita"],
    "qty_ordered_period": ["qtaord", "quantit\xc3\xa0ordinata", "ordinata", "ordin\xc3\xa0"],
    # Aggiunti sinonimi per i casi "Quantità ordinata dai fornitori" e
    # "Quantità ordinata dai clienti". La normalizzazione rimuove gli spazi,
    # accenti e preposizioni ("dai/dai"), quindi questi diventano
    # quantitaordinatadaifornitori e quantitaordinatadaiclienti. In questo modo
    # vengono riconosciuti correttamente.
    # Quantità già ordinate ai fornitori (ordini fornitori ancora da ricevere).
    # Includiamo varianti con o senza accenti e preposizioni per una migliore
    # riconoscibilità. La funzione di normalizzazione eliminerà comunque accenti
    # e spazi, ma avere un set completo di sinonimi permette di coprire casi
    # particolari come "quantità ordinata dai fornitori".
    "qty_already_ordered_suppliers": [
        "quantità ordinata fornitori",
        "quantità ordinata dai fornitori",
        "quantita ordinata fornitori",
        "quantita ordinata dai fornitori",
        "quantitàordinatafornitori",
        "quantitaordinatafornitori",
        "fornitoriordinati",
        "ordinatifornitori",
        "quantitaordinatadaifornitori",
    ],
    # Quantità impegnata su ordini clienti (ordini clienti non ancora evasi).
    # Anche qui si includono varianti con preposizioni e senza accenti per
    # gestire diverse esportazioni di SAP.
    "qty_committed_open_customer_orders": [
        "quantità impegnata",
        "impegnata",
        "ordini clienti",
        "impegnato",
        "quantità ordinata clienti",
        "quantità ordinata dai clienti",
        "quantita ordinata clienti",
        "quantita ordinata dai clienti",
        "quantitàordinatadaiclienti",
        "quantitaordinatadaiclienti",
    ],
    "stock_on_hand_total": ["giactot", "giacenzatotale", "giacenza", "stock"],
    "stock_rc": ["giacrc", "rc"],
    "stock_dap": ["giacds", "dap"],
    "avg_sales_last_6_months": ["media6mesi", "media6mesivendite", "vendite6mesi"],
    "selling_unit": ["unit\xc3\xa0dimisuradivendita", "unitadivendita", "unit\xc3\xa0"],
    "pack_size": ["pezzicolloscotola", "pezzi collo/scatola", "pezzi collo", "pezzi per collo"],
    "vendor_name": ["fornitore", "nomefornitore", "vendor"],
    "vendor_code": ["codicefornitore", "vendorcode"],
    "last_purchase_price": ["ultimoprezzodacquisto", "ultimo prezzo d’acquisto", "ultimo prezzo acquisto"],
    "last_purchase_price_date": ["ultimoprezzodacquistodata", "data ultimo prezzo acquisto"],
}


def _normalize_column_name(name: str) -> str:
    """Elimina caratteri speciali e converte in minuscolo una stringa."""
    name = name.lower()
    # Rimuove accenti comuni
    name = (
        name.replace("à", "a").replace("è", "e").replace("é", "e")
        .replace("ì", "i").replace("ò", "o").replace("ù", "u")
    )
    # Rimuove spazi e caratteri non alfanumerici
    return re.sub(r"[^a-z0-9]", "", name)


def _find_internal_name(external: str) -> Optional[str]:
    """Trova il nome interno corrispondente a un header proveniente dal file.

    Args:
        external: Il nome di colonna originale.

    Returns:
        Il nome canonico utilizzato internamente oppure ``None`` se non è stato
        riconosciuto.
    """
    clean = _normalize_column_name(external)
    for internal, synonyms in _COLUMN_SYNONYMS.items():
        for syn in synonyms:
            if clean == _normalize_column_name(syn):
                return internal
    return None


def read_sales_excel(file: IO[bytes]) -> pd.DataFrame:
    """Legge un file Excel proveniente da SAP B1 e normalizza i nomi delle colonne.

    Args:
        file: Oggetto file-like in modalità binaria.

    Returns:
        Un DataFrame con i nomi delle colonne normalizzati secondo il
        dizionario ``_COLUMN_SYNONYMS``. Le colonne non riconosciute vengono
        mantenute con il loro nome originale.
    """
    # Legge il file utilizzando pandas; openpyxl è richiesto per XLSX
    df = pd.read_excel(file, engine="openpyxl")
    # Mappa le colonne ai nomi canonici quando possibile
    new_columns: Dict[str, str] = {}
    for col in df.columns:
        internal = _find_internal_name(col)
        if internal:
            # Se sono presenti più colonne con lo stesso nome interno, aggiungi un suffisso
            if internal in new_columns.values():
                # Conteggia quante volte appare già
                count = list(new_columns.values()).count(internal)
                new_columns[col] = f"{internal}_{count+1}"
            else:
                new_columns[col] = internal
        else:
            new_columns[col] = _normalize_column_name(col)
    df = df.rename(columns=new_columns)
    return df