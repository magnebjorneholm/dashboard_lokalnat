"""
Modul: tidsserie_view.py

(1) Specifikation
- Egen flik "Tidsserie" som visar kapkost i MSEK (2022), helår (H1+H2) för 2024–2027.
- Kontroller: nät (single/multi), år (multi), toggles: ord/tail-uppdelning, scenarioöverlagring.
- KPI-rad (senaste valda året): total MSEK, Δ mot föregående år (MSEK, %), tail-andel.
- Huvudgraf: dep vs return (stackat), valbar uppdelning ord/tail; scenario-linje kan överlagras.
- Δ-panel: årsvis dekomponering (Δdep, Δreturn, Δtotal).
- Tail-diagnos: tail-andel över tid + peak-markör.
- Kvalitetsnotis: varna diskret om komponenterna inte summerar till capcost_sum (>0,5 MSEK per halvår).

(2) Motivation
- Ger Ei en sammanhållen bild av nivå och förändring, med scenario i samma flik (ingen navigering).
- Replikerar Tab 3-skalning av räntedelarna per halvår innan helårssummering.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from kapitalbas.beräkningsfiler.tidsserie_backend import (
    TIME_LABEL_TO_CODE,
    YEAR_TO_CODES,
    normalize_halfyear,
    add_year_column,
    aggregate_year,
    filter_by_networks_and_years,
    to_msek,
    compute_kpi_year,
    delta_decomposition_year,
    tail_share_series,
    quality_report,
    scenario_scale_returns_halfyear,
    scenario_year_from_half,
    label_networks,
    ALL_COLS,
)

RECON_DEFAULT_PATH = "effektiviseringskrav/datafiler/reconciliation_id_network_firm_dmu.csv"
R_OLD_DEFAULT = 0.0453  # real, pre-tax – samma som i beräkningskedjan (Tab 3)


def _load_recon_df(path: str) -> Optional[pd.DataFrame]:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _id_label_mapping(df_half: pd.DataFrame, recon_path: Optional[str]) -> pd.DataFrame:
    ids = df_half[["id_network"]].drop_duplicates().sort_values("id_network")
    recon = _load_recon_df(recon_path) if recon_path else None
    return label_networks(ids, recon)


def _network_selector(df_half: pd.DataFrame, recon_path: Optional[str]) -> List[int]:
    labels = _id_label_mapping(df_half, recon_path)
    options = (
        labels.sort_values("id_network")
        .assign(option=lambda d: d["label"].fillna(d["id_network"].astype(str)))
    )
    default_ids = options["id_network"].head(3).tolist()  # rimlig default i prototyp
    selection = st.multiselect(
        "Välj nät (id/etikett)",
        options=options.to_dict(orient="records"),
        default=[options.to_dict(orient="records")[0]] if len(options) else [],
        format_func=lambda r: r["option"],
        key="ts_networks",
    )
    if not selection:
        return default_ids
    return [r["id_network"] for r in selection]


def _year_selector() -> List[int]:
    year_options = list(YEAR_TO_CODES.keys())
    default = year_options
    years = st.multiselect(
        "Välj år",
        options=year_options,
        default=default,
        key="ts_years",
    )
    return [int(y) for y in years] if years else year_options


def _scenario_controls() -> Optional[float]:
    show = st.toggle("Visa scenario-överlagring (skala räntedelar)", value=False, key="ts_show_scenario")
    if not show:
        return None
    c1, c2 = st.columns([1, 1])
    with c1:
        st.number_input("Gammal real WACC (r_old)", value=R_OLD_DEFAULT, format="%.4f", step=0.0001, key="ts_r_old")
    with c2:
        r_new = st.number_input("Ny real WACC (r_new)", value=R_OLD_DEFAULT, format="%.4f", step=0.0001, key="ts_r_new")
    return float(st.session_state.get("ts_r_new", R_OLD_DEFAULT))


def _prep_year_tables(df_capcost: pd.DataFrame, networks: Sequence[int], years: Sequence[int]):
    # (1) Summera till halvårsnivå (id_network, time)
    half = normalize_halfyear(df_capcost)
    # (2) Filtrera på valda nät/år (år appliceras via time->year)
    half_f = filter_by_networks_and_years(half, networks=networks, years=years)
    # (3) Helårssummering (id_network, year)
    year_tbl = aggregate_year(half_f)
    return half_f, year_tbl


def _kpi_row(year_tbl: pd.DataFrame, years: Sequence[int]):
    kpi = compute_kpi_year(year_tbl, years)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label=f"Total kapkost {kpi['latest_year']} (MSEK, 2022)", value=None if math.isnan(kpi["capcost_msek"]) else f"{kpi['capcost_msek']:.1f}")
    with c2:
        delta_val = "–" if (kpi["delta_msek"] is None or math.isnan(kpi["delta_msek"])) else f"{kpi['delta_msek']:.1f}"
        delta_pct = "" if (kpi["delta_pct"] is None or math.isnan(kpi["delta_pct"])) else f" ({kpi['delta_pct']:.1f}%)"
        st.metric(label="Δ mot föregående år (MSEK)", value=delta_val + delta_pct)
    with c3:
        tail = "–" if (kpi["tail_share_pct"] is None or math.isnan(kpi["tail_share_pct"])) else f"{kpi['tail_share_pct']:.1f}%"
        st.metric(label="Tail-andel (dep+ränta)", value=tail)


def _main_chart(year_tbl: pd.DataFrame, show_split: bool, scenario_year: Optional[pd.DataFrame]):
    """Linjegraf med tydlig legend.
    - Default: två linjer (Dep total, Ränta total)
    - Uppdelat läge: fyra linjer (Dep ord/tail, Ränta ord/tail)
    - Scenario: läggs som 'Scenario: Total' (streckad) och hamnar i legend.
    """
    # 1) Årsvis totals (MSEK)
    annual = year_tbl.groupby("year", dropna=False)[ALL_COLS].sum(min_count=1).reset_index()
    annual = to_msek(annual, ALL_COLS)
    annual["dep_total"] = annual["dep_ord"] + annual["dep_tail"]
    annual["return_total"] = annual["return_ord"] + annual["return_tail"]

    # 2) Välj serier + long-format för legend
    if show_split:
        plot_cols = ["dep_ord", "dep_tail", "return_ord", "return_tail"]
        labels = {"dep_ord":"Dep ord","dep_tail":"Dep tail","return_ord":"Ränta ord","return_tail":"Ränta tail"}
    else:
        plot_cols = ["dep_total", "return_total"]
        labels = {"dep_total":"Dep total","return_total":"Ränta total"}

    base_long = annual.melt(id_vars=["year"], value_vars=plot_cols, var_name="serie", value_name="msek")
    base_long["serie_label"] = base_long["serie"].map(labels)

    # 3) Scenario som egen serie i samma long-Df (för att få legend)
    if scenario_year is not None and len(scenario_year):
        scen = scenario_year.groupby("year", dropna=False)["capcost_sum_new"].sum(min_count=1).reset_index()
        scen = scen.assign(msek=scen["capcost_sum_new"] / 1000.0,
                           serie_label="Scenario: Total")[["year","msek","serie_label"]]
        long = pd.concat([base_long[["year","msek","serie_label"]], scen], ignore_index=True)
    else:
        long = base_long[["year","msek","serie_label"]]

    # 4) Linjegraf + legend till höger + starkare kontrast
    base = alt.Chart(long).encode(x=alt.X("year:O", title="År"))
    chart = base.mark_line(point=True).encode(
        y=alt.Y("msek:Q", title="MSEK"),
        color=alt.Color("serie_label:N", title="", legend=alt.Legend(orient="right"),
                        scale=alt.Scale(scheme="tableau10")),
        # Gör scenariolinjen streckad/tjockare
        strokeDash=alt.condition(alt.FieldEqualPredicate(field="serie_label", equal="Scenario: Total"),
                                 alt.value([6,3]), alt.value([1,0])),
        size=alt.condition(alt.FieldEqualPredicate(field="serie_label", equal="Scenario: Total"),
                           alt.value(3), alt.value(2)),
        tooltip=["year","serie_label", alt.Tooltip("msek:Q", format=".1f")],
    )
    st.altair_chart(chart.interactive().properties(height=340), use_container_width=True)



def _delta_panel(year_tbl: pd.DataFrame):
    delta = delta_decomposition_year(year_tbl)
    if not len(delta):
        return
    # Hitta största hopp (absolut)
    d_abs = delta.set_index("year")["d_total"].abs()
    peak_year = int(d_abs.idxmax()) if len(d_abs) else None
    peak_val = float(delta.loc[delta["year"] == peak_year, "d_total"].values[0]) if peak_year else np.nan

    st.subheader("Årsvis förändring (Δ)")
    st.dataframe(delta.rename(columns={"d_dep": "Δ Dep (MSEK)", "d_return": "Δ Ränta (MSEK)", "d_total": "Δ Total (MSEK)"}), use_container_width=True)

    if not math.isnan(peak_val):
        driver = "dep" if abs(float(delta.loc[delta["year"] == peak_year, "d_dep"])) >= abs(float(delta.loc[delta["year"] == peak_year, "d_return"])) else "ränta"
        st.caption(f"Största hopp: {peak_year} (Δ total {peak_val:.1f} MSEK), primärt drivet av {driver}.")


def _tail_chart(year_tbl: pd.DataFrame):
    share = tail_share_series(year_tbl)
    st.subheader("Tail-andel över tid")
    peak_row = share.loc[share["tail_share_pct"].idxmax()] if len(share) else None
    chart = alt.Chart(share).mark_line(point=True).encode(
        x=alt.X("year:O", title="År"), y=alt.Y("tail_share_pct:Q", title="%"), tooltip=["year", "tail_share_pct"],
    )
    st.altair_chart(chart.properties(height=260), use_container_width=True)
    if peak_row is not None and np.isfinite(peak_row["tail_share_pct"]):
        st.caption(f"Peak tail-andel: {int(peak_row['year'])} ({float(peak_row['tail_share_pct']):.1f}%).")


def _quality_note(half_tbl: pd.DataFrame):
    rep = quality_report(half_tbl, tol_msek=0.5)
    if rep.mismatched_rows > 0:
        st.info(
            f"Kvalitetsnotis: {rep.mismatched_rows} halvårsrader avviker (>0,5 MSEK). Max |diff| = {rep.max_abs_diff_tkr/1000:.2f} MSEK."
        )


def show_tidsserie(capcost_df: Optional[pd.DataFrame] = None, recon_path: Optional[str] = RECON_DEFAULT_PATH):
    """Rendera Tidsserie-fliken. Om capcost_df inte angivs, hämtas st.session_state["capcost_a"]."""
    st.header("Tidsserie – Kapitalkostnader (MSEK, 2022)")

    # 1) Hämta data
    if capcost_df is None:
        if "capcost_a" not in st.session_state:
            st.error("capcost_a saknas i session_state. Läs in data via data_loader först.")
            return
        capcost_df = st.session_state["capcost_a"]

    # 2) Kontroller (vänsterkolumn)
    with st.sidebar:
        st.subheader("Filter")
        networks = _network_selector(capcost_df, recon_path)
        years = _year_selector()
        show_split = st.toggle("Visa ord/tail-uppdelning", value=False, key="ts_split")
        r_new = _scenario_controls()

    # 3) Förbered aggregerade tabeller
    half_tbl, year_tbl = _prep_year_tables(capcost_df, networks, years)

    # 4) KPI-rad
    _kpi_row(year_tbl, years)

    # 5) Scenario (valfritt): skala räntor per halvår -> summera till år
    scenario_year = None
    if r_new is not None:
        try:
            half_scaled = scenario_scale_returns_halfyear(half_tbl, r_old=R_OLD_DEFAULT, r_new=r_new)
            scenario_year = scenario_year_from_half(half_scaled)
        except Exception as e:
            st.warning(f"Scenario kunde inte beräknas: {e}")

    # 6) Huvudgraf
    _main_chart(year_tbl, show_split=show_split, scenario_year=scenario_year)

    # 7) Δ-panel
    _delta_panel(year_tbl)

    # 8) Tail-diagnos
    _tail_chart(year_tbl)

    # 9) Kvalitetsnotis
    _quality_note(half_tbl)


# Om man vill köra modulen isolerat i utveckling
if __name__ == "__main__":
    st.write("Detta är en komponentmodul. Importera och kör show_tidsserie() från er huvudapp.")
