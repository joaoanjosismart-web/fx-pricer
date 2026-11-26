"""🎯 Opção europeia de USD/BRL (Garman-Kohlhagen na forma de Black-76).

O preço é calculado sobre o forward, o que evita converter convenções de
juros diferentes (252 úteis em BRL e 360 corridos em USD):

    C = DF_brl * (F * N(d1) - K * N(d2))
    P = DF_brl * (K * N(-d2) - F * N(-d1))
    d1 = [ln(F/K) + 0.5 * vol^2 * T] / (vol * sqrt(T))
    d2 = d1 - vol * sqrt(T)

Aqui T = dias corridos / 365 é o tempo usado para a volatilidade.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import log, sqrt

from scipy.stats import norm

from .curves import df_brl, df_usd, forward


@dataclass
class FXOption:
    """Opção europeia de dólar (preço em BRL por USD, multiplicado pelo nocional)."""

    spot: float
    strike: float
    tipo: str  # "call" ou "put"
    du: int
    dc: int
    taxa_pre: float
    taxa_usd: float
    vol: float
    nocional: float = 1.0

    def __post_init__(self):
        self.tipo = self.tipo.lower()
        if self.tipo not in ("call", "put"):
            raise ValueError("tipo deve ser 'call' ou 'put'")
        if self.vol <= 0 or self.dc <= 0:
            raise ValueError("vol e dc devem ser positivos")

    # ---- componentes ---------------------------------------------------
    @property
    def T(self) -> float:
        return self.dc / 365.0

    @property
    def df_brl(self) -> float:
        return df_brl(self.taxa_pre, self.du)

    @property
    def df_usd(self) -> float:
        return df_usd(self.taxa_usd, self.dc)

    @property
    def forward(self) -> float:
        return forward(self.spot, self.taxa_pre, self.du, self.taxa_usd, self.dc)

    def _d1_d2(self) -> tuple[float, float]:
        sig = self.vol * sqrt(self.T)
        d1 = (log(self.forward / self.strike) + 0.5 * self.vol**2 * self.T) / sig
        return d1, d1 - sig

    # ---- preço ---------------------------------------------------------
    def preco(self) -> float:
        """Prêmio em BRL (já multiplicado pelo nocional)."""
        d1, d2 = self._d1_d2()
        F, K, DF = self.forward, self.strike, self.df_brl
        if self.tipo == "call":
            p = DF * (F * norm.cdf(d1) - K * norm.cdf(d2))
        else:
            p = DF * (K * norm.cdf(-d2) - F * norm.cdf(-d1))
        return p * self.nocional

    # ---- Greeks --------------------------------------------------------
    def delta(self) -> float:
        """Delta em relação ao spot (por USD de nocional)."""
        d1, _ = self._d1_d2()
        if self.tipo == "call":
            return self.df_usd * norm.cdf(d1) * self.nocional
        return -self.df_usd * norm.cdf(-d1) * self.nocional

    def gamma(self) -> float:
        d1, _ = self._d1_d2()
        return (
            self.df_usd
            * norm.pdf(d1)
            / (self.spot * self.vol * sqrt(self.T))
            * self.nocional
        )

    def vega(self) -> float:
        """Vega por 1 ponto de volatilidade (1 vol = 0,01)."""
        d1, _ = self._d1_d2()
        return self.df_brl * self.forward * norm.pdf(d1) * sqrt(self.T) * 0.01 * self.nocional

    def theta(self) -> float:
        """Theta de 1 dia (variação do prêmio ao passar um dia útil)."""
        if self.du <= 1 or self.dc <= 1:
            return 0.0
        amanha = replace(self, du=self.du - 1, dc=self.dc - 1)
        return amanha.preco() - self.preco()

    def rho_brl(self) -> float:
        """Variação do prêmio para +1 bp na taxa pré."""
        alta = replace(self, taxa_pre=self.taxa_pre + 0.0001)
        return alta.preco() - self.preco()

    def rho_usd(self) -> float:
        """Variação do prêmio para +1 bp na taxa em USD."""
        alta = replace(self, taxa_usd=self.taxa_usd + 0.0001)
        return alta.preco() - self.preco()

    def greeks(self) -> dict[str, float]:
        return {
            "preco": self.preco(),
            "delta": self.delta(),
            "gamma": self.gamma(),
            "vega_1vol": self.vega(),
            "theta_1dia": self.theta(),
            "rho_brl_1bp": self.rho_brl(),
            "rho_usd_1bp": self.rho_usd(),
        }
