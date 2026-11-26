"""🧮 fxpricer: precificação de NDF e opções de câmbio (USD/BRL)."""

from .calendario import dias_corridos, dias_uteis
from .curves import CurvaPre, df_brl, df_usd, forward
from .montecarlo import (
    payoff_asiatica_opcao,
    payoff_asiatico_ndf,
    payoff_europeia,
    payoff_ndf_com_cap,
    preco_mc,
    simular_trajetorias,
)
from .ndf import NDF
from .nativo import CPP_DISPONIVEL, greeks_opcao_cpp, preco_mc_cpp, preco_opcao_cpp
from .options import FXOption

__all__ = [
    "CPP_DISPONIVEL",
    "greeks_opcao_cpp",
    "preco_mc_cpp",
    "preco_opcao_cpp",
    "CurvaPre",
    "FXOption",
    "NDF",
    "df_brl",
    "df_usd",
    "dias_corridos",
    "dias_uteis",
    "forward",
    "payoff_asiatica_opcao",
    "payoff_asiatico_ndf",
    "payoff_europeia",
    "payoff_ndf_com_cap",
    "preco_mc",
    "simular_trajetorias",
]

__version__ = "0.1.0"
