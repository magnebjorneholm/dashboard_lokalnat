# ANPASSAD KONTROLL – baserad på kolumner i final_capbase_sample.parquet

import pandas as pd

df = pd.read_parquet("kapitalbas_filer/final_capbase_sample.parquet")

# Kontroll 1: Alla nät med?
valda_nät = [3035, 160, 7]
faktiska_nät = set(df['id_network'].unique())
saknade = set(valda_nät) - faktiska_nät
if saknade:
    print(f"❌ VARNING: Följande nät saknas: {saknade}")
else:
    print("✅ Alla tre nät finns med.")

# Kontroll 2: Viktiga kolumner (anpassad)
viktiga_kolumner = ['nuav', 'time_invest']
saknade_kolumner = [col for col in viktiga_kolumner if col not in df.columns]
if saknade_kolumner:
    print(f"❌ Saknade kolumner: {saknade_kolumner}")
else:
    print("✅ Nyckelkolumner finns: nuav och time_invest")

# Kontroll 3: Summerad kapitalbas per nät
# print("\n💰 Summerad kapitalbas (nuav) per nät (MSEK):")
# print((df.groupby('id_network')['nuav'].sum() / 1_000_000).round(2))

# (valfritt) Beräkna ålder om du vill
df['age_estimate'] = 2024 - df['time_invest']

df = pd.read_parquet("kapitalbas_filer/final_capbase_sample.parquet")
df_n7 = df[df["id_network"] == 7]
print(df_n7["time_invest"].describe())
print("\nUnika värden eller de vanligaste:")
print(df_n7["time_invest"].value_counts().sort_index())

for nid in [160, 3035]:
    df_n = df[df["id_network"] == nid]
    print(f"\n=== Nät {nid} ===")
    print(df_n["time_invest"].describe())
    print(df_n["time_invest"].value_counts().sort_index())


