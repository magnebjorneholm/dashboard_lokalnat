# livslangd_simulering.py
# (1) Modellspecifikation: Simulerar kapitalbas, årlig avskrivning och räntedel med flexibla antaganden om ekonomisk och maximal livslängd.
# (2) Motivation: Skapa korrekt och policyrelevant bild av hur reglerade kapitalkostnader påverkas av livslängdsantaganden.

import pandas as pd

def simulera_livslangd(df, eko_livslangd=30, max_livslangd=50, ranta=0.03, ar=236):
    """
    Parametrar:
    - df: DataFrame med komponentdata
    - eko_livslangd: ekonomisk livslängd i år (default 30)
    - max_livslangd: maximal livslängd i år (default 50)
    - ranta: kalkylränta som andel (default 3%)
    - ar: tillsynsår (default 236 = 2024)

    Returnerar:
    - df: DataFrame med NAV, dep, ränta och kapitalkostnad före och efter simulering
    - agg: summerad skillnad per nät
    """

    df = df.copy()
    age_col = f"age_component_{ar}"
    df["alder"] = df[age_col]

    df = df.dropna(subset=["anskaffningsvärde", "alder"])
    df = df[df["alder"] > 0]

    # Begränsa ålder till max livslängd
    df["alder_sim"] = df["alder"].clip(upper=max_livslangd)

    # Ackumulerad avskrivning enl. trappa
    def ackumulerad_dep(row):
        a = row["alder_sim"]
        AV = row["anskaffningsvärde"]

        if a <= eko_livslangd:
            return AV * a / eko_livslangd
        elif a <= max_livslangd:
            # Linjär avskrivning över svansperioden
            rest = AV * (1 - 1)  # fullt avskriven efter eko i Ei:s metod
            
            # Alternativ pragmatisk trappa för kontroll
            return AV * (1 - (max_livslangd - a)/(max_livslangd - eko_livslangd))
        else:
            return AV  # helt avskriven

    df["dep_ack_sim"] = df.apply(ackumulerad_dep, axis=1)
    df["nuav_sim"] = df["anskaffningsvärde"] - df["dep_ack_sim"]
    df["nuav_sim"] = df["nuav_sim"].clip(lower=0)

    # Faktisk NAV är enligt Ei:
    df["nuav_faktisk"] = df["nuav"]

    # Årlig avskrivning (approx): 
    df["dep_ar_sim"] = df["dep_ack_sim"] / df["alder_sim"]

    # Ränta: medelvärde NAV över perioden
    df["nav_start"] = df["anskaffningsvärde"]
    df["nav_slut"] = df["nuav_sim"]
    df["nav_medel"] = (df["nav_start"] + df["nav_slut"]) / 2
    df["ranta_sim"] = ranta * df["nav_medel"]

    # Totalkostnad
    df["kapkost_sim"] = df["dep_ar_sim"] + df["ranta_sim"]

    # Aggregat per nät
    agg = df.groupby("id_network")[[
        "nuav_faktisk", "nuav_sim", "dep_ar_sim", "ranta_sim", "kapkost_sim"
    ]].sum().reset_index()

    agg["diff_nav"] = agg["nuav_sim"] - agg["nuav_faktisk"]

    return df, agg