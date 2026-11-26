from dataclasses import replace

import pytest

from fxpricer import NDF


@pytest.fixture
def ndf(params):
    return NDF(nocional=1_000_000, **params)


def test_mtm_zero_quando_strike_igual_ao_forward(ndf):
    justo = replace(ndf, strike=ndf.forward())
    assert justo.valor_presente() == pytest.approx(0.0, abs=1e-6)


def test_mtm_vs_spot_coincide_no_spot_atual(ndf):
    assert ndf.mtm_vs_spot([ndf.spot])[0] == pytest.approx(ndf.valor_presente(), rel=1e-12)


def test_venda_tem_sinal_oposto(ndf):
    venda = replace(ndf, compra=False)
    assert venda.valor_presente() == pytest.approx(-ndf.valor_presente())


def test_forward_acima_do_spot_com_juro_brl_maior(ndf):
    # juro em BRL maior que em USD => forward acima do spot
    assert ndf.forward() > ndf.spot
    assert ndf.pontos_forward() > 0


def test_payoff_na_liquidacao(ndf):
    assert ndf.payoff(5.55) == pytest.approx(1_000_000 * (5.55 - 5.45))
