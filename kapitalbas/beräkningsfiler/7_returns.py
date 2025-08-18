import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path("ny_kapitalbas") / "datafiler"
PROC_DIR = BASE_DIR / "mellandata"
PROC_DIR.mkdir(parents=True, exist_ok=True)

input_file = PROC_DIR / "capbase_b_sample.parquet"
df = pd.read_parquet(input_file)

interest = 0.0453
df['ekdep2'] = df['ekdep'] / 2

# Räkna per komponent
for t in range(229, 237):
    age = df[f'age_component_{t}'].copy()
    ret_age = age + np.where((age % 2 == 1), np.where(age > 0, 1, -1), 0)
    ret_age = ret_age / 2 - 1
    df[f'age_return_{t}'] = ret_age

    cap_ord = ((df['ekdep2'] - ret_age) / df['ekdep2']) * df[f'nuav_ord_{t}']
    cap_ord = np.where(ret_age < 0, 0, cap_ord)
    df[f'return_ord_{t}'] = interest * cap_ord / 2

    cap_tail = (1 / (ret_age + 1)) * df[f'nuav_tail_{t}']
    df[f'return_tail_{t}'] = interest * cap_tail / 2

# Summera per nät×kategori och skala/avrunda i tusental – som i Stata
grp = df.groupby(['cat_encode','id_network'], as_index=False)
ret_sums = grp.agg({f'return_ord_{t}':'sum' for t in range(229,237)} |
                   {f'return_tail_{t}':'sum' for t in range(229,237)})

for t in range(229, 237):
    ret_sums[f'return_ord_{t}']  = (ret_sums[f'return_ord_{t}']  / 1000).round()
    ret_sums[f'return_tail_{t}'] = (ret_sums[f'return_tail_{t}'] / 1000).round()

# Endast aggregerade returns + nycklar (inga strängkolumner) ⇒ inga encoding-problem
ret_sums.to_parquet(PROC_DIR / "returns_compress_sample.parquet", index=False)
print("Saved returns_compress_sample.parquet:", ret_sums.shape)
