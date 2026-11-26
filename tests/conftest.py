import sys
from pathlib import Path

import pytest

# Permite rodar `pytest` sem instalar o pacote.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fxpricer import FXOption  # noqa: E402


@pytest.fixture
def params():
    return dict(
        spot=5.40,
        strike=5.45,
        du=63,
        dc=91,
        taxa_pre=0.145,
        taxa_usd=0.043,
    )


@pytest.fixture
def call(params):
    return FXOption(tipo="call", vol=0.14, **params)


@pytest.fixture
def put(params):
    return FXOption(tipo="put", vol=0.14, **params)
