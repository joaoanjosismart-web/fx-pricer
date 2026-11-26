"""⚡ Benchmark: Monte Carlo em NumPy vs núcleo C++ (mesmo produto, mesmos parâmetros)."""

import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import fxpricer as fx

P = dict(spot=5.40, strike=5.45, du=63, dc=91, taxa_pre=0.145, taxa_usd=0.043, vol=0.14)
T = P["dc"] / 365
F = fx.forward(P["spot"], P["taxa_pre"], P["du"], P["taxa_usd"], P["dc"])
DF = fx.df_brl(P["taxa_pre"], P["du"])
TEMPOS = np.linspace(T / P["du"], T, P["du"])  # fixing diário (asiática)
N = 1_000_000


def medir(f, rep=3):
    ts = []
    for _ in range(rep):
        t0 = time.perf_counter()
        r = f()
        ts.append(time.perf_counter() - t0)
    return min(ts), r


if not fx.CPP_DISPONIVEL:
    raise SystemExit("⚠️ módulo C++ não compilado")

t_np, r_np = medir(lambda: fx.preco_mc(
    fx.payoff_asiatica_opcao(P["strike"]), P["spot"], F, P["vol"], TEMPOS, DF,
    n_caminhos=N, barra=False))
t_c1, r_c1 = medir(lambda: fx.preco_mc_cpp(
    "asian_option", P["strike"], P["spot"], F, P["vol"], TEMPOS, DF, N, n_threads=1))
t_cn, r_cn = medir(lambda: fx.preco_mc_cpp(
    "asian_option", P["strike"], P["spot"], F, P["vol"], TEMPOS, DF, N, n_threads=0))

print(f"{'motor':<22}{'tempo (s)':>10}{'preço':>12}{'erro pad.':>12}{'speedup':>9}")
for nome, t, r in [("NumPy", t_np, r_np), ("C++ 1 thread", t_c1, r_c1), ("C++ multithread", t_cn, r_cn)]:
    print(f"{nome:<22}{t:>10.3f}{r['preco']:>12.6f}{r['erro_padrao']:>12.6f}{t_np / t:>8.1f}x")

fig, ax = plt.subplots(figsize=(7, 3.8))
nomes = ["NumPy", "C++ (1 thread)", "C++ (multithread)"]
tempos = [t_np, t_c1, t_cn]
barras = ax.bar(nomes, tempos, color=["#6b7280", "#2563eb", "#16a34a"])
for b, t in zip(barras, tempos):
    ax.text(b.get_x() + b.get_width() / 2, t, f"{t:.2f}s\n({t_np / t:.1f}x)", ha="center", va="bottom")
ax.set_ylabel("Tempo (s)")
ax.set_title(f"Opção asiática USD/BRL: {N:,} caminhos, {len(TEMPOS)} fixings".replace(",", "."))
ax.set_ylim(0, t_np * 1.25)
fig.tight_layout()
fig.savefig("docs/benchmark.png", dpi=150)
print("📈 docs/benchmark.png salvo")
