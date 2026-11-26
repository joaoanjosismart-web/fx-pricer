from dataclasses import replace

import pytest

from fxpricer import CurvaPre


def test_paridade_put_call(call, put):
    # C - P = DF_brl * (F - K)
    esperado = call.df_brl * (call.forward - call.strike)
    assert call.preco() - put.preco() == pytest.approx(esperado, abs=1e-10)


def test_delta_confere_com_diferenca_finita(call):
    h = 1e-4
    alta = replace(call, spot=call.spot + h).preco()
    baixa = replace(call, spot=call.spot - h).preco()
    assert call.delta() == pytest.approx((alta - baixa) / (2 * h), rel=1e-6)


def test_gamma_confere_com_diferenca_finita(call):
    h = 1e-3
    alta = replace(call, spot=call.spot + h).preco()
    meio = call.preco()
    baixa = replace(call, spot=call.spot - h).preco()
    assert call.gamma() == pytest.approx((alta - 2 * meio + baixa) / h**2, rel=1e-4)


def test_vega_confere_com_diferenca_finita(call):
    h = 1e-4
    alta = replace(call, vol=call.vol + h).preco()
    baixa = replace(call, vol=call.vol - h).preco()
    # vega esta em "por 1 ponto de vol" (0,01)
    assert call.vega() == pytest.approx((alta - baixa) / (2 * h) * 0.01, rel=1e-6)


def test_preco_cresce_com_volatilidade(call):
    mais_vol = replace(call, vol=call.vol + 0.05)
    assert mais_vol.preco() > call.preco()


def test_tipo_invalido(params):
    from fxpricer import FXOption

    with pytest.raises(ValueError):
        FXOption(tipo="straddle", vol=0.14, **params)


def test_curva_pre_nos_vertices():
    curva = CurvaPre({21: 0.1475, 63: 0.1460, 126: 0.1440, 252: 0.1400})
    assert curva.taxa(63) == pytest.approx(0.1460, abs=1e-12)
    assert curva.df(126) == pytest.approx((1.1440) ** (-126 / 252), abs=1e-12)
    # interpolada fica entre os vértices vizinhos
    assert 0.1440 < curva.taxa(90) < 0.1460
