"""⚡ Ponte para o núcleo C++ (`_fxcore`), com fallback para NumPy.

Se o módulo compilado não existir, `CPP_DISPONIVEL` fica False e as
funções `*_cpp` levantam RuntimeError. O restante do pacote segue funcionando.
"""

from __future__ import annotations

try:  # módulo gerado por: cmake -S cpp -B build && cmake --build build
    from . import _fxcore

    CPP_DISPONIVEL = True
except ImportError:  # pragma: no cover
    _fxcore = None
    CPP_DISPONIVEL = False


def _exigir() -> None:
    if not CPP_DISPONIVEL:
        raise RuntimeError(
            "Módulo C++ não compilado. Rode: cmake -S cpp -B build && cmake --build build"
        )


def preco_opcao_cpp(spot, strike, tipo, du, dc, taxa_pre, taxa_usd, vol, nocional=1.0) -> float:
    _exigir()
    return _fxcore.preco_opcao(spot, strike, tipo, du, dc, taxa_pre, taxa_usd, vol, nocional)


def greeks_opcao_cpp(spot, strike, tipo, du, dc, taxa_pre, taxa_usd, vol, nocional=1.0) -> dict:
    _exigir()
    return _fxcore.greeks_opcao(spot, strike, tipo, du, dc, taxa_pre, taxa_usd, vol, nocional)


def preco_mc_cpp(
    produto: str,
    strike: float,
    spot: float,
    forward_T: float,
    vol: float,
    tempos,
    df_desconto: float,
    n_caminhos: int = 200_000,
    seed: int = 42,
    n_threads: int = 0,
    tipo: str = "call",
    cap: float = 0.0,
    nocional: float = 1.0,
    compra: bool = True,
) -> dict:
    """Monte Carlo multithread em C++. `produto`: european, asian_option, asian_ndf, ndf_cap."""
    _exigir()
    return _fxcore.preco_mc(
        produto, strike, spot, forward_T, vol, list(map(float, tempos)), df_desconto,
        n_caminhos, seed, n_threads, tipo, cap, nocional, compra,
    )
