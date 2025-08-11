# kapitalbas_app/livslangd_simulering.py
# (1) Modellspecifikation:
# Simulerar kapitalbas (NAV), årlig avskrivning och räntedel enligt EIFS 2023:5.
# Linjär avskrivning fram till ekonomisk livslängd, därefter konstant svansavskrivning fram till maximal livslängd.
# (2) Motivation:
# Säkerställa metodkorrekt beräkning av NAV, avskrivningar och kapitalkostnader i enlighet med föreskrift,
# men med förenklad ålderslogik för prototyp (ej exakt halvårsskifte).

import pandas as pd
from kapitalbas.kapitalbas_app.utils import YEAR_MAP

def simulera_livslangd(df, eko_livslangd=30, max_livslangd=50, ranta=0.03, ar=236):
    """
    Parametrar:
    - df: DataFrame med komponentdata
    - eko_livslangd: ekonomisk livslängd (år)
    - max_livslangd: maximal livslängd (år)
    - ranta: kalkylränta (andel)
    - ar: intern årskod (enligt YEAR_MAP)
    """

    df = df.copy()

    # === 1. Korrigera ålder enligt §4 (förenklad för prototyp) ===
    if "time_invest" in df.columns:
        invest_year = pd.to_datetime(df["time_invest"]).dt.year
        pre2011_mask = invest_year < 2011
        invest_year_adj = invest_year.copy()

        # Före 2011: ålder från 1 jan året efter
        invest_year_adj[pre2011_mask] += 1

        # Från 2011: förenklad regel (+0,5 år)
        post2011_mask = ~pre2011_mask
        invest_year_adj[post2011_mask] += 0.5

        current_year = YEAR_MAP.get(ar, ar)
        df["alder"] = (current_year - invest_year_adj).astype(float)
    else:
        age_col = f"age_component_{ar}"
        df["alder"] = df[age_col]

    df = df.dropna(subset=["anskaffningsvärde", "alder"])
    df = df[df["alder"] > 0]
    df["alder_sim"] = df["alder"].clip(upper=max_livslangd)

    # === 2. Beräkna ackumulerad och årlig avskrivning ===
    def beräkna_avskrivningar(a, AV):
        ack_dep = 0.0
        dep_year = 0.0
        for år in range(1, int(a) + 1):
            if år <= eko_livslangd:
                avskr = AV / eko_livslangd
            elif år <= max_livslangd:
                avskr = AV / (max_livslangd - eko_livslangd)  # konstant svans
            else:
                avskr = 0.0
            if ack_dep + avskr > AV:
                avskr = AV - ack_dep
            ack_dep += avskr
            if år == int(a):
                dep_year = avskr
        return ack_dep, dep_year

    ack_list = []
    year_list = []
    for a, AV in zip(df["alder_sim"], df["anskaffningsvärde"]):
        ack, dep_y = beräkna_avskrivningar(a, AV)
        ack_list.append(ack)
        year_list.append(dep_y)

    df["dep_ack_sim"] = ack_list
    df["dep_ar_sim"] = year_list

    # === 3. NAV och räntedel ===
    df["nuav_sim"] = (df["anskaffningsvärde"] - df["dep_ack_sim"]).clip(lower=0)
    df["nuav_faktisk"] = df["nuav"]

    # Medelvärde NAV för året (ingående + utgående) / 2
    df["nav_start"] = df["nuav_sim"] + df["dep_ar_sim"]
    df["nav_slut"] = df["nuav_sim"]
    df["nav_medel"] = (df["nav_start"] + df["nav_slut"]) / 2
    df["ranta_sim"] = ranta * df["nav_medel"]

    # === 4. Sätt alltid simulerat år ===
    current_year = YEAR_MAP.get(ar, ar)
    df["year"] = current_year

    # === 5. Totalkostnad ===
    df["kapkost_sim"] = df["dep_ar_sim"] + df["ranta_sim"]

    # === 6. Aggregera per nät och år ===
    agg = df.groupby(["id_network", "year"])[
        "nuav_faktisk", "nuav_sim", "dep_ar_sim", "ranta_sim", "kapkost_sim"
    ].sum().reset_index()
    agg["diff_nav"] = agg["nuav_sim"] - agg["nuav_faktisk"]

    return df, agg
