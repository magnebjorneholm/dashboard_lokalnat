# kapitalbas_app/policy_playground_view.py

import streamlit as st
import pandas as pd
import altair as alt
from kapitalbas.kapitalbas_app.data_loader import load_tail_sample, load_tail_full
from kapitalbas.kapitalbas_app.livslangd_simulering import simulera_livslangd
from kapitalbas.kapitalbas_app.utils import YEAR_MAP


def show_policy_playground(capcost_df):
    """Visar tre scenarier: WACC-ändring, KPI-indexering, och Tail-andelar."""
    st.subheader("Policy Playground – simulera olika regleringsscenarier")
    st.write("Testa olika kalkylräntor (WACC) och värderingsprinciper (KPI-baserad kapitalbas)")


    tab1, tab2, tab3, tab4 = st.tabs(["Kalkylränta (WACC)", "KPI-simulering", "Tail-andelar", "Livslängdssimulering"])

    # === TAB 1: Kalkylränta (WACC) ===
    with tab1:
        networks = sorted(capcost_df["id_network"].unique())
        network_choice = st.selectbox("Välj nät", ["Alla"] + networks)

        scenario_df = capcost_df.copy()
        if network_choice != "Alla":
            scenario_df = scenario_df[scenario_df["id_network"] == network_choice]

        scenario_df = scenario_df.fillna(0)
        wacc_change = st.slider("Ändra kalkylräntan (WACC) ± %", -3.0, 3.0, 0.0, step=0.25)
        rate_factor = 1 + (wacc_change / 100)

        return_ord = scenario_df[[c for c in scenario_df.columns if c.startswith("return_ord")]].sum().sum() * rate_factor
        return_tail = scenario_df[[c for c in scenario_df.columns if c.startswith("return_tail")]].sum().sum() * rate_factor
        dep_ord = scenario_df[[c for c in scenario_df.columns if c.startswith("dep_ord")]].sum().sum()
        dep_tail = scenario_df[[c for c in scenario_df.columns if c.startswith("dep_tail")]].sum().sum()

        cost_ord = return_ord + dep_ord
        cost_tail = return_tail + dep_tail
        cost_total = cost_ord + cost_tail

        col1, col2, col3 = st.columns(3)
        col1.metric("Total kapitalkostnad (MSEK)", f"{cost_total / 1_000_000:,.1f}")
        col2.metric("Ordinarie kapitalkostnad (MSEK)", f"{cost_ord / 1_000_000:,.1f}")
        col3.metric("Tail-kapitalkostnad (MSEK)", f"{cost_tail / 1_000_000:,.1f}")

        scenario_df["year"] = scenario_df["time"].map(YEAR_MAP).astype(int)

        scenario_df["capcost_with_tail"] = (
            scenario_df[[c for c in scenario_df.columns if c.startswith("return_")]].sum(axis=1) * rate_factor +
            scenario_df[[c for c in scenario_df.columns if c.startswith("dep_")]].sum(axis=1)
        )

        scenario_df["capcost_without_tail"] = (
            scenario_df[[c for c in scenario_df.columns if c.startswith("return_ord")]].sum(axis=1) * rate_factor +
            scenario_df[[c for c in scenario_df.columns if c.startswith("dep_ord")]].sum(axis=1)
        )

        ts_summary = scenario_df.groupby("year")[["capcost_with_tail", "capcost_without_tail"]].sum().reset_index()
        plot_df = ts_summary.melt(id_vars="year", var_name="Scenario", value_name="Kapitalkostnad")
        plot_df["Scenario"] = plot_df["Scenario"].map({
            "capcost_with_tail": "Med Tail",
            "capcost_without_tail": "Utan Tail"
        })

        st.altair_chart(alt.Chart(plot_df).mark_line(point=True).encode(
            x=alt.X("year:O", title="År"),
            y=alt.Y("Kapitalkostnad:Q", title="SEK"),
            color=alt.Color("Scenario:N", title="Scenario")
        ).properties(width=700, height=400), use_container_width=True)

    # === TAB 2: KPI-simulering ===
    with tab2:
        st.markdown("#### Simulera förmögenhetsbevarande värdering (KPI-indexering)")
        st.warning("Datafel i nuläget, läs labbjournal")

    # === TAB 3: Tail-andelar ===
    with tab3:
        sample_df = load_tail_sample()
        full_df = load_tail_full()

        nätkoder = sorted(sample_df["id_network"].unique())
        nätnamn = {3035: "Stort nät (3035)", 160: "Medelstort nät (160)", 7: "Kommunalt nät (7)"}

        def beräkna_tail_andelar(df, nät_namn="Totalt"):
            nuav_ord_cols = [c for c in df.columns if c.startswith("nuav_ord_")]
            nuav_tail_cols = [c for c in df.columns if c.startswith("nuav_tail_")]
            dep_ord_cols = [c for c in df.columns if c.startswith("dep_ord_")]
            dep_tail_cols = [c for c in df.columns if c.startswith("dep_tail_")]

            nuav_ord_sum = df[nuav_ord_cols].sum().sum()
            nuav_tail_sum = df[nuav_tail_cols].sum().sum()
            dep_ord_sum = df[dep_ord_cols].sum().sum()
            dep_tail_sum = df[dep_tail_cols].sum().sum()

            return {
                "Nät": nät_namn,
                "Tailandel Kapitalbas": 100 * nuav_tail_sum / (nuav_tail_sum + nuav_ord_sum) if (nuav_tail_sum + nuav_ord_sum) > 0 else 0,
                "Tailandel Avskrivning": 100 * dep_tail_sum / (dep_tail_sum + dep_ord_sum) if (dep_tail_sum + dep_ord_sum) > 0 else 0,
            }

        resultat = [beräkna_tail_andelar(sample_df[sample_df["id_network"] == n], nätnamn.get(n, str(n))) for n in nätkoder]
        # Beräkna medel över nät
        mean_kap = []
        mean_dep = []
        for n in full_df["id_network"].unique():
            sub = beräkna_tail_andelar(full_df[full_df["id_network"] == n])
            mean_kap.append(sub["Tailandel Kapitalbas"])
            mean_dep.append(sub["Tailandel Avskrivning"])

        resultat.append({
            "Nät": "Alla nät",
            "Tailandel Kapitalbas": sum(mean_kap) / len(mean_kap),
            "Tailandel Avskrivning": sum(mean_dep) / len(mean_dep)
        })

        result_df = pd.DataFrame(resultat)

        st.info("'Alla nät' avser medelvärde för alla 159 nät.")
        st.dataframe(result_df.set_index("Nät").style.format("{:.1f} %"))

        st.markdown("#### Tailandel av kapitalbas (med tooltip)")
        st.altair_chart(alt.Chart(result_df).mark_bar().encode(
            x="Nät:N",
            y=alt.Y("Tailandel Kapitalbas:Q", scale=alt.Scale(domain=[0, 100])),
            tooltip=["Nät", alt.Tooltip("Tailandel Kapitalbas:Q", format=".1f")]
        ).properties(width=600, height=300), use_container_width=True)

        st.markdown("#### Tailandel av avskrivning (med tooltip)")
        st.altair_chart(alt.Chart(result_df).mark_bar().encode(
            x="Nät:N",
            y=alt.Y("Tailandel Avskrivning:Q", scale=alt.Scale(domain=[0, 100])),
            tooltip=["Nät", alt.Tooltip("Tailandel Avskrivning:Q", format=".1f")]
        ).properties(width=600, height=300), use_container_width=True)

        st.markdown("### Avvikelse från total Tailandel (kapitalbas)")
        tail_cols = [c for c in full_df.columns if c.startswith("nuav_tail_")]
        ord_cols = [c for c in full_df.columns if c.startswith("nuav_ord_")]
        andels_lista = []
        for nät in full_df["id_network"].unique():
            t_sum = full_df.loc[full_df["id_network"] == nät, tail_cols].sum().sum()
            o_sum = full_df.loc[full_df["id_network"] == nät, ord_cols].sum().sum()
            if (t_sum + o_sum) > 0:
                andels_lista.append(t_sum / (t_sum + o_sum))
        total_andel = sum(andels_lista) / len(andels_lista) if andels_lista else 0


        rows = []
        for nät in full_df["id_network"].unique():
            sub = full_df[full_df["id_network"] == nät]
            t_sum = sub[tail_cols].sum().sum()
            o_sum = sub[ord_cols].sum().sum()
            andel = t_sum / (t_sum + o_sum) if (t_sum + o_sum) > 0 else 0
            rows.append({
                "id_network": nät,
                "Tailandel Kapitalbas": andel * 100,
                "Avvikelse från total": (andel - total_andel) * 100
            })
        avvikelse_df = pd.DataFrame(rows)

        st.markdown(f"Totalt medelvärde (alla nät): **{total_andel * 100:.1f} %**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Topp 10 högre än total")
            st.dataframe( avvikelse_df.sort_values("Avvikelse från total", ascending=False).head(10).style.format({
            "Tailandel Kapitalbas": "{:.1f} %",
            "Avvikelse från total": "{:+.1f} %"
        }))
        with col2:
            st.markdown("#### Topp 10 lägre än total")
            st.dataframe( avvikelse_df.sort_values("Avvikelse från total", ascending=True).head(10).style.format({
            "Tailandel Kapitalbas": "{:.1f} %",
            "Avvikelse från total": "{:+.1f} %"
        }))

    # === TAB 4: Livslängdssimulering ===
    with tab4:
        st.subheader("Livslängdssimulering")

        st.info("""
        **Vad gör funktionen?**  
        Simulerar kapitalbas (NAV), årlig avskrivning och räntedel för varje komponent i ett valt nät,
        utifrån antaganden om ekonomisk och maximal livslängd.  
        Avskrivning beräknas enligt EIFS 2023:5 §5: linjär fram till ekonomisk livslängd, därefter konstant svansavskrivning.  
        Räntan beräknas som årsmedel av ingående och utgående NAV.

        **Kända brister i prototypen**  
        - Halvårsskiftet enligt §4 är förenklat (ej exakt datum).  
        - Sista året vid maxliv beräknas på årsbas, vilket kan ge något hög räntedel.  
        - Åldern antas korrekt i indata.  
        - `nuav` antas vara faktisk NAV för jämförelseåret.
        """)

        df = st.session_state["final_capbase_sample"]

        # --- Välj nät ---
        nätval = st.selectbox("Välj nät", sorted(df["id_network"].unique()))
        df_nät = df[df["id_network"] == nätval]

        # --- Välj simulerat år ---
        årval = st.selectbox("Välj simulerat år", list(YEAR_MAP.values()))
        ar_kod = [k for k, v in YEAR_MAP.items() if v == årval][0]

        # --- Parametrar ---
        eko = st.slider("Ekonomisk livslängd (år)", 10, 60, 30)
        maxx = st.slider("Maximal livslängd (år)", 20, 100, 50)

        # Säkerställ att maxliv > ekoliv
        if maxx <= eko:
            maxx = eko + 1
            st.warning(f"Maximal livslängd justerades automatiskt till {maxx} år för att vara större än ekonomisk livslängd.")

        ranta = st.slider("Kalkylränta (%)", 0.0, 10.0, 3.0, step=0.1) / 100

        # --- Simulera ---
        df_sim, agg = simulera_livslangd(
            df_nät,
            eko_livslangd=eko,
            max_livslangd=maxx,
            ranta=ranta,
            ar=ar_kod
        )

        # --- Filtrera KPI:er till valt år ---
        total = agg.loc[agg["year"] == årval].sum(numeric_only=True)

        if total.empty:
            st.warning("Inga komponenter matchade urvalet.")
        else:
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Faktisk NAV (MSEK)", f"{total['nuav_faktisk'] / 1_000_000:,.1f}")
            kpi2.metric("Simulerad NAV (MSEK)", f"{total['nuav_sim'] / 1_000_000:,.1f}",
                        delta=f"{total['diff_nav'] / 1_000_000:,.1f}")
            kpi3.metric("Totalkostnad (sim, MSEK)", f"{total['kapkost_sim'] / 1_000_000:,.1f}")

            # --- Diagram ---
            df_plot = df_sim.copy()
            df_plot["diff_nuav"] = (df_plot["nuav_sim"] - df_plot["nuav_faktisk"]) / 1_000_000
            df_plot["nuav_faktisk"] /= 1_000_000
            df_plot["nuav_sim"] /= 1_000_000
            df_plot["abs_diff"] = df_plot["diff_nuav"].abs()
            df_plot["positiv"] = df_plot["diff_nuav"] > 0
            topdiff = df_plot.nlargest(15, "abs_diff")

            chart = alt.Chart(topdiff).mark_bar().encode(
                x=alt.X("diff_nuav:Q", title="Skillnad i NAV (MSEK)", axis=alt.Axis(format=",.1f", labelAngle=0)),
                y=alt.Y("id_component:N", sort="-x", title="Komponent-ID"),
                color=alt.Color("positiv:N", scale=alt.Scale(domain=[True, False], range=["#1f77b4", "#d62728"]),
                                legend=alt.Legend(title="Ökning")),
                tooltip=[
                    "id_component", "cat", "subcat",
                    alt.Tooltip("nuav_faktisk:Q", title="Faktisk NAV (MSEK)", format=".2f"),
                    alt.Tooltip("nuav_sim:Q", title="Simulerad NAV (MSEK)", format=".2f"),
                    alt.Tooltip("diff_nuav:Q", title="Differens (MSEK)", format=".2f")
                ]
            ).properties(
                title="Största skillnader i NAV efter simulering",
                height=400
            )

            st.altair_chart(chart, use_container_width=True)

            # --- Alla monetära värden i MSEK ---
            df_sim["nuav_faktisk_msek"] = df_sim["nuav_faktisk"] / 1_000_000
            df_sim["nuav_sim_msek"] = df_sim["nuav_sim"] / 1_000_000
            df_sim["dep_ar_sim_msek"] = df_sim["dep_ar_sim"] / 1_000_000
            df_sim["ranta_sim_msek"] = df_sim["ranta_sim"] / 1_000_000
            df_sim["kapkost_sim_msek"] = df_sim["kapkost_sim"] / 1_000_000

            with st.expander("Visa komponenter (detaljer)"):
                st.dataframe(df_sim[[
                    "id_component", "cat", "subcat", "alder", "anskaffningsvärde",
                    "nuav_faktisk_msek", "nuav_sim_msek",
                    "dep_ar_sim_msek", "ranta_sim_msek", "kapkost_sim_msek"
                ]].sort_values("kapkost_sim_msek", ascending=False), use_container_width=True)
