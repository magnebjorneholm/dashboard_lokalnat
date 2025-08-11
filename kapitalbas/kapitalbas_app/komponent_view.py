# kapitalbas_app/komponent_view.py

import streamlit as st
import pandas as pd
import io
from kapitalbas.kapitalbas_app.data_loader import load_component_sample

def show_komponenter():
    """Visar komponentfliken inklusive inaktivt kapital."""
    st.subheader("Komponenter – Analys på anläggningsnivå och inaktivt kapital")
    st.warning("Negativa värden förekommer (även i metafil), se över varför det är så och om man kan separera? (om det är önskat).")

    comp_df = load_component_sample()

    comp_df["year"] = pd.to_datetime(comp_df["time_invest"], errors="coerce").dt.year
    comp_df = comp_df.dropna(subset=["year"])
    comp_df["age"] = 2024 - comp_df["year"]

    tab1, tab2 = st.tabs(["Komponentanalys", "Inaktivt kapital"])

    # === TAB 1 ===
    with tab1:
        networks = sorted(comp_df["id_network"].unique())
        categories = sorted(comp_df["cat"].dropna().unique())
        subcategories = sorted(comp_df["subcat"].dropna().unique())

        selected_network = st.sidebar.selectbox("Välj nät", networks)
        min_age = int(comp_df["age"].min())
        max_age = int(comp_df["age"].max())
        age_range = st.sidebar.slider("Filtrera ålder (år)", min_age, max_age, (min_age, max_age))
        selected_cats = st.sidebar.multiselect("Filtrera kategori (cat)", options=categories, default=categories)
        selected_subcats = st.sidebar.multiselect("Filtrera subkategori (subcat)", options=subcategories, default=subcategories)

        filtered_df = comp_df[
            (comp_df["id_network"] == selected_network) &
            (comp_df["age"].between(age_range[0], age_range[1])) &
            (comp_df["cat"].isin(selected_cats)) &
            (comp_df["subcat"].isin(selected_subcats))
        ]

        with st.expander("🔎 Felsök filtrering"):
            st.write(f"Antal rader totalt i nät {selected_network}: {len(comp_df[comp_df['id_network'] == selected_network])}")
            st.write(f"Efter åldersfilter: {len(filtered_df)}")
            st.write(f"Efter kategori-filter: {len(filtered_df[filtered_df['cat'].isin(selected_cats)])}")
            st.write(f"Efter subkategori-filter: {len(filtered_df[filtered_df['subcat'].isin(selected_subcats)])}")
            st.write(f"🔴 Slutlig filtrerad tabell: {len(filtered_df)} rader")

        st.markdown(f"### Komponenter i nät {selected_network}")
        st.dataframe(
            filtered_df[["id_component", "cat", "subcat", "techspec", "volt", "time_invest", "age", "nuav"]]
            .sort_values("age", ascending=False)
            .reset_index(drop=True),
            use_container_width=True
        )

        cat_count = filtered_df["cat"].value_counts().reset_index()
        cat_count.columns = ["Kategori", "Antal"]
        st.markdown("### Antal komponenter per kategori")
        st.bar_chart(cat_count.set_index("Kategori"))

        st.markdown("### Åldersfördelning")
        age_bins = pd.cut(filtered_df["age"], bins=range(0, 81, 5))
        age_dist = age_bins.value_counts().sort_index()
        labels = [f"{int(i.left)}–{int(i.right)} år" for i in age_dist.index]
        age_dist.index = pd.CategoricalIndex(labels, ordered=True, categories=labels)
        st.bar_chart(age_dist)

        st.markdown("### Exportera till Excel")
        if not filtered_df.empty:
            export_cols = ["id_component", "cat", "subcat", "techspec", "volt", "time_invest", "age", "nuav"]
            to_export = filtered_df[export_cols].sort_values("age", ascending=False)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                to_export.to_excel(writer, sheet_name="Komponenter", index=False)
            buffer.seek(0)
            st.download_button(
                label="📥 Ladda ner som Excel",
                data=buffer,
                file_name=f"komponenter_nät_{selected_network}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Ingen data att exportera – kontrollera filtren.")

    # === TAB 2 ===
    with tab2:
        st.markdown("### Inaktivt kapital – indikatorer på överskattning eller dataproblem")
        st.info("⚠️ Denna flik visar endast nät 160 som exempelnät i prototypen. Bortse från valen i sidopanelen.")

        st.expander("ℹ️ Vad visar denna flik?").markdown("""
        Denna vy visar komponenter som är **potentiellt inaktuella eller osäkra** i kapitalbasen. En komponent visas här om den är:

        - **helt avskriven** (`maxdep = 124`) eller
        - **har negativt nuanskaffningsvärde** (`nuav < 0`)
        """)

        df160 = comp_df[comp_df["id_network"] == 160].copy()
        df160["avskriven"] = df160["maxdep"].apply(lambda x: "Ja" if x == 124 else "Nej")
        df160["helt_avskriven"] = df160["maxdep"] == 124
        df160["neg_nuav"] = df160["nuav"] < 0
        df160["inaktiv"] = df160["helt_avskriven"] | df160["neg_nuav"]
        inaktiv_df = df160[df160["inaktiv"]].copy()

        catval = st.multiselect("Filtrera kategori", sorted(inaktiv_df["cat"].dropna().unique()), default=None)
        statusval = st.multiselect("Filtrera status", ["Helt avskriven", "Negativt nuav"], default=["Helt avskriven", "Negativt nuav"])

        status_mask = pd.Series([False] * len(inaktiv_df), index=inaktiv_df.index)
        if "Helt avskriven" in statusval:
            status_mask |= inaktiv_df["helt_avskriven"]
        if "Negativt nuav" in statusval:
            status_mask |= inaktiv_df["neg_nuav"]

        filt_df = inaktiv_df[status_mask & (inaktiv_df["cat"].isin(catval) if catval else True)]

        if filt_df.empty:
            st.info("Inga inaktiva komponenter hittades för valt filter.")
        else:
            st.markdown("#### Summering per kategori")
            summary_df = df160.copy()
            summary_df["negativ_flagga"] = summary_df["nuav"] < 0
            summary_df["positiv_flagga"] = summary_df["nuav"] > 0

            kategori_summary = summary_df.groupby("cat").agg(
                Antal_komponenter=("id_component", "count"),
                Antal_negativa=("negativ_flagga", "sum"),
                Positivt_nuav=("nuav", lambda x: x[x > 0].sum()),
                Negativt_nuav=("nuav", lambda x: x[x < 0].sum()),
                Totalt_nuav=("nuav", "sum")
            ).reset_index()
            kategori_summary["Andel negativa komponenter"] = kategori_summary["Antal_negativa"] / kategori_summary["Antal_komponenter"]

            st.dataframe(
                kategori_summary[[
                    "cat", "Antal_komponenter", "Andel negativa komponenter",
                    "Positivt_nuav", "Negativt_nuav", "Totalt_nuav"
                ]]
                .rename(columns={
                    "cat": "Kategori",
                    "Totalt_nuav": "Netto (SEK)",
                    "Positivt_nuav": "Positivt nuanskaffningsvärde (SEK)",
                    "Negativt_nuav": "Negativt nuanskaffningsvärde (SEK)"
                })
                .style.format({
                    "Netto (SEK)": "{:,.0f}",
                    "Positivt nuanskaffningsvärde (SEK)": "{:,.0f}",
                    "Negativt nuanskaffningsvärde (SEK)": "{:,.0f}",
                    "Andel negativa komponenter": "{:.0%}"
                })
            )

            st.markdown("#### Inaktiva komponenter")
            st.dataframe(
                filt_df[["id_component", "cat", "subcat", "time_to", "avskriven", "nuav"]]
                .rename(columns={"avskriven": "Helt avskriven", "nuav": "Nuanskaffningsvärde (SEK)"})
                .style.format({"Nuanskaffningsvärde (SEK)": "{:,.0f}"})
            )
