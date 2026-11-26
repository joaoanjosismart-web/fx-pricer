import numpy as np
import pytest

from fxpricer import (
    payoff_asiatico_ndf,
    payoff_europeia,
    payoff_ndf_com_cap,
    preco_mc,
)


def _tempos(call, n_obs=1):
    """Datas de observação igualmente espaçadas até o vencimento."""
    return np.linspace(call.T / n_obs, call.T, n_obs)


def test_europeia_mc_bate_com_formula_fechada(call):
    r = preco_mc(
        payoff_europeia(call.strike, "call"),
        spot=call.spot,
        forward_T=call.forward,
        vol=call.vol,
        tempos=_tempos(call, 1),
        df_desconto=call.df_brl,
        n_caminhos=400_000,
        seed=7,
        barra=False,
    )
    # dentro de 4 erros padrão da fórmula fechada
    assert abs(r["preco"] - call.preco()) < 4 * r["erro_padrao"]


def test_asiatico_ndf_tem_valor_esperado_analitico(call):
    n_obs = 12
    tempos = _tempos(call, n_obs)
    K = call.strike
    r = preco_mc(
        payoff_asiatico_ndf(K, nocional=1.0),
        spot=call.spot,
        forward_T=call.forward,
        vol=call.vol,
        tempos=tempos,
        df_desconto=call.df_brl,
        n_caminhos=400_000,
        seed=11,
        barra=False,
    )
    # no modelo, E[S_t] = S * exp(mu * t), com mu = ln(F/S)/T
    mu = np.log(call.forward / call.spot) / call.T
    media_forwards = np.mean(call.spot * np.exp(mu * tempos))
    esperado = call.df_brl * (media_forwards - K)
    assert abs(r["preco"] - esperado) < 4 * r["erro_padrao"]


def test_cap_limita_o_ganho(call):
    cap = call.strike * 1.02
    caminhos = np.array([[call.strike * 1.10]])  # fixing muito acima do cap
    ganho = payoff_ndf_com_cap(call.strike, cap)(caminhos)[0]
    assert ganho == pytest.approx(cap - call.strike)


def test_resultado_reprodutivel_com_mesma_semente(call):
    args = dict(
        payoff=payoff_europeia(call.strike, "call"),
        spot=call.spot,
        forward_T=call.forward,
        vol=call.vol,
        tempos=_tempos(call, 1),
        df_desconto=call.df_brl,
        n_caminhos=20_000,
        seed=3,
        barra=False,
    )
    assert preco_mc(**args)["preco"] == preco_mc(**args)["preco"]
