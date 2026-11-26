// Benchmark do Monte Carlo em C++ puro (sem Python).
#include <chrono>
#include <cstdio>
#include <thread>
#include <vector>

#include "fxcore/fxcore.hpp"

using namespace fxcore;

static double seconds(const McInput& in) {
    const auto t0 = std::chrono::steady_clock::now();
    const McResult r = price_mc(in);
    const auto t1 = std::chrono::steady_clock::now();
    (void)r;
    return std::chrono::duration<double>(t1 - t0).count();
}

int main() {
    const int du = 63, dc = 91;
    const double pre = 0.145, usd = 0.043, spot = 5.40, vol = 0.14;

    McInput in;
    in.strike = 5.45;
    in.spot = spot;
    in.forward = forward(spot, pre, du, usd, dc);
    in.vol = vol;
    in.discount = df_brl(pre, du);
    in.n_paths = 2'000'000;

    const double T = dc / 365.0;
    std::vector<double> times(du);
    for (int i = 0; i < du; ++i) times[i] = T * (i + 1) / du;

    const unsigned hw = std::max(1u, std::thread::hardware_concurrency());
    std::printf("%-28s %10s %14s\n", "produto", "threads", "tempo (s)");

    in.payoff = Payoff::European;
    in.times = {T};
    for (unsigned th : {1u, hw}) {
        in.n_threads = th;
        std::printf("%-28s %10u %14.3f\n", "europeia (1 fixing)", th, seconds(in));
    }

    in.payoff = Payoff::AsianOption;
    in.times = times;
    for (unsigned th : {1u, hw}) {
        in.n_threads = th;
        std::printf("%-28s %10u %14.3f\n", "asiatica (63 fixings)", th, seconds(in));
    }
    return 0;
}
