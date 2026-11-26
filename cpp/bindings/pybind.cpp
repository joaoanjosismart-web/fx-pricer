// Ligacao Python <-> C++ (pybind11). Gera o modulo `fxpricer._fxcore`.
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <stdexcept>
#include <string>
#include <vector>

#include "fxcore/fxcore.hpp"

namespace py = pybind11;
using namespace fxcore;

namespace {

OptionType parse_type(const std::string& s) {
    if (s == "call") return OptionType::Call;
    if (s == "put") return OptionType::Put;
    throw std::invalid_argument("tipo deve ser 'call' ou 'put'");
}

Payoff parse_payoff(const std::string& s) {
    if (s == "european") return Payoff::European;
    if (s == "asian_option") return Payoff::AsianOption;
    if (s == "asian_ndf") return Payoff::AsianNDF;
    if (s == "ndf_cap") return Payoff::NDFCap;
    throw std::invalid_argument("produto deve ser 'european', 'asian_option', 'asian_ndf' ou 'ndf_cap'");
}

OptionInput make_option(double spot, double strike, const std::string& tipo, int du, int dc, double taxa_pre,
                        double taxa_usd, double vol, double nocional) {
    OptionInput in;
    in.spot = spot;
    in.strike = strike;
    in.type = parse_type(tipo);
    in.du = du;
    in.dc = dc;
    in.taxa_pre = taxa_pre;
    in.taxa_usd = taxa_usd;
    in.vol = vol;
    in.notional = nocional;
    return in;
}

}  // namespace

PYBIND11_MODULE(_fxcore, m) {
    m.doc() = "Nucleo em C++ do fxpricer: formulas fechadas, Greeks e Monte Carlo multithread.";

    m.def("df_brl", &fxcore::df_brl, py::arg("taxa_pre"), py::arg("du"));
    m.def("df_usd", &fxcore::df_usd, py::arg("taxa_usd"), py::arg("dc"));
    m.def("forward", &fxcore::forward, py::arg("spot"), py::arg("taxa_pre"), py::arg("du"), py::arg("taxa_usd"),
          py::arg("dc"));

    m.def(
        "preco_opcao",
        [](double spot, double strike, const std::string& tipo, int du, int dc, double taxa_pre, double taxa_usd,
           double vol, double nocional) {
            return option_price(make_option(spot, strike, tipo, du, dc, taxa_pre, taxa_usd, vol, nocional));
        },
        py::arg("spot"), py::arg("strike"), py::arg("tipo"), py::arg("du"), py::arg("dc"), py::arg("taxa_pre"),
        py::arg("taxa_usd"), py::arg("vol"), py::arg("nocional") = 1.0);

    m.def(
        "greeks_opcao",
        [](double spot, double strike, const std::string& tipo, int du, int dc, double taxa_pre, double taxa_usd,
           double vol, double nocional) {
            const Greeks g =
                option_greeks(make_option(spot, strike, tipo, du, dc, taxa_pre, taxa_usd, vol, nocional));
            py::dict d;
            d["preco"] = g.price;
            d["delta"] = g.delta;
            d["gamma"] = g.gamma;
            d["vega_1vol"] = g.vega_1vol;
            d["theta_1dia"] = g.theta_1dia;
            d["rho_brl_1bp"] = g.rho_brl_1bp;
            d["rho_usd_1bp"] = g.rho_usd_1bp;
            return d;
        },
        py::arg("spot"), py::arg("strike"), py::arg("tipo"), py::arg("du"), py::arg("dc"), py::arg("taxa_pre"),
        py::arg("taxa_usd"), py::arg("vol"), py::arg("nocional") = 1.0);

    // O Monte Carlo libera o GIL: roda em varias threads sem travar o Python.
    m.def(
        "preco_mc",
        [](const std::string& produto, double strike, double spot, double forward_T, double vol,
           const std::vector<double>& tempos, double df_desconto, std::size_t n_caminhos, std::uint64_t seed,
           unsigned n_threads, const std::string& tipo, double cap, double nocional, bool compra) {
            McInput in;
            in.payoff = parse_payoff(produto);
            in.type = parse_type(tipo);
            in.strike = strike;
            in.cap = cap;
            in.notional = nocional;
            in.buy = compra;
            in.spot = spot;
            in.forward = forward_T;
            in.vol = vol;
            in.times = tempos;
            in.discount = df_desconto;
            in.n_paths = n_caminhos;
            in.seed = seed;
            in.n_threads = n_threads;

            McResult r;
            {
                py::gil_scoped_release liberar;
                r = price_mc(in);
            }
            py::dict d;
            d["preco"] = r.price;
            d["erro_padrao"] = r.std_error;
            d["ic95_inf"] = r.ci95_low;
            d["ic95_sup"] = r.ci95_high;
            d["n_caminhos"] = r.n_paths;
            return d;
        },
        py::arg("produto"), py::arg("strike"), py::arg("spot"), py::arg("forward_T"), py::arg("vol"),
        py::arg("tempos"), py::arg("df_desconto"), py::arg("n_caminhos") = 200000, py::arg("seed") = 42,
        py::arg("n_threads") = 0, py::arg("tipo") = "call", py::arg("cap") = 0.0, py::arg("nocional") = 1.0,
        py::arg("compra") = true);
}
