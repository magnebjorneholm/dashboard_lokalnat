import pandas as pd

# === Parametrar ===
input_path = "kapitalbas_filer/capbase_compress_tail.parquet"
output_path = "kapitalbas_filer/capbase_compress_tail_sample.parquet"


valda_nät = [3035, 160, 7]  # Litet kommunalt, medelstort, stort

# === Läs in metadata (kolumner + id_network) ===
print("🔍 Läser in nät och kolumnstruktur...")
meta_df = pd.read_parquet(input_path, columns=["id_network"])
unikt_nät = sorted(meta_df["id_network"].unique())
print(f"✅ Antal nät i full dataset: {len(unikt_nät)}")
print(f"📌 Representativa nät som efterfrågas: {valda_nät}")

# === Kontroll: Finns alla nät?
saknas = [n for n in valda_nät if n not in unikt_nät]
if saknas:
    print(f"❌ Följande nät saknas i datasetet: {saknas}")
    raise SystemExit("⚠️ Avbryter. Du måste uppdatera listan eller kontrollera datakällan.")

# === Läs in all data för valda nät
print("📥 Läser in tail-dataset för representativa nät...")
df = pd.read_parquet(input_path, filters=[("id_network", "in", valda_nät)])
print(f"✅ Inläst: {df.shape[0]} rader, {df.shape[1]} kolumner")

# === Visa exempel på tail-relevanta kolumner
nuav_cols = [c for c in df.columns if "nuav_" in c]
dep_cols = [c for c in df.columns if "dep_" in c]
return_cols = [c for c in df.columns if "return_" in c]
print(f"📊 Kolumner för kapitalbas: {len(nuav_cols)}")
print(f"📉 Kolumner för avskrivning: {len(dep_cols)}")
print(f"💸 Kolumner för avkastning: {len(return_cols)}")

# === Fullständig kolumnöversikt ===
print("\n🧾 Fullständig lista över kolumner:")
for col in df.columns:
    print(f"  - {col}")

# === Spara till ny fil
print(f"💾 Sparar sample till: {output_path}")
df.to_parquet(output_path, index=False)
print("✅ Klart!")