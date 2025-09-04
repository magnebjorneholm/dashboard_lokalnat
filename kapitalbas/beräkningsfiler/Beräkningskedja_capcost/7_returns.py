import pandas as pd
import numpy as np
from pathlib import Path
from pandas.api.types import is_categorical_dtype


def compute_returns(input_file, output_file):
    # Load the original capbase file
    df = pd.read_parquet(input_file)
    print(f"Loaded {input_file}: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Define interest rate
    interest = 0.0453
    
    # Calculate ekdep2 and maxdep2
    df['ekdep2'] = df['ekdep'] / 2
    df['maxdep2'] = df['maxdep'] / 2
    
    # Process for each time period (229 to 236 inclusive)
    for time in range(229, 237):
        # Calculate age_return
        age_col = f'age_component_{time}'
        ret_col = f'age_return_{time}'
        df[ret_col] = df[age_col].copy()
        # For rows where the value is odd, adjust by 1 in the proper direction
        mask = (df[ret_col] % 2 == 1)
        df.loc[mask, ret_col] += df.loc[mask, ret_col].apply(lambda x: 1 if x > 0 else -1)
        df[ret_col] = df[ret_col] / 2
        df[ret_col] = df[ret_col] - 1

        # Ordinary returns calculations
        cap_ord = f'capbase_left_ord_{time}'
        df[cap_ord] = ((df['ekdep2'] - df[ret_col]) / df['ekdep2']) * df[f'nuav_ord_{time}']
        df.loc[df[ret_col] < 0, cap_ord] = 0
        ret_ord = f'return_ord_{time}'
        df[ret_ord] = interest * df[cap_ord] / 2

        # Tail returns calculations
        cap_tail = f'capbase_left_tail_{time}'
        df[cap_tail] = (1 / (df[ret_col] + 1)) * df[f'nuav_tail_{time}']
        ret_tail = f'return_tail_{time}'
        df[ret_tail] = interest * df[cap_tail] / 2

    # Identify all the return columns
    return_columns = []
    for time in range(229, 237):
        for t in ['ord', 'tail']:
            col = f'return_{t}_{time}'
            if col in df.columns:
                return_columns.append(col)

    agg_dict = {col: 'sum' for col in return_columns}

    # Group the dataframe
    if is_categorical_dtype(df['cat_encode']):
        df['cat_encode'] = df['cat_encode'].cat.remove_unused_categories()
    if is_categorical_dtype(df['id_network']):
        df['id_network'] = df['id_network'].cat.remove_unused_categories()

    grouped = (
        df.groupby(['cat_encode', 'id_network'], as_index=False, observed=True, sort=False)
        .agg(agg_dict)
    )

    # Divide aggregated returns by 1000 - NO ROUNDING
    for col in return_columns:
        grouped[col] = grouped[col] / 1000

    # Keep only necessary columns and sort
    keep_cols = ['id_network', 'cat_encode'] + return_columns
    returns_compress = grouped[keep_cols].sort_values(['id_network', 'cat_encode'])

    # Save to parquet
    output_path = Path(output_file)
    returns_compress.to_parquet(output_file)
    
    # Also save as Excel
    excel_file = output_path.with_suffix('.xlsx')
    returns_compress.to_excel(excel_file, index=False)
    
    print(f"Saved {output_file}: {returns_compress.shape[0]} rows, {len(returns_compress.columns)} columns")
    print(f"Saved {excel_file}: {returns_compress.shape[0]} rows, {len(returns_compress.columns)} columns")
    
    return returns_compress

if __name__ == "__main__":
    # Setup paths
    BASE_DIR = Path("kapitalbas") / "datafiler"
    PROC_DIR = BASE_DIR / "mellandata"
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    
    input_file = PROC_DIR / "capbase_b_sample_1_and_3035.parquet"
    output_file = PROC_DIR / "returns_compress_sample_1_and_3035.parquet"
    compute_returns(input_file, output_file)