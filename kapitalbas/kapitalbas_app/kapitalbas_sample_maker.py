# Innehåller tre representativa nät + kontroll av dataintegritet

import pandas as pd

# === Filvägar ===
input_path = "kapitalbas_filer/final_capbase.parquet"
output_path = "kapitalbas_filer/final_capbase_sample.parquet"

# === Valda nät ===
valda_nät = [3035, 160, 7]

# === Läs in komponentdata för dessa nät ===
print("Läser in komponentdata...")
df = pd.read_parquet(input_path, filters=[("id_network", "in", valda_nät)])

# === Kontroll 1: Har alla nät kommit med? ===
faktiska_nät = set(df['id_network'].unique())
saknade = set(valda_nät) - faktiska_nät
if saknade:
    print(f"❌ VARNING: Följande nät saknas i filen: {saknade}")
else:
    print("✅ Alla tre nät har lästs in korrekt.")

# === Kontroll 2: Finns nyckelkolumner för analys? ===
viktiga_kolumner = ['nuav_ord_229', 'age_component', 'time_invest']
saknade_kolumner = [col for col in viktiga_kolumner if col not in df.columns]
if saknade_kolumner:
    print(f"❌ VARNING: Saknar viktiga kolumner: {saknade_kolumner}")
else:
    print("✅ Alla viktiga kolumner finns med.")

# === Kontroll 3: Summerad kapitalbas per nät (för sanity check) ===
if 'nuav_ord_229' in df.columns:
    print("\n💰 Summerad kapitalbas (nuav_ord_229) per nät (MSEK):")
    print((df.groupby('id_network')['nuav_ord_229'].sum() / 1_000_000).round(2))

# === Spara till ny fil ===
df.to_parquet(output_path, index=False)
print("\n✅ Prototypfil sparad som:", output_path)



