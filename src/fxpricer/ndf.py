"""💵 NDF (Non-Deliverable Forward) de USD/BRL."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .curves import df_brl, df_usd, forward


@dataclass
class NDF:
    """NDF vanilla de dólar contra real, liquidado em BRL.

    Parâmetros
    ----------
    spot: USD/BRL à vista.
    strike: taxa contratada (BRL por USD).
    du, dc: dias úteis (base 252) e dias corridos (base 360) até a liquidação.
    taxa_pre: taxa pré efetiva a.a. (DI) para o prazo.
    taxa_usd: taxa em USD simples a.a. (por exemplo, SOFR/curva USD).
    nocional: nocional em USD.
    compra: True para quem compra USD (ganha se o fixing ficar acima do strike).
    """

    spot: float
    strike: float
    du: int
    dc: int
    taxa_pre: float
    taxa_usd: float
    nocional: float = 1_000_000.0
    compra: bool = True

    @property
    def sinal(self) -> int:
        return 1 if self.compra else -1

    def forward(self) -> float:
        """Forward justo (paridade coberta de juros)."""
        return forward(self.spot, self.taxa_pre, self.du, self.taxa_usd, self.dc)

    def pontos_forward(self) -> float:
        """Forward menos spot, em BRL por USD."""
        return self.forward() - self.spot

    def valor_presente(self) -> float:
        """Marcação a mercado em BRL: N * (F - K) * DF_brl, com sinal da posição."""
        return (
            self.sinal
            * self.nocional
            * (self.forward() - self.strike)
            * df_brl(self.taxa_pre, self.du)
        )

    def payoff(self, fixing) -> np.ndarray | float:
        """Resultado na liquidação (BRL) para um fixing (PTAX) ou vetor de fixings."""
        return self.sinal * self.nocional * (np.asarray(fixing) - self.strike)

    def mtm_vs_spot(self, spots) -> np.ndarray:
        """MTM em BRL para diferentes níveis de spot (juros constantes)."""
        spots = np.asarray(spots, dtype=float)
        fator = df_usd(self.taxa_usd, self.dc) / df_brl(self.taxa_pre, self.du)
        return (
            self.sinal
            * self.nocional
            * (spots * fator - self.strike)
            * df_brl(self.taxa_pre, self.du)
        )
