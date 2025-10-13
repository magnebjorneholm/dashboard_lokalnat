# kapitalbas_app/policy_playground_view.py

import streamlit as st
import pandas as pd
import altair as alt
from kapitalbas.kapitalbas_app.data_loader import load_tail_sample, load_tail_full
from kapitalbas.kapitalbas_app.översikt_view import pick_year_columns, YEAR_CODE

YEAR_MAP = {
    229: 2016, 230: 2017, 231: 2018, 232: 2019,
    233: 2020, 234: 2021, 235: 2022, 236: 2023
}


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
        scenario_df["year"] = scenario_df["time"].map(YEAR_MAP).astype(int)

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

        scenario_df["capcost_with_tail"] = (
            (scenario_df[[c for c in scenario_df.columns if c.startswith("return_")]].sum(axis=1) * rate_factor +
            scenario_df[[c for c in scenario_df.columns if c.startswith("dep_")]].sum(axis=1)) / 1_000_000
        )

        scenario_df["capcost_without_tail"] = (
            (scenario_df[[c for c in scenario_df.columns if c.startswith("return_ord")]].sum(axis=1) * rate_factor +
            scenario_df[[c for c in scenario_df.columns if c.startswith("dep_ord")]].sum(axis=1)) / 1_000_000
        )

        ts_summary = scenario_df.groupby("year")[["capcost_with_tail", "capcost_without_tail"]].sum().reset_index()
        plot_df = ts_summary.melt(id_vars="year", var_name="Scenario", value_name="Kapitalkostnad")
        plot_df["Scenario"] = plot_df["Scenario"].map({
            "capcost_with_tail": "Med Tail",
            "capcost_without_tail": "Utan Tail"
        })

        st.altair_chart(alt.Chart(plot_df).mark_line(point=True).encode(
            x=alt.X("year:O", title="År"),
            y=alt.Y("Kapitalkostnad:Q", title="MSEK"),
            color=alt.Color("Scenario:N", title="Scenario")
        ).properties(width=700, height=400), width='stretch')


    # === TAB 2: KPI-simulering ===
    with tab2:
        st.markdown("#### Simulera förmögenhetsbevarande värdering (KPI-indexering)")
        st.warning("Datafel i nuläget, läs labbjournal")

    # === TAB 3: Tail-andelar ===
    with tab3:
        sample_df = load_tail_sample()
        full_df = load_tail_full()

        # Plocka bara årskolumner för 2023
        sample_year = pick_year_columns(sample_df, YEAR_CODE)
        full_year = pick_year_columns(full_df, YEAR_CODE)

        nätkoder = sorted(sample_df["id_network"].unique())
        nätnamn = {3035: "Stort nät (3035)", 160: "Medelstort nät (160)", 7: "Kommunalt nät (7)"}

        def beräkna_tail_andelar(df, nät_namn="Totalt"):
            """Beräknar tailandelar för ett nät eller en samling nät. Varje nät får lika vikt."""
            df_year = pd.concat(
                [df[["id_network"]].reset_index(drop=True),
                pick_year_columns(df, YEAR_CODE).reset_index(drop=True)],
                axis=1
            )
            nuav_andel = ((df_year["nuav_tail"] / (df_year["nuav_tail"] + df_year["nuav_ord"])) * 100).mean()
            dep_andel = ((df_year["dep_tail"] / (df_year["dep_tail"] + df_year["dep_ord"])) * 100).mean()
            return {
                "Nät": nät_namn,
                "Tailandel Kapitalbas (%)": round(nuav_andel, 1),
                "Tailandel Avskrivning (%)": round(dep_andel, 1),
            }

        # Lista med resultat per nät i sample
        resultat = [
            beräkna_tail_andelar(sample_df[sample_df["id_network"] == n], nätnamn.get(n, str(n)))
            for n in nätkoder
        ]

        # Lägg till medelvärde för alla nät (varje nät lika vikt)
        resultat.append(beräkna_tail_andelar(full_df, "Alla nät"))

        result_df = pd.DataFrame(resultat)

        st.info("'Alla nät' avser medelvärde för alla nät, varje nät viktas lika.")
        st.dataframe(result_df.set_index("Nät").style.format("{:.1f} %"))

        # Diagram: Kapitalbas
        st.markdown("#### Tailandel av kapitalbas")
        st.altair_chart(
            alt.Chart(result_df).mark_bar().encode(
                x="Nät:N",
                y=alt.Y("Tailandel Kapitalbas (%):Q", scale=alt.Scale(domain=[0, 100])),
                tooltip=["Nät", alt.Tooltip("Tailandel Kapitalbas (%):Q", format=".1f")]
            ).properties(width=600, height=300),
            width='stretch'
        )

        # Diagram: Avskrivning
        st.markdown("#### Tailandel av avskrivning")
        st.altair_chart(
            alt.Chart(result_df).mark_bar().encode(
                x="Nät:N",
                y=alt.Y("Tailandel Avskrivning (%):Q", scale=alt.Scale(domain=[0, 100])),
                tooltip=["Nät", alt.Tooltip("Tailandel Avskrivning (%):Q", format=".1f")]
            ).properties(width=600, height=300),
            width='stretch'
        )

        # ===== Avvikelse från medel – Kapitalbas =====
        st.markdown("### Avvikelse från medel Tailandel (kapitalbas) – år 2023")

        full_year_cap = pd.concat(
            [full_df[["id_network"]].reset_index(drop=True),
            pick_year_columns(full_df, YEAR_CODE).reset_index(drop=True)],
            axis=1
        )
        andel_per_nät_cap = (full_year_cap["nuav_tail"] / (full_year_cap["nuav_tail"] + full_year_cap["nuav_ord"])) * 100
        medel_andel_cap = andel_per_nät_cap.mean()

        avvikelse_df_cap = pd.DataFrame({
            "id_network": full_year_cap["id_network"],
            "Tailandel Kapitalbas": andel_per_nät_cap.round(1),
            "Avvikelse från medel": (andel_per_nät_cap - medel_andel_cap).round(1)
        }).drop_duplicates(subset="id_network")

        st.markdown(f"Medelvärde (alla nät): **{medel_andel_cap:.1f} %**")
        col1, col2 = st.columns(2)

        col1.markdown("#### Topp 10 högre än medel")
        col1.dataframe(avvikelse_df_cap.sort_values("Avvikelse från medel", ascending=False).head(10).style.format({
            "Tailandel Kapitalbas": "{:.1f} %",
            "Avvikelse från medel": "{:+.1f} %"
        }))

        col2.markdown("#### Topp 10 lägre än medel")
        col2.dataframe(avvikelse_df_cap.sort_values("Avvikelse från medel", ascending=True).head(10).style.format({
            "Tailandel Kapitalbas": "{:.1f} %",
            "Avvikelse från medel": "{:+.1f} %"
        }))

        # ===== Avvikelse från medel – Avskrivning =====
        st.markdown("### Avvikelse från medel Tailandel (avskrivning) – år 2023")

        andel_per_nät_dep = (full_year_cap["dep_tail"] / (full_year_cap["dep_tail"] + full_year_cap["dep_ord"])) * 100
        medel_andel_dep = andel_per_nät_dep.mean()

        avvikelse_df_dep = pd.DataFrame({
            "id_network": full_year_cap["id_network"],
            "Tailandel Avskrivning": andel_per_nät_dep.round(1),
            "Avvikelse från medel": (andel_per_nät_dep - medel_andel_dep).round(1)
        }).drop_duplicates(subset="id_network")

        st.markdown(f"Medelvärde (alla nät): **{medel_andel_dep:.1f} %**")
        col3, col4 = st.columns(2)

        col3.markdown("#### Topp 10 högre än medel")
        col3.dataframe(avvikelse_df_dep.sort_values("Avvikelse från medel", ascending=False).head(10).style.format({
            "Tailandel Avskrivning": "{:.1f} %",
            "Avvikelse från medel": "{:+.1f} %"
        }))

        col4.markdown("#### Topp 10 lägre än medel")
        col4.dataframe(avvikelse_df_dep.sort_values("Avvikelse från medel", ascending=True).head(10).style.format({
            "Tailandel Avskrivning": "{:.1f} %",
            "Avvikelse från medel": "{:+.1f} %"
        }))

    with tab4:
        st.markdown("### Livslängdssimulering")
        st.warning("Jobbar på ny version.")
        # Placeholder for future implementation
        # simulera_livslangd()  # Uncomment when the function is implemented