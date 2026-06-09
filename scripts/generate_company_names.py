"""Generate the curated company-name reference file.

Reads the id-reconciliation reference (authoritative full legal names in the
``id_firm`` column) and joins a hand-curated short name per ``REId`` to produce
``data/reference/company_names.csv`` with three columns:

    REId, name_full, name_short

The short names below were curated by hand (brand names, disambiguation between
look-alike companies, trimmed legal forms). ``name_full`` always comes from the
reconciliation file so spelling and encoding stay authoritative.

Run:
    ./venv/Scripts/python.exe scripts/generate_company_names.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "data" / "reference" / "reconciliation_id_network_firm_dmu.csv"
TARGET = REPO_ROOT / "data" / "reference" / "company_names.csv"

# Curated short name per REId. REL03050 carries "(Viggafors)" so the standard
# "Kortnamn (REId)" display pattern stays unambiguous against REL00139.
SHORT_NAMES = {
    "REL00018": "Borlänge Energi",
    "REL00149": "PiteEnergi",
    "REL00091": "Affärsverken Karlskrona",
    "RET03036": "Svenska kraftnät",
    "REL00001": "Ale El",
    "REL03049": "Alingsås Energi",
    "REL00003": "Almnäs Bruk",
    "REL00004": "Alvesta Elnät",
    "REL00005": "Arvika Teknik",
    "REL00007": "Bengtsfors Energi",
    "REL00008": "Bergs Tingslags",
    "REL00010": "Bjäre Kraft",
    "REL00011": "Bjärke Energi",
    "REL00014": "Blåsjön Nät",
    "REL00015": "Bodens Energi",
    "REL00016": "Boo Energi",
    "REL00017": "Borgholm Energi",
    "REL00019": "Borås Elnät",
    "REL01012": "Brittedals Elnät",
    "REL00021": "Bromölla Energi",
    "REL00023": "C4 Elnät",
    "REL00024": "Carlfors Bruk",
    "REL03009": "Dala Energi",
    "REL00025": "Degerfors Energi",
    "REL03028": "E.ON",
    "REL00030": "Eksjö Elnät",
    "REL03035": "Ellevio",
    "REL00031": "Emmaboda Elnät",
    "REL00035": "Eskilstuna Energi",
    "REL00037": "Falbygdens Energi",
    "REL00038": "Falkenberg Energi",
    "REL03015": "Falu Elnät",
    "REL00040": "Filipstad Energi",
    "REL00043": "Gislaved Energi",
    "REL00945": "Gotlands Elnät",
    "REL00049": "Grästorps Energi",
    "REL00885": "Gävle Energi",
    "REL00062": "Göteborg Energi",
    "REL00585": "Götene Elförening",
    "REL00064": "Habo Kraft",
    "REL00067": "Hallstaviks Elverk",
    "REL00033": "Halmstads Energi",
    "REL00938": "Hedemora Elnät",
    "REL00072": "Herrljunga Elektriska",
    "REL03041": "Hjo Elnät",
    "REL00074": "Hjärtums Elförening",
    "REL00075": "Hofors Elverk",
    "REL00576": "Härjeåns",
    "REL00077": "Härnösand Elnät",
    "REL00078": "Härryda Energi",
    "REL00080": "Höganäs Energi",
    "REL00083": "Jukkasjärvi",
    "REL00085": "Jämtkraft",
    "REL00086": "Jönköping Energi",
    "REL00087": "Kalmar Energi",
    "REL03043": "Karlsborgs Elnät",
    "REL03047": "Karlshamn Elnät",
    "REL00090": "Karlskoga Elnät",
    "REL00092": "Karlstads Elnät",
    "REL00886": "Kraftringen",
    "REL00098": "Kristinehamns Elnät",
    "REL00100": "Kungälv Energi",
    "REL00899": "Kvänumbygdens Energi",
    "REL00121": "LEVA i Lysekil",
    "REL00590": "LKAB Nät",
    "REL00103": "Landskrona Energi",
    "REL00106": "Lerum Energi",
    "REL03038": "Lidköping Elnät",
    "REL00944": "Linde Energi",
    "REL00112": "Ljungby Energi",
    "REL00113": "Ljusdal Elnät",
    "REL00118": "Luleå Energi",
    "REL00123": "Malung-Sälens Elnät",
    "REL00126": "Mellersta Skånes Kraft",
    "REL00127": "Mjölby Kraft",
    "REL00267": "Mälarenergi",
    "REL00128": "Mölndal Energi",
    "REL00130": "Nacka Energi",
    "REL00182": "Njudung Sävsjö",
    "REL00936": "Njudung Vetlanda",
    "REL00133": "Norrtälje Energi",
    "REL00135": "Nossebroortens Energi",
    "REL00137": "Nybro Elnät",
    "REL00139": "Näckåns Elnät",
    "REL03050": "Näckåns Elnät (Viggafors)",
    "REL00141": "Nässjö Affärsverk",
    "REL00143": "Olofströms Kraft",
    "REL00144": "Olseröds El",
    "REL00146": "Oskarshamn Energi",
    "REL00147": "Oxelö Energi",
    "REL00148": "Partille Energi",
    "REL00152": "Ronneby Miljöteknik",
    "REL00156": "Rödeby Elverk",
    "REL00160": "SEVAB",
    "REL00157": "Sala-Heby Energi",
    "REL00158": "Sandhult-Sandared",
    "REL01010": "Sandviken Energi",
    "REL00163": "Sjogerstads El",
    "REL00164": "Sjöbo Elnät",
    "REL03042": "Skara Elnät",
    "REL00824": "Skellefteå Kraft",
    "REL00167": "Skurups Elverk",
    "REL00168": "Skyllbergs Bruk",
    "REL00169": "Skånska Energi",
    "REL00170": "Skövde Energi",
    "REL00171": "Smedjebacken Energi",
    "REL00173": "Sollentuna Energi",
    "REL00175": "Staffanstorps Energi",
    "REL00177": "Sturefors El",
    "REL00178": "Sundsvall Elnät",
    "REL00183": "Söderhamn Elnät",
    "REL00184": "Södra Hallands Kraft",
    "REL00185": "Sölvesborg Energi",
    "REL00965": "Sörbylunds Elnät",
    "REL00093": "Tekniska verken Katrineholm",
    "REL00111": "Tekniska verken Linköping",
    "REL00186": "Telge Nät",
    "REL00187": "Tibro Elnät",
    "REL00332": "Tidaholms Elnät",
    "REL00937": "Tranås Energi",
    "REL03019": "Trelleborgs Elnät",
    "REL00191": "Trollhättan Energi",
    "REL00193": "Töre Energi",
    "REL00195": "Uddevalla Energi",
    "REL03044": "Ulricehamn Energi",
    "REL00584": "Umeå Energi",
    "REL00012": "Upplands Energi",
    "REL03016": "Vaggeryds Elverk",
    "REL00201": "Vallebygdens Energi",
    "REL00203": "Vara Energi",
    "REL00204": "Varberg Energi",
    "REL00205": "Varbergsortens Elkraft",
    "REL03030": "Vattenfall",
    "REL00958": "Vimmerby Energi",
    "REL00594": "VänerEnergi",
    "REL00235": "Värnamo Elnät",
    "REL00570": "Västerbergslagens Elnät",
    "REL00239": "Västerviks Elnät",
    "REL00242": "Västra Orust Energi",
    "REL00243": "Växjö Energi",
    "REL00244": "Ystad Energi",
    "REL00246": "Ålem Energi",
    "REL00249": "Årsunda Kraft",
    "REL00959": "Åsele Elnät",
    "REL00904": "Öresundskraft",
    "REL00364": "Österlens Kraft",
    "REL00255": "Östra Kinds Elkraft",
    "REL00029": "Övertorneå Energi",
    "REL00257": "Övik Energi",
}


def main() -> None:
    df = pd.read_csv(SOURCE)
    out = df[["REId"]].copy()
    out["name_full"] = df["id_firm"].astype(str).str.strip()

    missing = sorted(set(out["REId"]) - set(SHORT_NAMES))
    if missing:
        raise ValueError(f"No curated short name for REId(s): {missing}")

    out["name_short"] = out["REId"].map(SHORT_NAMES)
    out = out.sort_values("name_full").reset_index(drop=True)
    out.to_csv(TARGET, index=False, encoding="utf-8")
    print(f"Wrote {len(out)} rows -> {TARGET.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
