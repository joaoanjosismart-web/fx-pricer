"""📈 Curvas e fatores de desconto.

Convenções de mercado usadas:
- BRL: taxa pré (DI) efetiva ao ano, base 252 dias úteis.
- USD: taxa simples ao ano, base 360 dias corridos.
"""

from __future__ import annotations

import numpy as np


def df_brl(taxa_pre: float, du: int) -> float:
    """Fator de desconto em BRL (taxa pré efetiva a.a., 252 dias úteis)."""
    return (1.0 + taxa_pre) ** (-du / 252.0)


def df_usd(taxa_usd: float, dc: int) -> float:
    """Fator de desconto em USD (taxa simples a.a., 360 dias corridos)."""
    return 1.0 / (1.0 + taxa_usd * dc / 360.0)


def forward(spot: float, taxa_pre: float, du: int, taxa_usd: float, dc: int) -> float:
    """Forward USD/BRL por paridade coberta de juros.

    F = S * DF_usd / DF_brl
    """
    return spot * df_usd(taxa_usd, dc) / df_brl(taxa_pre, du)


class CurvaPre:
    """Curva pré (DI x pré) a partir de vértices, com interpolação flat forward.

    `vertices` é um dicionário `{dias_uteis: taxa_efetiva_aa}`, por exemplo
    `{21: 0.1475, 63: 0.1460, 126: 0.1440, 252: 0.1400}`.
    Fora do intervalo dos vértices, mantém a taxa do vértice mais próximo.
    """

    def __init__(self, vertices: dict[int, float]):
        if not vertices:
            raise ValueError("Informe ao menos um vértice da curva.")
        self.du = np.array(sorted(vertices), dtype=float)
        self.r = np.array([vertices[int(k)] for k in self.du], dtype=float)
        self._ln_df = -(self.du / 252.0) * np.log1p(self.r)

    def df(self, du: int) -> float:
        """Fator de desconto para `du` dias úteis."""
        if du <= 0:
            return 1.0
        if du <= self.du[0]:
            return float((1.0 + self.r[0]) ** (-du / 252.0))
        if du >= self.du[-1]:
            return float((1.0 + self.r[-1]) ** (-du / 252.0))
        return float(np.exp(np.interp(du, self.du, self._ln_df)))

    def taxa(self, du: int) -> float:
        """Taxa efetiva a.a. (base 252) para `du` dias úteis."""
        if du <= 0:
            return float(self.r[0])
        return float(self.df(du) ** (-252.0 / du) - 1.0)
