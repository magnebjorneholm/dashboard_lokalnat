"""
decomp — the parametrised cost-component decomposition of the new-benchmarking outcome.

This package replaces the old hard-coded s4/s5 pair. The decomposition is the same Shapley
machinery run over a *parameter grid*:

    outcome      ∈ {"req", "eff"}        # signed two-sided requirement (pp) | capped DEA efficiency
    outlier_mode ∈ {"dynamic", "frozen"} # re-detect outliers per subset | freeze the full-model set

Players (7), each adding its post on top of the phase-1 baseline (opexp_dea + capex_unadj):
    losses, grid_subscription, grid_connection, feed_in, capacity_reserve, capex_adj, cable.

The frontier payable post is opexp_dea (Ei's raw OPEXp), NEVER controllable_cost_average —
see new_benchmarking_model/totex/totex.py. The requirement base stays controllable on the kr
side, which the decomposition does not touch (it works in pp / efficiency units, not kr).

Entry points:
    players.subset_input / subset_outputs   — compose one subset's DEA spec (pure arithmetic)
    engine.run_decomposition(...)           — one (outcome, outlier_mode) run → result dataclass
    io.write_run(...)                        — persist a result under out/decomp_<outcome>/<mode>/
"""
