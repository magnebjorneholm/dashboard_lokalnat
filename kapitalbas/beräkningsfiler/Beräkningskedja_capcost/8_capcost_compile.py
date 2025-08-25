import pandas as pd
import numpy as np
from pathlib import Path

# ==============================
# Basmappar
# ==============================
BASE_DIR = Path("ny_kapitalbas") / "datafiler"
PROC_DIR = BASE_DIR / "mellandata"
FINAL_DIR = BASE_DIR / "slutdata"
PROC_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# Load datasets
# ==============================
df_depr = pd.read_parquet(PROC_DIR / "depreciation_compress_sample.parquet")
df_ret = pd.read_parquet(PROC_DIR / "returns_compress_sample.parquet")

# ==============================
# Merge with suffix handling
# ==============================
df = pd.merge(df_depr, df_ret, on=['cat_encode', 'id_network'], how='inner', suffixes=('', '_ret'))
df['cat_encode'] = df['cat_encode'] + 1


# Rensa dubbletter: om en kolumn finns i båda, fyll på från _ret om basen är NaN
for col in df.columns:
    if col.endswith('_ret'):
        base_col = col.replace('_ret', '')
        if base_col in df.columns:
            df[base_col] = df[base_col].fillna(df[col])
            df.drop(columns=[col], inplace=True)

# ==============================
# Rename invest columns to match pattern
# ==============================
for col in df.columns:
    if 'invest' in col:
        year = col.split('_')[-1]
        new_name = 'age_component_invest_' + year
        df.rename(columns={col: new_name}, inplace=True)

# ==============================
# Get base variables for reshaping
# ==============================
base_vars = ['nuav_ord', 'dep_ord', 'nuav_tail', 'dep_tail', 
             'age_component', 'age_component_invest', 'age_reg', 
             'return_ord', 'return_tail']

# ==============================
# Reshape wide to long
# ==============================
df_long = pd.wide_to_long(df, 
                         stubnames=base_vars,
                         i=['id_network', 'cat_encode'],
                         j='time',
                         sep='_',
                         suffix='\d+').reset_index()

# ==============================
# Calculate variables
# ==============================
df_long['capcost_sum'] = (
    df_long['dep_ord'].astype('float32') + 
    df_long['dep_tail'].astype('float32') + 
    df_long['return_ord'].astype('float32') + 
    df_long['return_tail'].astype('float32')
)

df_long['capcost_network'] = df_long.groupby('id_network')['capcost_sum'].transform('sum').astype('float32')

# ==============================
# Convert time to int16
# ==============================
df_long['time'] = df_long['time'].astype('int16')

# ==============================
# Sort and select columns
# ==============================
df_long = df_long.sort_values(['id_network', 'cat_encode', 'time'])

final_cols = ['age_reg', 'capcost_network', 'capcost_sum',
              'cat_encode', 'dep_ord', 'dep_tail', 'id_network', 'nuav_ord', 'nuav_tail',
              'return_ord', 'return_tail', 'time']
df_final = df_long[final_cols]

# ==============================
# Save
# ==============================
output_file = FINAL_DIR / "capcost_a_sample.parquet"
df_final.to_parquet(output_file, index=False)
print(f"✅ Saved {output_file}: {df_final.shape[0]} rows, {df_final.shape[1]} columns")

excel_file = FINAL_DIR / "capcost_a_sample.xlsx"
df_final.to_excel(excel_file, index=False)

print(f"✅ Saved {output_file} and {excel_file}: {df_final.shape[0]} rows, {df_final.shape[1]} columns")
