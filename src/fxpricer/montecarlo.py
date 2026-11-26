"""🎲 Monte Carlo para produtos que dependem da trajetória (Asiático e cap).

Modelo: movimento browniano geométrico com drift calibrado para que
E[S_T] seja igual ao forward de mercado (neutro ao risco):

    mu = ln(F / S) / T
    S_t = S * exp((mu - 0.5 * vol^2) * t + vol * W_t)
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from tqdm import tqdm

Payoff = Callable[[np.ndarray], np.ndarray]


def simular_trajetorias(
    spot: float,
    forward_T: float,
    vol: float,
    tempos,
    n_caminhos: int = 1_000,
    seed: int | None = 42,
) -> np.ndarray:
    """Simula trajetórias nos instantes `tempos` (em anos, crescentes).

    Retorna matriz `(n_caminhos, len(tempos))` com o spot em cada data de observação.
    """
    tempos = np.asarray(tempos, dtype=float)
    rng = np.random.default_rng(seed)
    T = tempos[-1]
    mu = np.log(forward_T / spot) / T
    dt = np.diff(np.concatenate(([0.0], tempos)))
    z = rng.standard_normal((n_caminhos, len(tempos)))
    incrementos = (mu - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * z
    return spot * np.exp(np.cumsum(incrementos, axis=1))


def preco_mc(
    payoff: Payoff,
    spot: float,
    forward_T: float,
    vol: float,
    tempos,
    df_desconto: float,
    n_caminhos: int = 200_000,
    lote: int = 20_000,
    seed: int | None = 42,
    barra: bool = True,
) -> dict[str, float]:
    """Preço por Monte Carlo com variáveis antitéticas.

    `payoff` recebe a matriz de trajetórias `(n, n_obs)` e devolve o vetor de
    resultados em BRL. `df_desconto` é o fator de desconto em BRL até a liquidação.
    O erro padrão é calculado sobre as médias dos pares antitéticos.
    """
    tempos = np.asarray(tempos, dtype=float)
    rng = np.random.default_rng(seed)
    T = tempos[-1]
    mu = np.log(forward_T / spot) / T
    dt = np.diff(np.concatenate(([0.0], tempos)))
    drift = (mu - 0.5 * vol**2) * dt
    difusao = vol * np.sqrt(dt)

    lote = max(2, lote - lote % 2)  # par, por causa dos antitéticos
    meio_total = int(np.ceil(n_caminhos / 2))
    feitos = 0
    n = soma = soma2 = 0.0

    with tqdm(total=meio_total * 2, desc="🎲 Monte Carlo", disable=not barra) as bar:
        while feitos < meio_total:
            meio = min(lote // 2, meio_total - feitos)
            z = rng.standard_normal((meio, len(tempos)))
            caminhos_a = spot * np.exp(np.cumsum(drift + difusao * z, axis=1))
            caminhos_b = spot * np.exp(np.cumsum(drift - difusao * z, axis=1))
            par = 0.5 * (payoff(caminhos_a) + payoff(caminhos_b))
            n += meio
            soma += par.sum()
            soma2 += (par**2).sum()
            feitos += meio
            bar.update(2 * meio)

    media = soma / n
    var = max(soma2 / n - media**2, 0.0)
    erro = np.sqrt(var / n)
    preco = df_desconto * media
    ep = df_desconto * erro
    return {
        "preco": float(preco),
        "erro_padrao": float(ep),
        "ic95_inf": float(preco - 1.96 * ep),
        "ic95_sup": float(preco + 1.96 * ep),
        "n_caminhos": int(2 * n),
    }


# ---- payoffs ----------------------------------------------------------
def payoff_europeia(strike: float, tipo: str = "call", nocional: float = 1.0) -> Payoff:
    """Opção europeia (usa o último ponto da trajetória). Serve para validação."""
    tipo = tipo.lower()

    def _p(caminhos: np.ndarray) -> np.ndarray:
        s_t = caminhos[:, -1]
        v = np.maximum(s_t - strike, 0.0) if tipo == "call" else np.maximum(strike - s_t, 0.0)
        return nocional * v

    return _p


def payoff_asiatica_opcao(strike: float, tipo: str = "call", nocional: float = 1.0) -> Payoff:
    """Opção asiática de preço médio (média aritmética dos fixings/PTAX)."""
    tipo = tipo.lower()

    def _p(caminhos: np.ndarray) -> np.ndarray:
        media = caminhos.mean(axis=1)
        v = np.maximum(media - strike, 0.0) if tipo == "call" else np.maximum(strike - media, 0.0)
        return nocional * v

    return _p


def payoff_asiatico_ndf(strike: float, nocional: float = 1.0, compra: bool = True) -> Payoff:
    """NDF asiático: liquida pela média dos fixings em vez do fixing final."""
    sinal = 1.0 if compra else -1.0

    def _p(caminhos: np.ndarray) -> np.ndarray:
        return sinal * nocional * (caminhos.mean(axis=1) - strike)

    return _p


def payoff_ndf_com_cap(
    strike: float, cap: float, nocional: float = 1.0, compra: bool = True
) -> Payoff:
    """NDF com cap (premissa simplificada).

    O ganho de quem compra USD é limitado quando o fixing final supera `cap`:
    resultado = N * (min(S_T, cap) - K). Variações de mercado (knock-out,
    cap só no ganho etc.) existem, então confira sempre as cláusulas do contrato.
    """
    sinal = 1.0 if compra else -1.0

    def _p(caminhos: np.ndarray) -> np.ndarray:
        return sinal * nocional * (np.minimum(caminhos[:, -1], cap) - strike)

    return _p
