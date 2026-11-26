#include "fxcore/fxcore.hpp"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <stdexcept>
#include <thread>

namespace fxcore {

namespace {

constexpr double kInvSqrt2 = 0.70710678118654752440;
constexpr double kInvSqrt2Pi = 0.39894228040143267794;

// splitmix64: deriva uma semente independente para cada bloco de simulacao.
std::uint64_t splitmix64(std::uint64_t x) noexcept {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

// xoshiro256++: gerador rapido e de boa qualidade estatistica.
struct Xoshiro256pp {
    std::uint64_t s[4];
    explicit Xoshiro256pp(std::uint64_t seed) noexcept {
        for (auto& x : s) {
            seed = splitmix64(seed);
            x = seed;
        }
    }
    static std::uint64_t rotl(std::uint64_t x, int k) noexcept { return (x << k) | (x >> (64 - k)); }
    std::uint64_t next() noexcept {
        const std::uint64_t r = rotl(s[0] + s[3], 23) + s[0];
        const std::uint64_t t = s[1] << 17;
        s[2] ^= s[0];
        s[3] ^= s[1];
        s[1] ^= s[2];
        s[0] ^= s[3];
        s[2] ^= t;
        s[3] = rotl(s[3], 45);
        return r;
    }
    // uniforme em (0, 1), nunca zero
    double uniform() noexcept { return (static_cast<double>(next() >> 11) + 0.5) * (1.0 / 9007199254740992.0); }
};

// Preenche z[0..n) com N(0,1) por Box-Muller em lote (loops simples: o compilador vetoriza).
void fill_normals(Xoshiro256pp& rng, double* z, double* u1, double* u2, std::size_t n) noexcept {
    const std::size_t m = (n + 1) / 2;
    for (std::size_t i = 0; i < m; ++i) {
        u1[i] = rng.uniform();
        u2[i] = rng.uniform();
    }
    constexpr double kTwoPi = 6.28318530717958647692;
    for (std::size_t i = 0; i < m; ++i) {
        const double r = std::sqrt(-2.0 * std::log(u1[i]));
        const double a = kTwoPi * u2[i];
        z[2 * i] = r * std::cos(a);
        z[2 * i + 1] = r * std::sin(a);
    }
}

void validate(const OptionInput& in) {
    if (!(in.spot > 0.0) || !(in.strike > 0.0)) throw std::invalid_argument("spot e strike devem ser positivos");
    if (!(in.vol > 0.0)) throw std::invalid_argument("vol deve ser positiva");
    if (in.dc <= 0) throw std::invalid_argument("dc deve ser positivo");
}

struct BlockStat {
    double sum = 0.0;
    double sum2 = 0.0;
    std::size_t n = 0;
};

}  // namespace

double norm_cdf(double x) noexcept { return 0.5 * std::erfc(-x * kInvSqrt2); }
double norm_pdf(double x) noexcept { return kInvSqrt2Pi * std::exp(-0.5 * x * x); }

double df_brl(double taxa_pre, int du) { return std::pow(1.0 + taxa_pre, -static_cast<double>(du) / 252.0); }
double df_usd(double taxa_usd, int dc) { return 1.0 / (1.0 + taxa_usd * static_cast<double>(dc) / 360.0); }

double forward(double spot, double taxa_pre, int du, double taxa_usd, int dc) {
    return spot * df_usd(taxa_usd, dc) / df_brl(taxa_pre, du);
}

// ---- opcao --------------------------------------------------------------------

double option_price(const OptionInput& in) {
    validate(in);
    const double T = static_cast<double>(in.dc) / 365.0;
    const double F = forward(in.spot, in.taxa_pre, in.du, in.taxa_usd, in.dc);
    const double DF = df_brl(in.taxa_pre, in.du);
    const double sig = in.vol * std::sqrt(T);
    const double d1 = (std::log(F / in.strike) + 0.5 * in.vol * in.vol * T) / sig;
    const double d2 = d1 - sig;
    double p;
    if (in.type == OptionType::Call) {
        p = DF * (F * norm_cdf(d1) - in.strike * norm_cdf(d2));
    } else {
        p = DF * (in.strike * norm_cdf(-d2) - F * norm_cdf(-d1));
    }
    return p * in.notional;
}

Greeks option_greeks(const OptionInput& in) {
    validate(in);
    const double T = static_cast<double>(in.dc) / 365.0;
    const double sqrtT = std::sqrt(T);
    const double F = forward(in.spot, in.taxa_pre, in.du, in.taxa_usd, in.dc);
    const double DFb = df_brl(in.taxa_pre, in.du);
    const double DFu = df_usd(in.taxa_usd, in.dc);
    const double d1 = (std::log(F / in.strike) + 0.5 * in.vol * in.vol * T) / (in.vol * sqrtT);

    Greeks g;
    g.price = option_price(in);
    g.delta = (in.type == OptionType::Call ? DFu * norm_cdf(d1) : -DFu * norm_cdf(-d1)) * in.notional;
    g.gamma = DFu * norm_pdf(d1) / (in.spot * in.vol * sqrtT) * in.notional;
    g.vega_1vol = DFb * F * norm_pdf(d1) * sqrtT * 0.01 * in.notional;

    if (in.du > 1 && in.dc > 1) {
        OptionInput amanha = in;
        amanha.du -= 1;
        amanha.dc -= 1;
        g.theta_1dia = option_price(amanha) - g.price;
    }
    OptionInput alta_brl = in;
    alta_brl.taxa_pre += 0.0001;
    g.rho_brl_1bp = option_price(alta_brl) - g.price;
    OptionInput alta_usd = in;
    alta_usd.taxa_usd += 0.0001;
    g.rho_usd_1bp = option_price(alta_usd) - g.price;
    return g;
}

// ---- Monte Carlo ----------------------------------------------------------------

McResult price_mc(const McInput& in) {
    if (in.times.empty()) throw std::invalid_argument("times nao pode ser vazio");
    if (!(in.spot > 0.0) || !(in.forward > 0.0)) throw std::invalid_argument("spot e forward devem ser positivos");
    if (!(in.vol > 0.0)) throw std::invalid_argument("vol deve ser positiva");
    if (in.n_paths == 0) throw std::invalid_argument("n_paths deve ser positivo");
    double anterior = 0.0;
    for (double t : in.times) {
        if (!(t > anterior)) throw std::invalid_argument("times deve ser estritamente crescente e positivo");
        anterior = t;
    }

    const std::size_t n_obs = in.times.size();
    const double T = in.times.back();
    const double mu = std::log(in.forward / in.spot) / T;  // E[S_t] = S * exp(mu * t)

    std::vector<double> drift(n_obs), diff(n_obs);
    double t_prev = 0.0;
    for (std::size_t i = 0; i < n_obs; ++i) {
        const double dt = in.times[i] - t_prev;
        drift[i] = (mu - 0.5 * in.vol * in.vol) * dt;
        diff[i] = in.vol * std::sqrt(dt);
        t_prev = in.times[i];
    }

    const double sign = in.buy ? 1.0 : -1.0;
    const bool is_call = in.type == OptionType::Call;
    auto payoff_of = [&](double s_last, double media) -> double {
        switch (in.payoff) {
            case Payoff::European:
                return in.notional * (is_call ? std::max(s_last - in.strike, 0.0) : std::max(in.strike - s_last, 0.0));
            case Payoff::AsianOption:
                return in.notional * (is_call ? std::max(media - in.strike, 0.0) : std::max(in.strike - media, 0.0));
            case Payoff::AsianNDF:
                return sign * in.notional * (media - in.strike);
            case Payoff::NDFCap:
                return sign * in.notional * (std::min(s_last, in.cap) - in.strike);
        }
        return 0.0;
    };

    constexpr std::size_t kBlockPairs = 2048;
    const std::size_t n_pairs = (in.n_paths + 1) / 2;
    const std::size_t n_blocks = (n_pairs + kBlockPairs - 1) / kBlockPairs;
    std::vector<BlockStat> blocks(n_blocks);

    std::atomic<std::size_t> next{0};
    auto worker = [&]() {
        std::vector<double> z(n_obs + 1), u1(n_obs + 1), u2(n_obs + 1), ea(n_obs), eb(n_obs);
        const double inv = 1.0 / static_cast<double>(n_obs);
        for (;;) {
            const std::size_t b = next.fetch_add(1, std::memory_order_relaxed);
            if (b >= n_blocks) break;
            Xoshiro256pp rng(in.seed ^ splitmix64(static_cast<std::uint64_t>(b) + 1));
            const std::size_t first = b * kBlockPairs;
            const std::size_t count = std::min(kBlockPairs, n_pairs - first);
            BlockStat st;
            for (std::size_t k = 0; k < count; ++k) {
                fill_normals(rng, z.data(), u1.data(), u2.data(), n_obs);
                for (std::size_t i = 0; i < n_obs; ++i) {
                    ea[i] = std::exp(drift[i] + diff[i] * z[i]);
                    eb[i] = std::exp(drift[i] - diff[i] * z[i]);
                }
                double sa = in.spot, sb = in.spot, acc_a = 0.0, acc_b = 0.0;
                for (std::size_t i = 0; i < n_obs; ++i) {
                    sa *= ea[i];
                    sb *= eb[i];
                    acc_a += sa;
                    acc_b += sb;
                }
                const double par = 0.5 * (payoff_of(sa, acc_a * inv) + payoff_of(sb, acc_b * inv));
                st.sum += par;
                st.sum2 += par * par;
                ++st.n;
            }
            blocks[b] = st;
        }
    };

    unsigned n_threads = in.n_threads != 0 ? in.n_threads : std::thread::hardware_concurrency();
    n_threads = std::max(1u, std::min<unsigned>(n_threads, static_cast<unsigned>(n_blocks)));
    if (n_threads == 1) {
        worker();
    } else {
        std::vector<std::thread> pool;
        pool.reserve(n_threads);
        for (unsigned t = 0; t < n_threads; ++t) pool.emplace_back(worker);
        for (auto& th : pool) th.join();
    }

    // Reducao na ordem dos blocos: resultado identico para qualquer n de threads.
    double sum = 0.0, sum2 = 0.0;
    std::size_t n = 0;
    for (const auto& st : blocks) {
        sum += st.sum;
        sum2 += st.sum2;
        n += st.n;
    }
    const double nd = static_cast<double>(n);
    const double media = sum / nd;
    const double var = std::max(sum2 / nd - media * media, 0.0);
    const double erro = std::sqrt(var / nd);

    McResult r;
    r.price = in.discount * media;
    r.std_error = in.discount * erro;
    r.ci95_low = r.price - 1.96 * r.std_error;
    r.ci95_high = r.price + 1.96 * r.std_error;
    r.n_paths = 2 * n;
    return r;
}

}  // namespace fxcore
