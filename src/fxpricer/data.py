"""🌐 Coleta de dados de mercado (fontes públicas).

- PTAX (USD/BRL): API Olinda do Banco Central.
- SOFR: arquivo CSV público do FRED (Federal Reserve Bank of St. Louis).
- Curva pré (DI x pré): carregada de um CSV que você baixa da B3
  (Taxas Referenciais). A B3 não tem uma API pública estável, por isso
  esta função lê um arquivo local com colunas `du` e `taxa`.
"""

from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd
import requests

_URL_PTAX = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
    "?@dataInicial='{ini}'&@dataFinalCotacao='{fim}'"
    "&$top=10000&$format=json&$select=cotacaoVenda,dataHoraCotacao"
)
_URL_SOFR = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR"


def baixar_ptax(inicio: date, fim: date, timeout: int = 30) -> pd.Series:
    """PTAX de venda (último boletim de cada dia) entre `inicio` e `fim`."""
    url = _URL_PTAX.format(ini=inicio.strftime("%m-%d-%Y"), fim=fim.strftime("%m-%d-%Y"))
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:  # pragma: no cover (depende de rede)
        raise RuntimeError(f"Não foi possível baixar a PTAX do Banco Central: {e}") from e
    df = pd.DataFrame(resp.json()["value"])
    if df.empty:
        raise RuntimeError("A API do Banco Central não devolveu dados para o período.")
    df["dataHoraCotacao"] = pd.to_datetime(df["dataHoraCotacao"])
    serie = (
        df.sort_values("dataHoraCotacao")
        .groupby(df["dataHoraCotacao"].dt.date)["cotacaoVenda"]
        .last()
    )
    serie.index = pd.to_datetime(serie.index)
    serie.name = "ptax"
    return serie


def baixar_sofr(timeout: int = 30) -> float:
    """Última SOFR disponível, como taxa a.a. em decimal (ex.: 0.043)."""
    try:
        resp = requests.get(_URL_SOFR, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:  # pragma: no cover (depende de rede)
        raise RuntimeError(f"Não foi possível baixar a SOFR do FRED: {e}") from e
    df = pd.read_csv(io.StringIO(resp.text))
    col_valor = df.columns[1]
    serie = pd.to_numeric(df[col_valor], errors="coerce").dropna()
    return float(serie.iloc[-1]) / 100.0


def carregar_curva_pre_csv(caminho: str) -> dict[int, float]:
    """Lê vértices da curva pré de um CSV com colunas `du` e `taxa` (em % a.a.).

    Devolve `{dias_uteis: taxa_decimal}`, pronto para `CurvaPre(...)`.
    """
    df = pd.read_csv(caminho)
    df.columns = [c.strip().lower() for c in df.columns]
    return {int(r.du): float(r.taxa) / 100.0 for r in df.itertuples()}


def vol_historica(ptax: pd.Series, janela: int = 63) -> float:
    """Volatilidade anualizada (252 dias) dos retornos log da PTAX nos últimos `janela` dias.

    Serve como aproximação inicial da volatilidade implícita, que é difícil de
    obter de graça para USD/BRL.
    """
    retornos = np.log(ptax).diff().dropna().tail(janela)
    return float(retornos.std(ddof=1) * np.sqrt(252))
