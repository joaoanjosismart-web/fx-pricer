"""📊 Gráficos (matplotlib). Cada função devolve a figura."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from .curves import CurvaPre, forward
from .ndf import NDF
from .options import FXOption


def plot_payoff_ndf(ndf: NDF, largura: float = 0.15):
    """Resultado do NDF na liquidação e MTM hoje, em função do spot/fixing."""
    spots = np.linspace(ndf.strike * (1 - largura), ndf.strike * (1 + largura), 200)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(spots, ndf.payoff(spots) / 1e3, label="Payoff na liquidação")
    ax.plot(spots, ndf.mtm_vs_spot(spots) / 1e3, "--", label="MTM hoje")
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(ndf.strike, color="gray", lw=0.8, ls=":")
    ax.set_xlabel("USD/BRL")
    ax.set_ylabel("R$ mil")
    ax.set_title("NDF: payoff e marcação a mercado")
    ax.legend()
    fig.tight_layout()
    return fig


def plot_preco_greeks(opcao: FXOption, largura: float = 0.15):
    """Prêmio, delta, gamma e vega em função do spot."""
    from dataclasses import replace

    spots = np.linspace(opcao.spot * (1 - largura), opcao.spot * (1 + largura), 120)
    ops = [replace(opcao, spot=float(s)) for s in spots]
    series = {
        "Prêmio (R$)": [o.preco() for o in ops],
        "Delta": [o.delta() for o in ops],
        "Gamma": [o.gamma() for o in ops],
        "Vega (1 vol)": [o.vega() for o in ops],
    }
    fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
    for ax, (nome, ys) in zip(axes.ravel(), series.items()):
        ax.plot(spots, ys)
        ax.axvline(opcao.strike, color="gray", lw=0.8, ls=":")
        ax.set_title(nome)
    for ax in axes[-1]:
        ax.set_xlabel("USD/BRL")
    fig.suptitle(f"Opção {opcao.tipo} (strike {opcao.strike:.4f}): prêmio e Greeks")
    fig.tight_layout()
    return fig


def plot_curva_forward(spot: float, curva: CurvaPre, taxa_usd: float, du_max: int = 504):
    """Forward USD/BRL por vencimento (dias úteis), usando a curva pré."""
    dus = np.arange(21, du_max + 1, 21)
    fwds = [
        forward(spot, curva.taxa(int(d)), int(d), taxa_usd, int(round(d * 365 / 252)))
        for d in dus
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(dus, fwds, marker="o", ms=3)
    ax.axhline(spot, color="gray", lw=0.8, ls=":", label="Spot")
    ax.set_xlabel("Dias úteis até o vencimento")
    ax.set_ylabel("Forward USD/BRL")
    ax.set_title("Curva forward")
    ax.legend()
    fig.tight_layout()
    return fig


def plot_trajetorias(tempos, caminhos: np.ndarray, strike: float | None = None, n: int = 50):
    """Algumas trajetórias simuladas e a média."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(tempos, caminhos[:n].T, lw=0.6, alpha=0.5)
    ax.plot(tempos, caminhos.mean(axis=0), "k", lw=2, label="Média das trajetórias")
    if strike is not None:
        ax.axhline(strike, color="red", ls=":", label="Strike")
    ax.set_xlabel("Anos")
    ax.set_ylabel("USD/BRL")
    ax.set_title("Trajetórias simuladas")
    ax.legend()
    fig.tight_layout()
    return fig


def plot_convergencia_mc(resultados: list[dict], referencia: float | None = None):
    """Preço Monte Carlo (com IC 95%) conforme o nº de caminhos aumenta."""
    ns = [r["n_caminhos"] for r in resultados]
    precos = np.array([r["preco"] for r in resultados])
    inf = np.array([r["ic95_inf"] for r in resultados])
    sup = np.array([r["ic95_sup"] for r in resultados])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.errorbar(ns, precos, yerr=[precos - inf, sup - precos], fmt="o-", capsize=3, label="Monte Carlo (IC 95%)")
    if referencia is not None:
        ax.axhline(referencia, color="red", ls="--", label="Fórmula fechada")
    ax.set_xscale("log")
    ax.set_xlabel("Nº de caminhos")
    ax.set_ylabel("Prêmio (R$ por USD)")
    ax.set_title("Convergência do Monte Carlo")
    ax.legend()
    fig.tight_layout()
    return fig
