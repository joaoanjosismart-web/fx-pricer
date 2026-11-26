// fxcore: nucleo em C++17 para precificacao de NDF e opcoes de USD/BRL.
//
// Convencoes (iguais as do pacote Python):
//  - BRL: taxa pre efetiva a.a., base 252 dias uteis.
//  - USD: taxa simples a.a., base 360 dias corridos.
//  - Tempo de volatilidade: T = dias corridos / 365.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace fxcore {

enum class OptionType { Call, Put };
enum class Payoff { European, AsianOption, AsianNDF, NDFCap };

// ---- utilitarios ----------------------------------------------------------
double norm_cdf(double x) noexcept;
double norm_pdf(double x) noexcept;

// ---- curvas e forward -----------------------------------------------------
double df_brl(double taxa_pre, int du);
double df_usd(double taxa_usd, int dc);
double forward(double spot, double taxa_pre, int du, double taxa_usd, int dc);

// ---- opcao europeia (Garman-Kohlhagen na forma de Black-76) ----------------
struct OptionInput {
    double spot = 0.0;
    double strike = 0.0;
    OptionType type = OptionType::Call;
    int du = 0;  // dias uteis
    int dc = 0;  // dias corridos
    double taxa_pre = 0.0;
    double taxa_usd = 0.0;
    double vol = 0.0;
    double notional = 1.0;
};

struct Greeks {
    double price = 0.0;
    double delta = 0.0;
    double gamma = 0.0;
    double vega_1vol = 0.0;    // por 1 ponto de volatilidade (0,01)
    double theta_1dia = 0.0;   // variacao ao passar 1 dia util
    double rho_brl_1bp = 0.0;  // +1 bp na taxa pre
    double rho_usd_1bp = 0.0;  // +1 bp na taxa USD
};

double option_price(const OptionInput& in);
Greeks option_greeks(const OptionInput& in);

// ---- Monte Carlo ------------------------------------------------------------
struct McInput {
    Payoff payoff = Payoff::European;
    OptionType type = OptionType::Call;  // usado em European e AsianOption
    double strike = 0.0;
    double cap = 0.0;  // usado em NDFCap
    double notional = 1.0;
    bool buy = true;  // usado em AsianNDF e NDFCap (compra de USD)

    double spot = 0.0;
    double forward = 0.0;           // forward ate o ultimo fixing
    double vol = 0.0;
    std::vector<double> times;      // datas de observacao em anos, crescentes
    double discount = 1.0;          // fator de desconto em BRL ate a liquidacao

    std::size_t n_paths = 200000;
    std::uint64_t seed = 42;
    unsigned n_threads = 0;         // 0 = todos os nucleos disponiveis
};

struct McResult {
    double price = 0.0;
    double std_error = 0.0;
    double ci95_low = 0.0;
    double ci95_high = 0.0;
    std::size_t n_paths = 0;
};

// Preco por Monte Carlo com variaveis antiteticas.
// O resultado e deterministico para uma mesma semente, independente do
// numero de threads (cada bloco de caminhos usa um gerador proprio).
McResult price_mc(const McInput& in);

}  // namespace fxcore
