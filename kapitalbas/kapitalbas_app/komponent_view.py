import streamlit as st
import pandas as pd

YEAR_LABEL = 2023
NUAV_COL = "nuav_236"
DEP_COL = "dep_236_ordinary"
TOLERANS = 1  # SEK

def prepare_component_data(df):
    """Förbereder komponentdatan för analys utifrån sample-strukturen."""
    df = df.copy()

    # Beräkningar
    df["nuav_total"] = df[NUAV_COL]  # Endast total nuav i samplet
    df["helt_avskriven"] = (df[DEP_COL] - df["nuav_total"]).abs() <= TOLERANS
    df["negativt_nuav"] = df["nuav_total"] < 0

    return df

def summering_per_kategori(df):
    """Summerar per kategori."""
    return df.groupby("cat_encode", observed=False).agg(
        antal_komponenter=("id_component", "count"),
        antal_helt_avskrivna=("helt_avskriven", "sum"),
        antal_negativt_nuav=("negativt_nuav", "sum"),
        positivt_nuav=("nuav_total", lambda x: x[x > 0].sum()),
        negativt_nuav=("nuav_total", lambda x: x[x < 0].sum()),
        netto_nuav=("nuav_total", "sum")
    ).reset_index()

def show_komponent_view(final_capbase_sample):
    # --- Företagsval i sidopanelen ---
    företag_val = st.sidebar.selectbox(
        "Välj företag (id_network)",
        options=[7, 160, 3035],
        format_func=lambda x: f"Nät {x}"
    )

    tab1, tab2 = st.tabs(["Alla komponenter", "Inaktivt kapital"])

    # ===== TAB 1 =====
    with tab1:
        st.subheader(f"Alla komponenter – år {YEAR_LABEL} – Nät {företag_val}")

        df_all = prepare_component_data(final_capbase_sample)
        df_all = df_all[df_all["id_network"] == företag_val]

        filter_helt = st.checkbox("Visa endast helt avskrivna", key="tab1_helt")
        filter_neg = st.checkbox("Visa endast negativt nuav", key="tab1_neg")

        mask = pd.Series(True, index=df_all.index)
        if filter_helt:
            mask &= df_all["helt_avskriven"]
        if filter_neg:
            mask &= df_all["negativt_nuav"]

        df_filtered = df_all[mask]
        st.info(f"Nät {företag_val} har {len(df_filtered)} komponenter efter filter.")

        st.markdown("### Summering per kategori")
        st.dataframe(summering_per_kategori(df_filtered))

        st.markdown("#### Netto nuav per kategori (SEK)")
        st.bar_chart(df_filtered.groupby("cat_encode", observed=False)["nuav_total"].sum())

        st.markdown("#### Antal helt avskrivna per kategori")
        st.bar_chart(df_filtered.groupby("cat_encode", observed=False)["helt_avskriven"].sum())

        st.markdown("### Komponenter (detaljvy)")
        st.dataframe(df_filtered[[
            "id_network", "id_component", "cat_encode", "subcat",
            NUAV_COL, DEP_COL, "helt_avskriven", "negativt_nuav"
        ]])

    # ===== TAB 2 =====
    with tab2:
        st.subheader(f"Inaktivt kapital – år {YEAR_LABEL} – Nät {företag_val}")

        df_selected = prepare_component_data(final_capbase_sample)
        df_selected = df_selected[df_selected["id_network"] == företag_val]

        df_selected["inaktivt_kapital"] = (
            df_selected["helt_avskriven"] & (df_selected["nuav_total"] > 0)
        )

        inaktivt_df = df_selected[df_selected["inaktivt_kapital"]].copy()
        st.info(f"Antal inaktiva komponenter i nät {företag_val}: {len(inaktivt_df)}")

        if inaktivt_df.empty:
            st.warning("Inga komponenter uppfyller villkoren för inaktivt kapital i valt nät och år.")
        else:
            st.metric(
                "Totalt värde inaktivt kapital (SEK)",
                f"{inaktivt_df['nuav_total'].sum():,.0f}"
            )

            st.markdown("#### Lista över inaktiva komponenter")
            st.dataframe(inaktivt_df[[
                "id_component", "cat_encode", "subcat",
                NUAV_COL, DEP_COL, "helt_avskriven"
            ]])

            st.markdown("#### Summering per kategori (inaktivt kapital)")
            st.dataframe(summering_per_kategori(inaktivt_df))

            st.markdown("#### Netto nuav per kategori (SEK) – Inaktivt kapital")
            st.bar_chart(inaktivt_df.groupby("cat_encode", observed=False)["nuav_total"].sum())

            st.markdown("#### Antal helt avskrivna per kategori – Inaktivt kapital")
            st.bar_chart(inaktivt_df.groupby("cat_encode", observed=False)["helt_avskriven"].sum())

        st.caption("*Inaktivt kapital = Helt avskriven komponent med positivt nuanskaffningsvärde (EIFS 2023:5, KENT-handboken)*")
