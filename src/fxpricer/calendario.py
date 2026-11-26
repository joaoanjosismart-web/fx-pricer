"""📅 Contagem de dias úteis (base 252) e corridos."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import numpy as np


def dias_uteis(inicio: date, fim: date, feriados: Iterable[date] | None = None) -> int:
    """Dias úteis entre `inicio` (inclusive) e `fim` (exclusive).

    Considera sábado e domingo como não úteis. Para ficar fiel ao mercado
    brasileiro, passe a lista de feriados nacionais (ANBIMA/B3) em `feriados`.
    """
    feriados_np = np.array(list(feriados or []), dtype="datetime64[D]")
    return int(
        np.busday_count(
            np.datetime64(inicio, "D"),
            np.datetime64(fim, "D"),
            holidays=feriados_np,
        )
    )


def dias_corridos(inicio: date, fim: date) -> int:
    """Dias corridos entre duas datas."""
    return (fim - inicio).days
