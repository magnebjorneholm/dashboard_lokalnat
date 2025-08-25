import pandas as pd
import numpy as np
import re
import pyreadstat
from pathlib import Path

BASE_DIR = Path("ny_kapitalbas") / "datafiler"
PROC_DIR = BASE_DIR / "mellandata"
PROC_DIR.mkdir(parents=True, exist_ok=True)

def compute_depreciation(input_file, output_file):
    df = pd.read_parquet(input_file)

    # Beräkna per komponent
    for t in range(229, 237):
        df[f'dep_ord_{t}'] = df[f'nuav_ord_{t}'] / df['ekdep']

        age = pd.to_numeric(df[f'age_component_{t}'], errors='coerce')
        adj = np.where((age % 2 == 1), np.where(age > 0, 1, -1), 0)
        df[f'age_reg_{t}'] = age + adj

        denom = df[f'age_reg_{t}'].astype(float)
        numer = pd.to_numeric(df[f'nuav_tail_{t}'], errors='coerce')
        dep_tail = np.divide(numer, denom, out=np.zeros_like(denom, dtype=float), where=(denom != 0))
        df[f'dep_tail_{t}'] = dep_tail

    # Summera per nät×kategori och skala/avrunda i tusental – som i Stata
    aggs = {}
    for t in range(229, 237):
        aggs[f'dep_ord_{t}']  = ('dep_ord_{t}',  'sum')
        aggs[f'dep_tail_{t}'] = ('dep_tail_{t}', 'sum')
        aggs[f'nuav_ord_{t}'] = (f'nuav_ord_{t}','sum')
        aggs[f'nuav_tail_{t}']= (f'nuav_tail_{t}','sum')

    # Bygg aggframe
    grp = df.groupby(['cat_encode','id_network'], as_index=False)
    sums = grp.agg({k:v[1] for k,v in aggs.items()})
    # Skala/avrunda
    for t in range(229, 237):
        for stub in ['dep_ord','dep_tail','nuav_ord','nuav_tail']:
            col = f'{stub}_{t}'
            sums[col] = (sums[col] / 1000).round()

    # Behåll också första förekomsten av ålderskolumner (för reshape i steg 8)
    age_cols = [c for c in df.columns if re.match(r'^age_component_\d+(_invest)?$', c)]
    age_reg_cols = [f'age_reg_{t}' for t in range(229, 237)]
    first = grp.first()[['cat_encode','id_network'] + age_cols + age_reg_cols]

    # Komprimerad tabell (exakt en rad per nät×kategori)
    out = pd.merge(first, sums, on=['cat_encode','id_network'], how='inner')

    # Spara med pyreadstat för robust encoding
    out.to_parquet(output_file, index=False)
    print(f"Saved {output_file}: {out.shape}")

if __name__ == "__main__":
    input_file = PROC_DIR / "capbase_b_test.parquet"
    output_file = PROC_DIR / "depreciation_compress_test.parquet"
    compute_depreciation(str(input_file), str(output_file))
