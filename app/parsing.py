"""Utility per l'estrazione delle date dal nome del file.

Le esportazioni di SAP Business One spesso includono un intervallo temporale nel nome
 del file, ad esempio `Analisi vendite - Basato su DDT - dett cliente 01.01.25_019.08.25 base.xlsx`.
Questo modulo contiene funzioni per individuare automaticamente l'intervallo di
analisi, utile per determinare i giorni del periodo su cui calcolare la domanda.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Tuple


def _parse_single_date(token: str) -> Optional[date]:
    """Converte una stringa nel formato ``DD.MM.YY`` o ``DD.MM.YYYY`` in un oggetto ``date``.

    Args:
        token: La stringa contenente la data.

    Returns:
        L'oggetto ``date`` corrispondente oppure ``None`` se il formato non è riconosciuto.
    """
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue
    return None


def extract_period_from_filename(filename: str) -> Tuple[Optional[date], Optional[date]]:
    """Estrae le date di inizio e fine dal nome di un file.

    La funzione cerca nel nome del file tutte le occorrenze di una data nel formato
    ``DD.MM.YY`` oppure ``DD.MM.YYYY``. Se individua almeno due date, restituisce la
    prima e l'ultima convertite in oggetti ``date``. In caso contrario restituisce
    ``(None, None)``.

    Args:
        filename: Il nome del file da analizzare.

    Returns:
        Una tupla ``(start_date, end_date)``. Se non vengono trovate due date,
        entrambi gli elementi saranno ``None``.
    """
    # Normalizza eventuali caratteri di separazione (underscore, trattini)
    clean = filename.replace("_", " ").replace("-", " ").replace("/", " ")
    # Ricerca di tutte le date nel formato dd.mm.yy o dd.mm.yyyy
    tokens = re.findall(r"\b\d{2}\.\d{2}\.\d{2,4}\b", clean)
    dates: list[date] = []
    for token in tokens:
        parsed = _parse_single_date(token)
        if parsed:
            dates.append(parsed)
    if len(dates) >= 2:
        # Considera la prima e l'ultima data trovate
        start_date = dates[0]
        end_date = dates[-1]
        # Se l'intervallo è invertito, correggi
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        return start_date, end_date
    return None, None
