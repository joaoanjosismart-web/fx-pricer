#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

#include "fxcore/fxcore.hpp"

using Catch::Approx;
using namespace fxcore;

namespace {

OptionInput base(OptionType t) {
    OptionInput in;
    in.spot = 5.40;
    in.strike = 5.45;
    in.type = t;
    in.du = 63;
    in.dc = 91;
    in.taxa_pre = 0.145;
    in.taxa_usd = 0.043;
    in.vol = 0.14;
    return in;
}

}  // namespace

TEST_CASE("forward e fatores de desconto batem com o Python") {
    // Valores de referencia gerados pela implementacao em Python.
    REQUIRE(df_brl(0.145, 63) == Approx(0.966715380570722).epsilon(1e-12));
    REQUIRE(df_usd(0.043, 91) == Approx(0.989247430017614).epsilon(1e-12));
    REQUIRE(forward(5.40, 0.145, 63, 0.043, 91) == Approx(5.52586234734508).epsilon(1e-12));
}

TEST_CASE("preco e Greeks da call batem com o Python") {
    const Greeks g = option_greeks(base(OptionType::Call));
    REQUIRE(g.price == Approx(0.187471820744095).epsilon(1e-10));
    REQUIRE(g.delta == Approx(0.585639045063896).epsilon(1e-10));
    REQUIRE(g.gamma == Approx(1.01756017059646).epsilon(1e-10));
    REQUIRE(g.vega_1vol == Approx(0.010356766446036).epsilon(1e-10));
    REQUIRE(g.theta_1dia == Approx(-0.00202260906245116).epsilon(1e-8));
    REQUIRE(g.rho_brl_1bp == Approx(6.49594003441778e-05).epsilon(1e-6));
    REQUIRE(g.rho_usd_1bp == Approx(-7.90689178642723e-05).epsilon(1e-6));
}

TEST_CASE("preco e delta da put batem com o Python") {
    const Greeks g = option_greeks(base(OptionType::Put));
    REQUIRE(g.price == Approx(0.114134522759412).epsilon(1e-10));
    REQUIRE(g.delta == Approx(-0.403608384953718).epsilon(1e-10));
}

TEST_CASE("paridade put-call: C - P = DF_brl * (F - K)") {
    const auto c = base(OptionType::Call);
    const auto p = base(OptionType::Put);
    const double esperado = df_brl(c.taxa_pre, c.du) * (forward(c.spot, c.taxa_pre, c.du, c.taxa_usd, c.dc) - c.strike);
    REQUIRE(option_price(c) - option_price(p) == Approx(esperado).margin(1e-12));
}

TEST_CASE("delta, gamma e vega conferem com diferencas finitas") {
    const auto c = base(OptionType::Call);
    const Greeks g = option_greeks(c);

    const double h = 1e-4;
    auto up = c, dn = c;
    up.spot += h;
    dn.spot -= h;
    REQUIRE(g.delta == Approx((option_price(up) - option_price(dn)) / (2 * h)).epsilon(1e-6));

    const double hg = 1e-3;
    auto gu = c, gd = c;
    gu.spot += hg;
    gd.spot -= hg;
    const double gamma_fd = (option_price(gu) - 2 * option_price(c) + option_price(gd)) / (hg * hg);
    REQUIRE(g.gamma == Approx(gamma_fd).epsilon(1e-4));

    const double hv = 1e-4;
    auto vu = c, vd = c;
    vu.vol += hv;
    vd.vol -= hv;
    REQUIRE(g.vega_1vol == Approx((option_price(vu) - option_price(vd)) / (2 * hv) * 0.01).epsilon(1e-6));
}

TEST_CASE("entradas invalidas geram excecao") {
    auto in = base(OptionType::Call);
    in.vol = -0.1;
    REQUIRE_THROWS_AS(option_price(in), std::invalid_argument);

    McInput mc;
    mc.spot = 5.4;
    mc.forward = 5.5;
    mc.vol = 0.14;
    mc.times = {};
    REQUIRE_THROWS_AS(price_mc(mc), std::invalid_argument);
    mc.times = {0.2, 0.1};  // nao crescente
    REQUIRE_THROWS_AS(price_mc(mc), std::invalid_argument);
}

namespace {

McInput mc_base(Payoff p, const std::vector<double>& times) {
    const auto c = base(OptionType::Call);
    McInput in;
    in.payoff = p;
    in.type = OptionType::Call;
    in.strike = c.strike;
    in.spot = c.spot;
    in.forward = forward(c.spot, c.taxa_pre, c.du, c.taxa_usd, c.dc);
    in.vol = c.vol;
    in.times = times;
    in.discount = df_brl(c.taxa_pre, c.du);
    in.n_paths = 400000;
    in.seed = 7;
    return in;
}

}  // namespace

TEST_CASE("Monte Carlo europeu confere com a formula fechada (4 erros padrao)") {
    const double T = 91.0 / 365.0;
    const auto r = price_mc(mc_base(Payoff::European, {T}));
    const double fechada = option_price(base(OptionType::Call));
    REQUIRE(std::abs(r.price - fechada) < 4.0 * r.std_error);
}

TEST_CASE("NDF asiatico tem valor esperado analitico") {
    const int n_obs = 12;
    const double T = 91.0 / 365.0;
    std::vector<double> tempos(n_obs);
    for (int i = 0; i < n_obs; ++i) tempos[i] = T * (i + 1) / n_obs;

    auto in = mc_base(Payoff::AsianNDF, tempos);
    in.seed = 11;
    const auto r = price_mc(in);

    const double mu = std::log(in.forward / in.spot) / T;
    double media_fwd = 0.0;
    for (double t : tempos) media_fwd += in.spot * std::exp(mu * t);
    media_fwd /= n_obs;
    const double esperado = in.discount * (media_fwd - in.strike);
    REQUIRE(std::abs(r.price - esperado) < 4.0 * r.std_error);
}

TEST_CASE("resultado identico para qualquer numero de threads") {
    const double T = 91.0 / 365.0;
    auto in = mc_base(Payoff::AsianOption, {T / 4, T / 2, 3 * T / 4, T});
    in.n_paths = 100000;

    in.n_threads = 1;
    const auto r1 = price_mc(in);
    in.n_threads = 4;
    const auto r4 = price_mc(in);
    REQUIRE(r1.price == r4.price);
    REQUIRE(r1.std_error == r4.std_error);
}

TEST_CASE("cap limita o ganho: preco com cap menor que sem cap") {
    const double T = 91.0 / 365.0;
    auto sem_cap = mc_base(Payoff::NDFCap, {T});
    sem_cap.cap = 1e9;  // cap inatingivel
    auto com_cap = sem_cap;
    com_cap.cap = sem_cap.strike * 1.02;
    REQUIRE(price_mc(com_cap).price < price_mc(sem_cap).price);
}
