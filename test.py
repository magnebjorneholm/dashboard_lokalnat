"""
Regumetrica Results Visualization Test v2
==========================================
Standalone test file to prototype module output visualizations.

Structure:
  1. DATA LAYER  -- fake data generators (swap for real data later)
  2. VIZ LAYER   -- chart-building functions (swap visualizations here)
  3. PAGE LAYOUT  -- Streamlit page with tabs matching real modules

Run:  streamlit run test.py

Changes v2:
  - Efficiency gauge -> histogram of 148 companies with truncation zones
  - Incentive simple waterfall -> pipeline waterfall (period total)
  - Per-year incentive: stacked bar + selectbox for year drill-down dumbbell
  - OPEX waterfall -> dumbbell chart (before/after with connector)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Tuple, Any

# =============================================================================
# CONSTANTS
# =============================================================================

COLORS = {
    "primary": "#2563EB",
    "primary_light": "#60A5FA",
    "primary_dark": "#1E40AF",
    "teal": "#0891B2",
    "teal_light": "#67E8F9",
    "violet": "#7C3AED",
    "emerald": "#059669",
    "emerald_light": "#6EE7B7",
    "orange": "#EA580C",
    "red": "#DC2626",
    "red_light": "#FCA5A5",
    "slate": "#64748B",
    "slate_light": "#CBD5E1",
    "bg_page": "#F8FAFC",
    "bg_card": "#FFFFFF",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",
}

C_CASE = COLORS["primary"]
C_CASE_LIGHT = COLORS["primary_light"]
C_BASELINE = COLORS["slate_light"]
C_BASELINE_DARK = COLORS["slate"]
C_ORD = COLORS["primary"]
C_TAIL = COLORS["teal"]
C_ORD_BL = COLORS["slate_light"]
C_TAIL_BL = "#A5B4C8"
C_POSITIVE = COLORS["emerald"]
C_NEGATIVE = COLORS["red"]
C_NEUTRAL = COLORS["slate"]

TIME_LABELS = {
    229: "2024H1", 230: "2024H2", 231: "2025H1", 232: "2025H2",
    233: "2026H1", 234: "2026H2", 235: "2027H1", 236: "2027H2",
}

CATEGORY_NAMES = {
    1: "Markarbeten/bygg (linje)", 2: "Annan ledn. (linje)",
    3: "Annan ledn. (omr.)", 4: "Annan luftledn. (linje)",
    5: "IT-system", 6: "Kabelskap",
    7: "Ledn. 220kV+ (linje)", 8: "Luftledn. 220kV+ (linje)",
    9: "Luftledn. (omr.)", 10: "Markarbeten 220kV+",
    11: "Markarbeten (omr.)", 12: "Matare",
    13: "Natstation", 14: "Shuntreaktor",
    15: "Styr/kontroll", 16: "Stallverk", 17: "Transformator",
}

LARGE_CATS = [9, 11, 13, 6, 16, 17, 15, 12]
MEDIUM_CATS = [3, 5, 1]
SMALL_CATS = [2, 4, 7, 8, 10, 14]


# =============================================================================
# DATA LAYER
# =============================================================================

def _make_rng(seed: int = 42) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_category_data(
    case_wacc: float = 0.0500, baseline_wacc: float = 0.0453,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = _make_rng()
    rows_bl, rows_case = [], []
    for cat_encode in CATEGORY_NAMES:
        if cat_encode in LARGE_CATS:
            base_nuav = rng.uniform(800_000, 3_500_000)
        elif cat_encode in MEDIUM_CATS:
            base_nuav = rng.uniform(100_000, 800_000)
        else:
            base_nuav = rng.uniform(5_000, 100_000)
        tail_ratio = rng.uniform(0.05, 0.25)
        for tc in TIME_LABELS:
            tf = 1 + (tc - 229) * 0.005
            n = rng.uniform(0.97, 1.03)
            nuav_ord_bl = base_nuav * tf * n
            nuav_tail_bl = base_nuav * tail_ratio * tf * rng.uniform(0.95, 1.05)
            dep_ord_bl = nuav_ord_bl * rng.uniform(0.008, 0.025)
            dep_tail_bl = nuav_tail_bl * rng.uniform(0.015, 0.04)
            ret_ord_bl = nuav_ord_bl * baseline_wacc / 2
            ret_tail_bl = nuav_tail_bl * baseline_wacc / 2
            rows_bl.append({"cat_encode": cat_encode, "time": tc,
                "nuav_ord": nuav_ord_bl, "nuav_tail": nuav_tail_bl,
                "dep_ord": dep_ord_bl, "dep_tail": dep_tail_bl,
                "return_ord": ret_ord_bl, "return_tail": ret_tail_bl})
            cs = rng.uniform(0.98, 1.04)
            rows_case.append({"cat_encode": cat_encode, "time": tc,
                "nuav_ord": nuav_ord_bl*cs, "nuav_tail": nuav_tail_bl*cs,
                "dep_ord": dep_ord_bl*cs, "dep_tail": dep_tail_bl*cs,
                "return_ord": nuav_ord_bl*cs*case_wacc/2,
                "return_tail": nuav_tail_bl*cs*case_wacc/2})
    return pd.DataFrame(rows_case), pd.DataFrame(rows_bl)


def generate_wacc_data() -> Dict[str, Any]:
    return {
        "input_method": "capm",
        "capm": {
            "3.1.1": {"label": "Debt ratio (S)", "case": 0.36, "baseline": 0.36, "fmt": "ratio"},
            "3.1.2": {"label": "Asset beta", "case": 0.40, "baseline": 0.37, "fmt": "ratio"},
            "3.1.3": {"label": "Risk-free rate (Rf)", "case": 0.0320, "baseline": 0.0287, "fmt": "pct"},
            "3.1.4": {"label": "Market risk premium", "case": 0.0668, "baseline": 0.0668, "fmt": "pct"},
            "3.1.5": {"label": "Credit risk premium", "case": 0.0114, "baseline": 0.0114, "fmt": "pct"},
            "3.1.6": {"label": "Tax rate", "case": 0.206, "baseline": 0.206, "fmt": "pct"},
            "3.1.7": {"label": "Inflation", "case": 0.0202, "baseline": 0.0202, "fmt": "pct"},
        },
        "derived": {
            "3.2.1": {"label": "Equity beta", "case": 0.59, "baseline": 0.54, "fmt": "ratio"},
            "3.2.2": {"label": "Cost of equity (Re)", "case": 0.0714, "baseline": 0.0645, "fmt": "pct"},
            "3.2.3": {"label": "Cost of debt (Rd)", "case": 0.0434, "baseline": 0.0401, "fmt": "pct"},
            "3.2.4": {"label": "WACC nominal pre-tax", "case": 0.0712, "baseline": 0.0664, "fmt": "pct"},
            "3.2.5": {"label": "WACC real pre-tax", "case": 0.0500, "baseline": 0.0453, "fmt": "pct"},
        },
    }


def generate_incentive_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    def _make_df(seed_offset=0):
        r = np.random.default_rng(99 + seed_offset)
        rows = []
        for y in [2024, 2025, 2026, 2027]:
            la = r.uniform(-15000, -5000)*1000; l = la*r.uniform(0.8, 1.0)
            ua = r.uniform(-8000, 5000)*1000; u = ua*r.uniform(0.7, 1.0)
            qp = r.uniform(-20000, -3000)*1000; qc = qp*r.uniform(0.85, 1.0); q = qc*r.uniform(0.9, 1.0)
            tp = l + u + q; t = tp*r.uniform(0.85, 1.0)
            ret = r.uniform(150000, 250000)*1000
            rows.append({"year": y, "loss_incentive_a": la, "loss_incentive": l,
                "util_incentive_a": ua, "util_incentive": u,
                "inc_inter": qp, "inter_incentive_a": qc, "inter_incentive": q,
                "total_before_agg_cap": tp, "incentive_total_year": t,
                "ret_period": ret, "max_adj": ret/3})
        df = pd.DataFrame(rows)
        td = df.select_dtypes(include="number").sum().to_dict(); td["year"] = "Total"
        return pd.concat([df, pd.DataFrame([td])], ignore_index=True)
    return _make_df(0), _make_df(5)


def generate_ait_aif_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    def _make_df(seed_offset=0):
        r = np.random.default_rng(77 + seed_offset)
        rows = []
        for y in [2024, 2025, 2026, 2027]:
            row = {"year": y}
            for ind in ["ait", "aif"]:
                for ann in ["o", "a"]:
                    for sni in range(1, 7):
                        sc = (1.0 if ind == "ait" else 0.4) * (2.0 if ann == "o" else 0.5) * (1.5 if sni == 5 else 0.5)
                        row[f"inc_{ind}_{ann}_{sni}"] = r.uniform(-5000, -500)*1000*sc
            rows.append(row)
        df = pd.DataFrame(rows)
        td = df.select_dtypes(include="number").sum().to_dict(); td["year"] = "Total"
        return pd.concat([df, pd.DataFrame([td])], ignore_index=True)
    return _make_df(0), _make_df(3)


def generate_opex_data() -> Tuple[Dict, Dict]:
    case_ir = {"Paverkbara_Periodsumma": 912_300, "Opaverkbara_Kostnader": 1_348_200,
        "Flexibilitetstjanster": 2_100, "Avbrottsersattning_12_24h": 850,
        "Avdrag_Statligt_Stod": 3_200, "Method_used": "TOTEX",
        "OPEX_Fore": 912_300, "OPEX_Effektivisering": 35_800, "OPEX_Efter": 876_500,
        "CAPEX_Fore": 769_900, "CAPEX_Effektivisering": 55_000, "CAPEX_Efter": 714_900,
        "OPEX_Andel": 0.62, "CAPEX_Andel": 0.38, "Lopande_Total": 2_268_600}
    baseline_ir = {"Paverkbara_Periodsumma": 877_800, "Opaverkbara_Kostnader": 1_348_200,
        "Flexibilitetstjanster": 2_100, "Avbrottsersattning_12_24h": 850,
        "Avdrag_Statligt_Stod": 3_200, "Method_used": "TOTEX",
        "OPEX_Fore": 877_800, "OPEX_Effektivisering": 30_500, "OPEX_Efter": 847_300,
        "CAPEX_Fore": 769_900, "CAPEX_Effektivisering": 55_000, "CAPEX_Efter": 714_900,
        "OPEX_Andel": 0.62, "CAPEX_Andel": 0.38, "Lopande_Total": 2_226_000}
    return case_ir, baseline_ir


def generate_efficiency_data() -> Dict[str, Any]:
    return {
        "params": {
            "trunkering_max": {"case": 0.30, "baseline": 0.30},
            "realiseringstid": {"case": 8, "baseline": 8},
            "kunddelning": {"case": 0.50, "baseline": 0.50},
            "outlier_krav": {"case": 0.01, "baseline": 0.01},
            "trunkering_min": {"case": 0.1624, "baseline": 0.1624},
        },
        "measures": {
            "efficiency": {"case": 0.823, "baseline": 0.847},
            "potential": {"case": 0.177, "baseline": 0.153},
            "potential_truncated": {"case": 0.177, "baseline": 0.153},
            "effkrav": {"case": 0.0385, "baseline": 0.0330},
            "super_efficiency": {"case": None, "baseline": None},
            "is_outlier": False,
        },
        "costs": {
            "opex_fore": {"case": 912_300, "baseline": 877_800},
            "opex_adj": {"case": 35_800, "baseline": 30_500},
            "opex_efter": {"case": 876_500, "baseline": 847_300},
            "capex_fore": {"case": 769_900, "baseline": 769_900},
            "capex_adj": {"case": 55_000, "baseline": 55_000},
            "capex_efter": {"case": 714_900, "baseline": 714_900},
            "method": "TOTEX",
        },
    }


def generate_all_companies_efficiency(n_companies: int = 148, seed: int = 55) -> pd.DataFrame:
    """Generate efficiency scores for all 148 companies. Beta distribution ~ 0.6-1.0."""
    rng = np.random.default_rng(seed)
    scores = 0.55 + rng.beta(5, 2, size=n_companies) * 0.45
    scores = np.minimum(scores, 1.0)
    return pd.DataFrame({"company_id": range(1, n_companies+1), "efficiency": scores})


def generate_benchmarking_data() -> Dict[str, Any]:
    return {
        "dea_method": "custom",
        "inputs": ["Total OPEX", "Capital base (NUAV)"],
        "outputs": ["Delivered energy (MWh)", "Customer count", "Network length (km)"],
        "rts": "CRS",
        "baseline": {"efficiency": 0.847, "potential": 0.153, "effkrav": 0.0330},
        "custom": {"efficiency": 0.891, "potential": 0.109, "effkrav": 0.0232},
    }


# =============================================================================
# VISUALIZATION LAYER
# =============================================================================

def _base_layout(**overrides) -> dict:
    defaults = dict(
        font=dict(family="Inter, sans-serif", size=13, color=COLORS["text_primary"]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        hoverlabel=dict(font_size=12), height=400,
    )
    defaults.update(overrides)
    return defaults


def _fmt_tkr(v: float) -> str:
    return f"{v:,.0f}"

def _fmt_msek(v: float) -> str:
    return f"{v / 1000:,.1f}"


# --- M1/M2/M3 Return: Category charts ---

def viz_category_horizontal_bar(case_period, baseline_period, value_col_prefix, title, unit="tkr"):
    ord_col = f"{value_col_prefix}_ord"
    tail_col = f"{value_col_prefix}_tail"
    total_col = f"{value_col_prefix}_total"

    ca = case_period.copy(); ca[total_col] = ca[ord_col] + ca[tail_col]
    ba = baseline_period.copy(); ba[total_col] = ba[ord_col] + ba[tail_col]
    ba["name"] = ba["cat_encode"].map(CATEGORY_NAMES)
    ca["name"] = ca["cat_encode"].map(CATEGORY_NAMES)
    ba = ba.sort_values(total_col, ascending=True)
    order = ba["cat_encode"].tolist()
    ca = ca.set_index("cat_encode").loc[order].reset_index()
    ba = ba.reset_index(drop=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(y=ba["name"], x=ba[ord_col], orientation="h", name="BL Ord",
        marker_color=C_ORD_BL, legendgroup="bl",
        hovertemplate="%{y}<br>BL Ord: %{x:,.0f} "+unit+"<extra></extra>"))
    fig.add_trace(go.Bar(y=ba["name"], x=ba[tail_col], orientation="h", name="BL Tail",
        marker_color=C_TAIL_BL, legendgroup="bl",
        hovertemplate="%{y}<br>BL Tail: %{x:,.0f} "+unit+"<extra></extra>"))
    fig.add_trace(go.Bar(y=ca["name"], x=ca[ord_col], orientation="h", name="Case Ord",
        marker_color=C_ORD, legendgroup="case",
        hovertemplate="%{y}<br>Case Ord: %{x:,.0f} "+unit+"<extra></extra>"))
    fig.add_trace(go.Bar(y=ca["name"], x=ca[tail_col], orientation="h", name="Case Tail",
        marker_color=C_TAIL, legendgroup="case",
        hovertemplate="%{y}<br>Case Tail: %{x:,.0f} "+unit+"<extra></extra>"))
    fig.update_layout(**_base_layout(
        title=dict(text=title, font=dict(size=15)),
        barmode="stack", bargroupgap=0.15, bargap=0.25,
        height=max(420, len(order)*45),
        xaxis=dict(title=unit, gridcolor="#E2E8F0", zeroline=True, zerolinecolor="#CBD5E1"),
        yaxis=dict(automargin=True)))
    return fig


def viz_category_delta_bar(case_period, baseline_period, value_col_prefix, title, unit="tkr"):
    oc, tc = f"{value_col_prefix}_ord", f"{value_col_prefix}_tail"
    m = case_period.merge(baseline_period, on="cat_encode", suffixes=("_c","_bl"))
    m["delta"] = (m[f"{oc}_c"]+m[f"{tc}_c"]) - (m[f"{oc}_bl"]+m[f"{tc}_bl"])
    m["name"] = m["cat_encode"].map(CATEGORY_NAMES)
    m = m.sort_values("delta", ascending=True)
    colors = [C_POSITIVE if d >= 0 else C_NEGATIVE for d in m["delta"]]
    fig = go.Figure(go.Bar(y=m["name"], x=m["delta"], orientation="h", marker_color=colors,
        hovertemplate="%{y}<br>Delta: %{x:+,.0f} "+unit+"<extra></extra>"))
    fig.update_layout(**_base_layout(
        title=dict(text=title, font=dict(size=15)),
        height=max(400, len(m)*40),
        xaxis=dict(title=f"Delta ({unit})", zeroline=True, zerolinecolor=COLORS["text_primary"],
                   zerolinewidth=1.5, gridcolor="#E2E8F0"),
        yaxis=dict(automargin=True), showlegend=False))
    return fig


def viz_halfyear_timeline(case_hy, baseline_hy, cat_encode, value_col_prefix, title, unit="tkr"):
    oc, tc = f"{value_col_prefix}_ord", f"{value_col_prefix}_tail"
    c = case_hy[case_hy["cat_encode"]==cat_encode].sort_values("time")
    b = baseline_hy[baseline_hy["cat_encode"]==cat_encode].sort_values("time")
    labels = [TIME_LABELS[t] for t in c["time"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=c[oc].values, name="Case Ord", marker_color=C_ORD, opacity=0.85))
    fig.add_trace(go.Bar(x=labels, y=c[tc].values, name="Case Tail", marker_color=C_TAIL, opacity=0.85))
    fig.add_trace(go.Scatter(x=labels, y=(b[oc].values+b[tc].values), name="BL Total",
        mode="lines+markers", line=dict(color=C_BASELINE_DARK, width=2, dash="dot"), marker=dict(size=6)))
    fig.update_layout(**_base_layout(
        title=dict(text=title, font=dict(size=14)), barmode="stack", height=350,
        xaxis=dict(title="Period"), yaxis=dict(title=unit, gridcolor="#E2E8F0")))
    return fig


def viz_category_heatmap(df, value_col_prefix, title):
    oc, tc = f"{value_col_prefix}_ord", f"{value_col_prefix}_tail"
    df = df.copy(); df["total"] = df[oc]+df[tc]; df["period"] = df["time"].map(TIME_LABELS)
    df["name"] = df["cat_encode"].map(CATEGORY_NAMES)
    pivot = df.pivot_table(index="name", columns="period", values="total", aggfunc="sum")
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
    fig = go.Figure(go.Heatmap(z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=[[0,"#F0F9FF"],[0.3,"#BAE6FD"],[0.6,"#38BDF8"],[1.0,"#1E40AF"]],
        hovertemplate="%{y}<br>%{x}: %{z:,.0f} tkr<extra></extra>", colorbar=dict(title="tkr", len=0.6)))
    fig.update_layout(**_base_layout(
        title=dict(text=title, font=dict(size=14)),
        height=max(400, len(pivot)*35), yaxis=dict(automargin=True)))
    return fig


# --- M3 WACC ---

def viz_wacc_chain(wacc_data):
    all_p = {**wacc_data["capm"], **wacc_data["derived"]}
    ids = list(all_p.keys())
    labels = [all_p[k]["label"] for k in ids]
    cv = [all_p[k]["case"] for k in ids]
    bv = [all_p[k]["baseline"] for k in ids]
    fmts = [all_p[k]["fmt"] for k in ids]
    def _fv(v,f): return f"{v*100:.2f}%" if f=="pct" else f"{v:.4f}"
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=cv, orientation="h", name="Case", marker_color=C_CASE,
        text=[_fv(v,f) for v,f in zip(cv,fmts)], textposition="outside", textfont=dict(size=11)))
    fig.add_trace(go.Scatter(y=labels, x=bv, mode="markers", name="Baseline",
        marker=dict(symbol="line-ns", size=18, line=dict(width=2.5, color=C_BASELINE_DARK))))
    fig.update_layout(**_base_layout(
        title=dict(text="WACC Parameters: Case vs Baseline", font=dict(size=15)),
        height=max(400, len(labels)*38),
        xaxis=dict(gridcolor="#E2E8F0", zeroline=False),
        yaxis=dict(automargin=True, autorange="reversed"), barmode="overlay"))
    return fig


# --- M3 Incentive: Pipeline waterfall (period total) ---

def viz_incentive_pipeline(case_df):
    """Horizontal waterfall: full regulatory incentive pipeline for period total."""
    t = case_df[case_df["year"]=="Total"].iloc[0]

    labels = [
        "Network loss (before cap)", "  Cap adjustment",
        "Utilization (before cap)", "  Cap adjustment",
        "Quality (before CEMI4)", "  CEMI4 adjustment", "  Cap adjustment",
        "Sum before agg. cap",
        "Aggregate cap",
        "Final incentive total",
    ]
    values = [
        t["loss_incentive_a"],
        t["loss_incentive"] - t["loss_incentive_a"],
        t["util_incentive_a"],
        t["util_incentive"] - t["util_incentive_a"],
        t["inc_inter"],
        t["inter_incentive_a"] - t["inc_inter"],
        t["inter_incentive"] - t["inter_incentive_a"],
        0,  # subtotal
        t["incentive_total_year"] - t["total_before_agg_cap"],
        0,  # final total
    ]
    measures = [
        "relative", "relative",
        "relative", "relative",
        "relative", "relative", "relative",
        "total",
        "relative",
        "total",
    ]

    # Build text labels
    text_vals = []
    running = 0
    for v, m in zip(values, measures):
        if m == "relative":
            running += v
            text_vals.append(f"{v/1000:+,.1f}")
        else:
            text_vals.append(f"{running/1000:,.1f}")

    fig = go.Figure(go.Waterfall(
        orientation="h", y=labels, x=[v/1000 for v in values],
        measure=measures, textposition="outside", text=text_vals,
        textfont=dict(size=11),
        increasing=dict(marker_color=C_POSITIVE),
        decreasing=dict(marker_color=C_NEGATIVE),
        totals=dict(marker_color=COLORS["primary_dark"]),
        connector=dict(line=dict(color="#94A3B8", width=1, dash="dot")),
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Incentive Pipeline (period total, tkr)", font=dict(size=15)),
        height=440,
        xaxis=dict(title="tkr", gridcolor="#E2E8F0", zeroline=True, zerolinecolor="#94A3B8"),
        yaxis=dict(automargin=True, autorange="reversed"),
        showlegend=False, margin=dict(l=20, r=80, t=50, b=30)))
    return fig


# --- M3 Incentive: Per-year stacked bar ---

def viz_incentive_year_stacked(case_df, baseline_df):
    """Stacked bar per year (after-cap components) + BL total line."""
    yc = case_df[case_df["year"]!="Total"].copy()
    ybl = baseline_df[baseline_df["year"]!="Total"].copy()
    xl = yc["year"].astype(int).astype(str).tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=xl, y=yc["loss_incentive"]/1000, name="Network loss",
        marker_color=COLORS["primary"],
        hovertemplate="%{x}<br>Network loss: %{y:,.1f} tkr<extra></extra>"))
    fig.add_trace(go.Bar(x=xl, y=yc["util_incentive"]/1000, name="Utilization",
        marker_color=COLORS["teal"],
        hovertemplate="%{x}<br>Utilization: %{y:,.1f} tkr<extra></extra>"))
    fig.add_trace(go.Bar(x=xl, y=yc["inter_incentive"]/1000, name="Quality",
        marker_color=COLORS["violet"],
        hovertemplate="%{x}<br>Quality: %{y:,.1f} tkr<extra></extra>"))
    fig.add_trace(go.Scatter(x=xl, y=ybl["incentive_total_year"]/1000, name="BL total",
        mode="lines+markers", line=dict(color=C_BASELINE_DARK, width=2.5, dash="dot"),
        marker=dict(size=8)))
    fig.update_layout(**_base_layout(
        title=dict(text="After-Cap Incentive by Year (Case)", font=dict(size=15)),
        barmode="relative", height=400,
        xaxis=dict(title="Year"),
        yaxis=dict(title="tkr", gridcolor="#E2E8F0", zeroline=True, zerolinecolor="#94A3B8")))
    return fig


# --- M3 Incentive: Per-year drill-down dumbbell ---

def viz_incentive_year_drill(case_df, year):
    """Dumbbell: before vs after adjustments for one year."""
    row = case_df[case_df["year"]==year].iloc[0]
    components = [
        ("Network loss", row["loss_incentive_a"], row["loss_incentive"]),
        ("Utilization", row["util_incentive_a"], row["util_incentive"]),
        ("Quality", row["inc_inter"], row["inter_incentive"]),
        ("Total", row["total_before_agg_cap"], row["incentive_total_year"]),
    ]
    y_labels = [c[0] for c in components]
    before = [c[1]/1000 for c in components]
    after = [c[2]/1000 for c in components]

    fig = go.Figure()
    # Connecting lines
    for i in range(len(y_labels)):
        fig.add_trace(go.Scatter(x=[before[i], after[i]], y=[y_labels[i]]*2,
            mode="lines", line=dict(color="#94A3B8", width=2.5),
            showlegend=False, hoverinfo="skip"))
    # Before markers
    fig.add_trace(go.Scatter(x=before, y=y_labels, mode="markers",
        name="Before adj.", marker=dict(size=13, color=COLORS["orange"],
            line=dict(width=1, color="white")),
        hovertemplate="%{y}<br>Before: %{x:,.1f} tkr<extra></extra>"))
    # After markers
    fig.add_trace(go.Scatter(x=after, y=y_labels, mode="markers",
        name="After adj.", marker=dict(size=13, color=COLORS["primary"],
            line=dict(width=1, color="white")),
        hovertemplate="%{y}<br>After: %{x:,.1f} tkr<extra></extra>"))

    fig.update_layout(**_base_layout(
        title=dict(text=f"Before / After Adjustments -- {year}", font=dict(size=14)),
        height=260,
        xaxis=dict(title="tkr", gridcolor="#E2E8F0", zeroline=True, zerolinecolor="#94A3B8"),
        yaxis=dict(automargin=True)))
    return fig


# --- M3 AIT/AIF heatmap ---

def viz_ait_aif_heatmap(case_df, indicator):
    sni_labels = {1:"Agriculture", 2:"Industry", 3:"Trade/Serv.", 4:"Public", 5:"Household", 6:"Boundary"}
    ydf = case_df[case_df["year"]!="Total"]
    md, yl = [], []
    for ann, al in [("o","Unplan."), ("a","Plan.")]:
        for sni in range(1,7):
            col = f"inc_{indicator}_{ann}_{sni}"
            if col in ydf.columns:
                md.append((ydf[col]/1000).values); yl.append(f"{al} {sni_labels[sni]}")
    z = np.array(md); xl = [str(int(y)) for y in ydf["year"]]
    fig = go.Figure(go.Heatmap(z=z, x=xl, y=yl, colorscale="RdBu_r", zmid=0,
        hovertemplate="%{y}<br>%{x}: %{z:,.1f} tkr<extra></extra>",
        colorbar=dict(title="tkr", len=0.7)))
    fig.update_layout(**_base_layout(
        title=dict(text=f"{indicator.upper()} Quality Incentive by Customer Type", font=dict(size=14)),
        height=max(350, len(yl)*30), yaxis=dict(automargin=True)))
    return fig


# --- M4 OPEX ---

def viz_opex_components(case_ir, baseline_ir):
    comps = [("Paverkbara_Periodsumma","Controllable (40.1)"),
             ("Opaverkbara_Kostnader","Non-controllable (40.2)"),
             ("Flexibilitetstjanster","Flexibility services"),
             ("Avbrottsersattning_12_24h","Interruption comp.")]
    labels = [c[1] for c in comps]
    cv = [case_ir.get(c[0],0) for c in comps]
    bv = [baseline_ir.get(c[0],0) for c in comps]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=cv, orientation="h", name="Case", marker_color=C_CASE))
    fig.add_trace(go.Bar(y=labels, x=bv, orientation="h", name="Baseline", marker_color=C_BASELINE))
    fig.update_layout(**_base_layout(
        title=dict(text="Operating Expenditure Components", font=dict(size=15)),
        barmode="group", height=320, xaxis=dict(title="tkr", gridcolor="#E2E8F0"),
        yaxis=dict(automargin=True)))
    return fig


def viz_opex_dumbbell(case_ir, baseline_ir):
    """Dumbbell chart: before -> after efficiency for OPEX (and CAPEX if TOTEX)."""
    method = case_ir.get("Method_used", "OPEX")
    items = [("OPEX", case_ir["OPEX_Fore"], case_ir["OPEX_Efter"],
              baseline_ir["OPEX_Fore"], baseline_ir["OPEX_Efter"])]
    if method == "TOTEX":
        items.append(("CAPEX", case_ir["CAPEX_Fore"], case_ir["CAPEX_Efter"],
                       baseline_ir["CAPEX_Fore"], baseline_ir["CAPEX_Efter"]))

    fig = go.Figure()
    show_legend_before = True
    show_legend_after = True

    for label, cb, ca, bb, ba in items:
        yc = f"{label} (Case)"; yb = f"{label} (BL)"

        # Case connector + markers
        fig.add_trace(go.Scatter(x=[cb,ca], y=[yc,yc], mode="lines",
            line=dict(color=COLORS["primary"], width=3), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[cb], y=[yc], mode="markers+text",
            marker=dict(size=14, color=COLORS["orange"]),
            text=[f"{cb:,.0f}"], textposition="top center", textfont=dict(size=10),
            name="Before eff." if show_legend_before else None, showlegend=show_legend_before,
            hovertemplate=f"{label} Case Before: {cb:,.0f} tkr<extra></extra>"))
        fig.add_trace(go.Scatter(x=[ca], y=[yc], mode="markers+text",
            marker=dict(size=14, color=COLORS["primary"]),
            text=[f"{ca:,.0f}"], textposition="top center", textfont=dict(size=10),
            name="After eff." if show_legend_after else None, showlegend=show_legend_after,
            hovertemplate=f"{label} Case After: {ca:,.0f} tkr<extra></extra>"))
        fig.add_annotation(x=(cb+ca)/2, y=yc, text=f"-{cb-ca:,.0f}",
            showarrow=False, yshift=-18, font=dict(size=11, color=C_NEGATIVE))

        # Baseline connector + markers
        fig.add_trace(go.Scatter(x=[bb,ba], y=[yb,yb], mode="lines",
            line=dict(color=C_BASELINE_DARK, width=3), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[bb], y=[yb], mode="markers",
            marker=dict(size=10, color=COLORS["orange"], opacity=0.5), showlegend=False,
            hovertemplate=f"{label} BL Before: {bb:,.0f} tkr<extra></extra>"))
        fig.add_trace(go.Scatter(x=[ba], y=[yb], mode="markers",
            marker=dict(size=10, color=C_BASELINE_DARK, opacity=0.5), showlegend=False,
            hovertemplate=f"{label} BL After: {ba:,.0f} tkr<extra></extra>"))
        fig.add_annotation(x=(bb+ba)/2, y=yb, text=f"-{bb-ba:,.0f}",
            showarrow=False, yshift=-18, font=dict(size=10, color="#94A3B8"))

        show_legend_before = False; show_legend_after = False

    fig.update_layout(**_base_layout(
        title=dict(text=f"Efficiency Adjustment ({method})", font=dict(size=15)),
        height=200+len(items)*100,
        xaxis=dict(title="tkr", gridcolor="#E2E8F0"),
        yaxis=dict(automargin=True), margin=dict(l=20, r=20, t=50, b=30)))
    return fig


# --- M5 Efficiency: Histogram ---

def viz_efficiency_histogram(all_companies, eff_data):
    """Histogram of 148 companies + truncation zones + company markers."""
    scores = all_companies["efficiency"].values
    cs = eff_data["measures"]["efficiency"]["case"]
    bs = eff_data["measures"]["efficiency"]["baseline"]
    tmax = eff_data["params"]["trunkering_max"]["case"]
    tmin = eff_data["params"]["trunkering_min"]["case"]

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=scores, nbinsx=30, marker_color=COLORS["primary_light"],
        opacity=0.7, name="All companies",
        hovertemplate="Score: %{x:.2f}<br>Count: %{y}<extra></extra>"))

    # Truncation zone
    fig.add_vrect(x0=1-tmax, x1=1-tmin, fillcolor="#FEF3C7", opacity=0.4, line_width=0,
        annotation_text="Truncation zone", annotation_position="top left",
        annotation_font=dict(size=10, color="#92400E"))
    # Low/no adjustment zone
    fig.add_vrect(x0=1-tmin, x1=1.0, fillcolor="#ECFDF5", opacity=0.3, line_width=0,
        annotation_text="Low/no adj.", annotation_position="top left",
        annotation_font=dict(size=10, color="#065F46"))

    # Company markers
    fig.add_vline(x=cs, line_width=3, line_color=COLORS["primary"],
        annotation_text=f"Case: {cs:.3f}", annotation_position="top right",
        annotation_font=dict(size=12, color=COLORS["primary"]))
    fig.add_vline(x=bs, line_width=2, line_dash="dot", line_color=C_BASELINE_DARK,
        annotation_text=f"BL: {bs:.3f}", annotation_position="bottom right",
        annotation_font=dict(size=11, color=C_BASELINE_DARK))

    fig.update_layout(**_base_layout(
        title=dict(text="Efficiency Score Distribution (all companies)", font=dict(size=15)),
        height=380,
        xaxis=dict(title="Efficiency score", range=[0.55, 1.02], gridcolor="#E2E8F0", dtick=0.05),
        yaxis=dict(title="Number of companies", gridcolor="#E2E8F0"),
        bargap=0.05))
    return fig


def viz_efficiency_costs(eff_data):
    costs = eff_data["costs"]; method = costs["method"]
    cats = ["Before adj.", "Eff. adjustment", "After adj."]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cats,
        y=[costs["opex_fore"]["case"], -costs["opex_adj"]["case"], costs["opex_efter"]["case"]],
        name="OPEX (Case)", marker_color=C_CASE))
    fig.add_trace(go.Bar(x=cats,
        y=[costs["opex_fore"]["baseline"], -costs["opex_adj"]["baseline"], costs["opex_efter"]["baseline"]],
        name="OPEX (BL)", marker_color=C_BASELINE))
    if method == "TOTEX":
        fig.add_trace(go.Bar(x=cats,
            y=[costs["capex_fore"]["case"], -costs["capex_adj"]["case"], costs["capex_efter"]["case"]],
            name="CAPEX (Case)", marker_color=COLORS["teal"]))
        fig.add_trace(go.Bar(x=cats,
            y=[costs["capex_fore"]["baseline"], -costs["capex_adj"]["baseline"], costs["capex_efter"]["baseline"]],
            name="CAPEX (BL)", marker_color=COLORS["teal_light"]))
    fig.update_layout(**_base_layout(
        title=dict(text="50.4 Efficiency-Adjusted Costs", font=dict(size=15)),
        barmode="group", height=400, yaxis=dict(title="tkr", gridcolor="#E2E8F0")))
    return fig


# --- M7 Benchmarking ---

def viz_benchmarking_comparison(bench_data):
    metrics = ["Efficiency score", "Potential", "Applied req."]
    bl = bench_data["baseline"]; cu = bench_data["custom"]
    bv = [bl["efficiency"], bl["potential"], bl["effkrav"]]
    cv = [cu["efficiency"], cu["potential"], cu["effkrav"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=metrics, x=bv, orientation="h", name="Baseline DEA",
        marker_color=C_BASELINE_DARK, text=[f"{v:.3f}" for v in bv], textposition="outside"))
    fig.add_trace(go.Bar(y=metrics, x=cv, orientation="h", name="Custom DEA",
        marker_color=C_CASE, text=[f"{v:.3f}" for v in cv], textposition="outside"))
    fig.update_layout(**_base_layout(
        title=dict(text="Baseline vs Custom DEA", font=dict(size=15)),
        barmode="group", height=280, xaxis=dict(gridcolor="#E2E8F0"),
        yaxis=dict(automargin=True)))
    return fig


# =============================================================================
# TABLE HELPERS
# =============================================================================

def build_comparison_table(case_period, baseline_period, value_col_prefix, var_id_fmt="11.{n}"):
    oc, tc = f"{value_col_prefix}_ord", f"{value_col_prefix}_tail"
    rows = []
    for ce, name in CATEGORY_NAMES.items():
        c = case_period[case_period["cat_encode"]==ce]
        b = baseline_period[baseline_period["cat_encode"]==ce]
        co = c[oc].iloc[0] if len(c) else 0; ct = c[tc].iloc[0] if len(c) else 0
        bo = b[oc].iloc[0] if len(b) else 0; bt = b[tc].iloc[0] if len(b) else 0
        ctot = co+ct; btot = bo+bt
        if abs(ctot) < 0.01 and abs(btot) < 0.01: continue
        d = ctot-btot; dp = (d/btot*100) if btot else 0
        rows.append({"Var-ID": var_id_fmt.replace("{n}", str(ce+1)), "Category": name,
            "C Ord": co, "C Tail": ct, "C Total": ctot,
            "BL Ord": bo, "BL Tail": bt, "BL Total": btot,
            "Delta": d, "Delta %": dp})
    return pd.DataFrame(rows)


def build_halfyear_table(case_hy, baseline_hy, cat_encode, value_col_prefix):
    oc, tc = f"{value_col_prefix}_ord", f"{value_col_prefix}_tail"
    rows = []
    for tcode, label in TIME_LABELS.items():
        cr = case_hy[(case_hy["cat_encode"]==cat_encode)&(case_hy["time"]==tcode)]
        br = baseline_hy[(baseline_hy["cat_encode"]==cat_encode)&(baseline_hy["time"]==tcode)]
        co = cr[oc].iloc[0] if len(cr) else 0; ct = cr[tc].iloc[0] if len(cr) else 0
        bo = br[oc].iloc[0] if len(br) else 0; bt = br[tc].iloc[0] if len(br) else 0
        rows.append({"Period": label, "C Ord": co, "C Tail": ct, "C Total": co+ct,
                      "BL Ord": bo, "BL Tail": bt, "BL Total": bo+bt})
    return pd.DataFrame(rows)


# =============================================================================
# PAGE LAYOUT
# =============================================================================

def _agg_period(df, pfx):
    return df.groupby("cat_encode")[[f"{pfx}_ord", f"{pfx}_tail"]].sum().reset_index()


def _render_m1_m2_m3(case_df, bl_df, pfx, label, vid_fmt, total_vid, unit="tkr"):
    oc, tc = f"{pfx}_ord", f"{pfx}_tail"
    cp = _agg_period(case_df, pfx); bp = _agg_period(bl_df, pfx)

    cot = cp[oc].sum(); ctt = cp[tc].sum(); ct = cot+ctt
    bot = bp[oc].sum(); btt = bp[tc].sum(); bt = bot+btt
    d = ct-bt; dp = (d/bt*100) if bt else 0

    st.markdown(f"**{total_vid} Total {label}**")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Case Total", f"{_fmt_msek(ct)} MSEK", delta=f"{dp:+.1f}%")
    with c2: st.metric("Baseline Total", f"{_fmt_msek(bt)} MSEK")
    with c3: st.metric("Delta", f"{_fmt_msek(d)} MSEK")

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.caption(f"Case Ord: {_fmt_msek(cot)} MSEK")
    with c2: st.caption(f"Case Tail: {_fmt_msek(ctt)} MSEK")
    with c3: st.caption(f"BL Ord: {_fmt_msek(bot)} MSEK")
    with c4: st.caption(f"BL Tail: {_fmt_msek(btt)} MSEK")

    st.divider()
    cl, cr = st.columns(2)
    with cl: st.plotly_chart(viz_category_horizontal_bar(cp, bp, pfx,
        f"{label} by Category (Case vs Baseline)", unit), use_container_width=True,
        config={"displayModeBar": False})
    with cr: st.plotly_chart(viz_category_delta_bar(cp, bp, pfx,
        f"{label} Delta per Category (Case - BL)", unit), use_container_width=True,
        config={"displayModeBar": False})

    st.divider()
    st.markdown(f"**{vid_fmt.replace('{n}','2')}-{vid_fmt.replace('{n}','18')} {label} by Category**")
    comp_df = build_comparison_table(cp, bp, pfx, vid_fmt)
    st.dataframe(comp_df, hide_index=True, use_container_width=True,
        column_config={
            "Var-ID": st.column_config.TextColumn("ID", width="small"),
            "Category": st.column_config.TextColumn("Category", width="medium"),
            **{c: st.column_config.NumberColumn(c, format="%.0f")
               for c in ["C Ord","C Tail","C Total","BL Ord","BL Tail","BL Total"]},
            "Delta": st.column_config.NumberColumn("Delta", format="%+.0f"),
            "Delta %": st.column_config.NumberColumn("Delta %", format="%+.1f%%")})

    st.divider()
    cl2, cr2 = st.columns([1,2])
    with cl2:
        sel = st.selectbox("Category", list(CATEGORY_NAMES.values()), key=f"{pfx}_hy_cat")
        se = [k for k,v in CATEGORY_NAMES.items() if v==sel][0]
        ht = build_halfyear_table(case_df, bl_df, se, pfx)
        st.dataframe(ht, hide_index=True, use_container_width=True,
            column_config={c: st.column_config.NumberColumn(c, format="%.0f")
                           for c in ht.columns if c!="Period"})
    with cr2:
        st.plotly_chart(viz_halfyear_timeline(case_df, bl_df, se, pfx,
            f"{sel} -- Half-year evolution", unit), use_container_width=True,
            config={"displayModeBar": False})

    with st.expander("Heatmap: all categories x half-years (Case)"):
        st.plotly_chart(viz_category_heatmap(case_df, pfx, f"Case {label} Heatmap"),
            use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# MAIN
# =============================================================================

def main():
    st.set_page_config(page_title="Regumetrica Viz Test v2", layout="wide")
    st.title("Regumetrica Results -- Visualization Prototype v2")
    st.caption("Test file with fake data. Viz layer separated from data layer.")

    case_cat, bl_cat = generate_category_data()
    wacc_data = generate_wacc_data()
    case_inc, bl_inc = generate_incentive_data()
    case_aitaif, bl_aitaif = generate_ait_aif_data()
    case_opex, bl_opex = generate_opex_data()
    eff_data = generate_efficiency_data()
    all_companies = generate_all_companies_efficiency()
    bench_data = generate_benchmarking_data()

    tabs = st.tabs(["M1 Asset Base", "M2 Depreciation", "M3 Cost of Capital",
                     "M4 Operating Exp.", "M5 Efficiency", "M7 Benchmarking"])

    with tabs[0]:
        _render_m1_m2_m3(case_cat, bl_cat, "nuav", "NUAV", "11.{n}", "11.1")

    with tabs[1]:
        _render_m1_m2_m3(case_cat, bl_cat, "dep", "Depreciation", "20.{n}", "20.1")

    with tabs[2]:
        st.markdown("**3.1-3.2 WACC Calculation Chain**")
        st.plotly_chart(viz_wacc_chain(wacc_data), use_container_width=True,
            config={"displayModeBar": False})

        wacc_rows = []
        for section in ["capm", "derived"]:
            for vid, info in wacc_data[section].items():
                if info["fmt"]=="pct":
                    cs=f"{info['case']*100:.2f}%"; bs=f"{info['baseline']*100:.2f}%"
                    ds=f"{(info['case']-info['baseline'])*100:+.2f} pp"
                else:
                    cs=f"{info['case']:.4f}"; bs=f"{info['baseline']:.4f}"
                    ds=f"{info['case']-info['baseline']:+.4f}"
                wacc_rows.append({"ID":vid,"Parameter":info["label"],"Case":cs,"Baseline":bs,"Delta":ds})
        with st.expander("WACC parameters table"):
            st.dataframe(pd.DataFrame(wacc_rows), hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("**30.1 Return on Capital by Category**")
        _render_m1_m2_m3(case_cat, bl_cat, "return", "Return", "30.1.{n}", "30.1")

        st.divider()
        st.markdown("**30.2-30.5 Incentive Adjustments**")

        il, ir = st.columns(2)
        with il:
            st.plotly_chart(viz_incentive_pipeline(case_inc),
                use_container_width=True, config={"displayModeBar": False})
        with ir:
            st.plotly_chart(viz_incentive_year_stacked(case_inc, bl_inc),
                use_container_width=True, config={"displayModeBar": False})

        # Year drill-down
        sel_year = st.selectbox("Drill into year", [2024,2025,2026,2027], key="inc_year_drill")
        st.plotly_chart(viz_incentive_year_drill(case_inc, sel_year),
            use_container_width=True, config={"displayModeBar": False})

        # Summary table
        tc = case_inc[case_inc["year"]=="Total"].iloc[0]
        tb = bl_inc[bl_inc["year"]=="Total"].iloc[0]
        inc_sum = []
        for vid, col, lbl in [("30.2.5","loss_incentive","Network loss"),
            ("30.3.5","util_incentive","Utilization"), ("30.4.59","inter_incentive","Quality"),
            ("30.5.2","incentive_total_year","Total incentive")]:
            c=tc[col]/1000; b=tb[col]/1000
            inc_sum.append({"ID":vid,"Component":lbl,"Case (tkr)":f"{c:,.0f}",
                "BL (tkr)":f"{b:,.0f}","Delta (tkr)":f"{c-b:+,.0f}"})
        st.dataframe(pd.DataFrame(inc_sum), hide_index=True, use_container_width=True)

        with st.expander("Per-year incentive detail"):
            vid_map = {"loss_incentive_a":"30.2.4","loss_incentive":"30.2.5",
                "util_incentive_a":"30.3.4","util_incentive":"30.3.5",
                "inc_inter":"30.4.57","inter_incentive_a":"30.4.58","inter_incentive":"30.4.59",
                "total_before_agg_cap":"30.5.1","incentive_total_year":"30.5.2"}
            lbl_map = {"loss_incentive_a":"Network loss (before cap)","loss_incentive":"Network loss (after cap)",
                "util_incentive_a":"Utilization (before cap)","util_incentive":"Utilization (after cap)",
                "inc_inter":"Quality (before CEMI4)","inter_incentive_a":"Quality (after CEMI4)",
                "inter_incentive":"Quality (after cap)",
                "total_before_agg_cap":"Total (before agg cap)","incentive_total_year":"Total (after agg cap)"}
            drows = []
            cy = case_inc[case_inc["year"]!="Total"]
            ct_df = case_inc[case_inc["year"]=="Total"]
            bt_df = bl_inc[bl_inc["year"]=="Total"]
            for cn, vid in vid_map.items():
                if cn not in case_inc.columns: continue
                row = {"ID":vid,"Desc":lbl_map.get(cn,cn)}
                for _,dr in cy.iterrows(): row[str(int(dr["year"]))] = dr[cn]/1000
                row["C Total"] = ct_df.iloc[0][cn]/1000
                row["BL Total"] = bt_df.iloc[0][cn]/1000
                row["Delta"] = row["C Total"]-row["BL Total"]
                drows.append(row)
            st.dataframe(pd.DataFrame(drows), hide_index=True, use_container_width=True)

        with st.expander("Quality incentive by customer type (AIT/AIF)"):
            ac, afc = st.columns(2)
            with ac: st.plotly_chart(viz_ait_aif_heatmap(case_aitaif,"ait"),
                use_container_width=True, config={"displayModeBar": False})
            with afc: st.plotly_chart(viz_ait_aif_heatmap(case_aitaif,"aif"),
                use_container_width=True, config={"displayModeBar": False})

    # M4
    with tabs[3]:
        st.markdown("**40.1-40.2 Operating Expenditures**")
        pvc = case_opex["Paverkbara_Periodsumma"]; pvb = bl_opex["Paverkbara_Periodsumma"]
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("40.1 Controllable", f"{pvc:,.0f} tkr",
            delta=f"{((pvc-pvb)/pvb*100):+.1f}%" if pvb else "")
        with c2: st.metric("40.2 Non-controllable", f"{case_opex['Opaverkbara_Kostnader']:,.0f} tkr")
        with c3: st.metric("Method", case_opex["Method_used"])

        st.divider()
        ml, mr = st.columns(2)
        with ml: st.plotly_chart(viz_opex_components(case_opex, bl_opex),
            use_container_width=True, config={"displayModeBar": False})
        with mr: st.plotly_chart(viz_opex_dumbbell(case_opex, bl_opex),
            use_container_width=True, config={"displayModeBar": False})

        st.markdown("**Other OPEX components**")
        other = [{"ID":"40.1.2","Component":"Flexibility services",
            "Case":f"{case_opex['Flexibilitetstjanster']:,.0f}",
            "BL":f"{bl_opex['Flexibilitetstjanster']:,.0f}",
            "Delta":f"{case_opex['Flexibilitetstjanster']-bl_opex['Flexibilitetstjanster']:+,.0f}"},
            {"ID":"-","Component":"Interruption comp. (12-24h)",
            "Case":f"{case_opex['Avbrottsersattning_12_24h']:,.0f}",
            "BL":f"{bl_opex['Avbrottsersattning_12_24h']:,.0f}",
            "Delta":f"{case_opex['Avbrottsersattning_12_24h']-bl_opex['Avbrottsersattning_12_24h']:+,.0f}"},
            {"ID":"-","Component":"State aid deduction",
            "Case":f"{-case_opex['Avdrag_Statligt_Stod']:,.0f}",
            "BL":f"{-bl_opex['Avdrag_Statligt_Stod']:,.0f}","Delta":"0"}]
        st.dataframe(pd.DataFrame(other), hide_index=True, use_container_width=True)

    # M5
    with tabs[4]:
        st.markdown("**5.2-5.3 Efficiency Parameters**")
        pr = []; p = eff_data["params"]
        for pid, lbl, key, fmt in [("5.2.1","Max potential cap","trunkering_max","pct"),
            ("5.2.2","Realization time","realiseringstid","yr"),
            ("5.2.3","Customer sharing","kunddelning","pct"),
            ("5.3.1","Min annual req.","outlier_krav","pct"),
            ("5.3.2","Truncation min","trunkering_min","pct")]:
            cv=p[key]["case"]; bv=p[key]["baseline"]
            if fmt=="pct":
                pr.append({"ID":pid,"Parameter":lbl,"Case":f"{cv*100:.2f}%","Baseline":f"{bv*100:.2f}%",
                    "Delta":f"{(cv-bv)*100:+.2f} pp" if abs(cv-bv)>0.0001 else "-"})
            else:
                pr.append({"ID":pid,"Parameter":lbl,"Case":f"{int(cv)} yr","Baseline":f"{int(bv)} yr",
                    "Delta":f"{int(cv-bv):+d} yr" if cv!=bv else "-"})
        st.dataframe(pd.DataFrame(pr), hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("**50.3 Efficiency Measures**")
        st.plotly_chart(viz_efficiency_histogram(all_companies, eff_data),
            use_container_width=True, config={"displayModeBar": False})

        m = eff_data["measures"]
        mr = [{"ID":"50.3.1","Measure":"Efficiency score",
            "Case":f"{m['efficiency']['case']:.3f}","BL":f"{m['efficiency']['baseline']:.3f}",
            "Delta":f"{m['efficiency']['case']-m['efficiency']['baseline']:+.3f}"},
            {"ID":"50.3.3","Measure":"Potential (raw)",
            "Case":f"{m['potential']['case']*100:.1f}%","BL":f"{m['potential']['baseline']*100:.1f}%",
            "Delta":f"{(m['potential']['case']-m['potential']['baseline'])*100:+.1f} pp"},
            {"ID":"-","Measure":"Truncated potential",
            "Case":f"{m['potential_truncated']['case']*100:.2f}%",
            "BL":f"{m['potential_truncated']['baseline']*100:.2f}%",
            "Delta":f"{(m['potential_truncated']['case']-m['potential_truncated']['baseline'])*100:+.2f} pp"},
            {"ID":"50.3.4","Measure":"Applied req. (annual)",
            "Case":f"{m['effkrav']['case']*100:.2f}%","BL":f"{m['effkrav']['baseline']*100:.2f}%",
            "Delta":f"{(m['effkrav']['case']-m['effkrav']['baseline'])*100:+.2f} pp"}]
        st.dataframe(pd.DataFrame(mr), hide_index=True, use_container_width=True)
        if m["is_outlier"]:
            st.warning("Company classified as outlier -- fixed minimum requirement applies.")

        st.divider()
        st.markdown("**50.4 Efficiency-Adjusted Costs**")
        ml, mrt = st.columns(2)
        with ml: st.plotly_chart(viz_efficiency_costs(eff_data),
            use_container_width=True, config={"displayModeBar": False})
        with mrt:
            costs = eff_data["costs"]
            cr = [{"ID":"-","Component":"OPEX before adj.",
                "Case":f"{costs['opex_fore']['case']:,.0f}","BL":f"{costs['opex_fore']['baseline']:,.0f}",
                "Delta":f"{costs['opex_fore']['case']-costs['opex_fore']['baseline']:+,.0f}"},
                {"ID":"50.4.1","Component":"OPEX eff. adj.",
                "Case":f"-{costs['opex_adj']['case']:,.0f}","BL":f"-{costs['opex_adj']['baseline']:,.0f}",
                "Delta":f"{-(costs['opex_adj']['case']-costs['opex_adj']['baseline']):+,.0f}"},
                {"ID":"50.4.3","Component":"OPEX after adj.",
                "Case":f"{costs['opex_efter']['case']:,.0f}","BL":f"{costs['opex_efter']['baseline']:,.0f}",
                "Delta":f"{costs['opex_efter']['case']-costs['opex_efter']['baseline']:+,.0f}"}]
            if costs["method"]=="TOTEX":
                cr += [{"ID":"","Component":"","Case":"","BL":"","Delta":""},
                    {"ID":"-","Component":"CAPEX before adj.",
                    "Case":f"{costs['capex_fore']['case']:,.0f}","BL":f"{costs['capex_fore']['baseline']:,.0f}",
                    "Delta":f"{costs['capex_fore']['case']-costs['capex_fore']['baseline']:+,.0f}"},
                    {"ID":"50.4.2","Component":"CAPEX eff. adj.",
                    "Case":f"-{costs['capex_adj']['case']:,.0f}","BL":f"-{costs['capex_adj']['baseline']:,.0f}",
                    "Delta":f"{-(costs['capex_adj']['case']-costs['capex_adj']['baseline']):+,.0f}"},
                    {"ID":"50.4.4","Component":"CAPEX after adj.",
                    "Case":f"{costs['capex_efter']['case']:,.0f}","BL":f"{costs['capex_efter']['baseline']:,.0f}",
                    "Delta":f"{costs['capex_efter']['case']-costs['capex_efter']['baseline']:+,.0f}"}]
            st.dataframe(pd.DataFrame(cr), hide_index=True, use_container_width=True)

    # M7
    with tabs[5]:
        st.markdown("**DEA Specification**")
        if bench_data["dea_method"]=="custom":
            c1,c2 = st.columns(2)
            with c1: st.markdown("**Inputs:** "+", ".join(bench_data["inputs"]))
            with c2: st.markdown("**Outputs:** "+", ".join(bench_data["outputs"]))
            st.markdown(f"**Returns to scale:** {bench_data['rts']}")
            st.divider()
            st.plotly_chart(viz_benchmarking_comparison(bench_data),
                use_container_width=True, config={"displayModeBar": False})
            bl=bench_data["baseline"]; cu=bench_data["custom"]
            comp = [{"Metric":"Efficiency score","Baseline DEA":f"{bl['efficiency']:.3f}",
                "Custom DEA":f"{cu['efficiency']:.3f}","Delta":f"{cu['efficiency']-bl['efficiency']:+.3f}"},
                {"Metric":"Efficiency potential","Baseline DEA":f"{bl['potential']:.1%}",
                "Custom DEA":f"{cu['potential']:.1%}","Delta":f"{(cu['potential']-bl['potential'])*100:+.1f} pp"},
                {"Metric":"Applied requirement","Baseline DEA":f"{bl['effkrav']:.2%}",
                "Custom DEA":f"{cu['effkrav']:.2%}","Delta":f"{(cu['effkrav']-bl['effkrav'])*100:+.2f} pp"}]
            st.dataframe(pd.DataFrame(comp), hide_index=True, width="stretch")
        else:
            st.info("Using Ei's baseline DEA model.")


if __name__ == "__main__":
    main()