"""
Skapar en datakatalog för alla kapitalbas-relaterade .parquet-filer.
- Läser bara in första 100 rader för att inte sega ner projektet
- Skriver ut en snabb översikt till terminalen
- Exporterar fullständig kolumnlista + metadata till data_katalog.csv
"""

import pandas as pd
import os

data_folder = "kapitalbas_filer"
output_csv = "data_katalog.csv"

rows = []

for file in os.listdir(data_folder):
    if file.endswith(".parquet"):
        path = os.path.join(data_folder, file)
        print(f"\n📄 --- {file} ---")

        # Läs bara de första 100 raderna för översikt
        df = pd.read_parquet(path)
        sample_df = df.head(100)

        # Grundinfo
        n_rows, n_cols = df.shape
        col_names = df.columns.tolist()

        print(f"   Rader: {n_rows:,} | Kolumner: {n_cols}")
        print(f"   Kolumner (max 15): {col_names[:15]}")
        print("   Exempelrader:")
        print(sample_df.head(3))

        # Lägg till i katalog-listan (en rad per kolumn)
        for col in col_names:
            rows.append({
                "fil": file,
                "antal_rader": n_rows,
                "antal_kolumner": n_cols,
                "kolumn": col
            })

# Gör en DataFrame och exportera till CSV
catalog_df = pd.DataFrame(rows)
catalog_df.to_csv(output_csv, index=False)
print(f"\n✅ Datakatalog skapad och sparad till {output_csv}")
