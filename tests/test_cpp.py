"""⚡ Testes do núcleo C++: devem bater com a implementação Python."""

import numpy as np
import pytest

import fxpricer as fx

pytestmark = pytest.mark.skipif(not fx.CPP_DISPONIVEL, reason="módulo C++ não compilado")

P = dict(spot=5.40, strike=5.45, du=63, dc=91, taxa_pre=0.145, taxa_usd=0.043, vol=0.14)


@pytest.mark.parametrize("tipo", ["call", "put"])
def test_preco_igual_python(tipo):
    py = fx.FXOption(tipo=tipo, **P).preco()
    assert fx.preco_opcao_cpp(tipo=tipo, **P) == pytest.approx(py, rel=1e-10)


def test_greeks_iguais_python():
    op = fx.FXOption(tipo="call", **P)
    g = fx.greeks_opcao_cpp(tipo="call", **P)
    assert g["delta"] == pytest.approx(op.delta(), rel=1e-9)
    assert g["gamma"] == pytest.approx(op.gamma(), rel=1e-9)
    assert g["vega_1vol"] == pytest.approx(op.vega(), rel=1e-9)


def test_mc_europeu_bate_formula_fechada():
    T = P["dc"] / 365
    F = fx.forward(P["spot"], P["taxa_pre"], P["du"], P["taxa_usd"], P["dc"])
    r = fx.preco_mc_cpp(
        "european", P["strike"], P["spot"], F, P["vol"], [T],
        fx.df_brl(P["taxa_pre"], P["du"]), n_caminhos=400_000, seed=3,
    )
    fechada = fx.FXOption(tipo="call", **P).preco()
    assert abs(r["preco"] - fechada) < 4 * r["erro_padrao"]


def test_mc_deterministico_entre_threads():
    T = P["dc"] / 365
    F = fx.forward(P["spot"], P["taxa_pre"], P["du"], P["taxa_usd"], P["dc"])
    tempos = np.linspace(T / 12, T, 12)
    args = ("asian_option", P["strike"], P["spot"], F, P["vol"], tempos, 0.97)
    a = fx.preco_mc_cpp(*args, n_caminhos=100_000, n_threads=1)
    b = fx.preco_mc_cpp(*args, n_caminhos=100_000, n_threads=2)
    assert a["preco"] == b["preco"]


def test_entrada_invalida():
    with pytest.raises(ValueError):
        fx.preco_opcao_cpp(tipo="call", **{**P, "vol": -1.0})
