import pandas as pd
import numpy as np
from pathlib import Path

def compile_capcost(depreciation_file, returns_file, output_file):
    # Load raw data - preserving categorical variables
    df_depr = pd.read_parquet(depreciation_file)
    df_ret = pd.read_parquet(returns_file)
    
    print(f"Loaded depreciation data: {df_depr.shape[0]} rows, {df_depr.shape[1]} columns")
    print(f"Loaded returns data: {df_ret.shape[0]} rows, {df_ret.shape[1]} columns")

    # Merge datasets
    df = pd.merge(df_depr, df_ret, on=['cat_encode', 'id_network'], how='inner')
    print(f"Merged data: {df.shape[0]} rows, {df.shape[1]} columns")

    # Rename the invest columns to match pattern (if any exist)
    for col in df.columns:
        if 'invest' in col:
            year = col.split('_')[-1]
            new_name = 'age_component_invest_' + year
            df = df.rename(columns={col: new_name})

    # Get base variables for reshaping
    base_vars = ['nuav_ord', 'dep_ord', 'nuav_tail', 'dep_tail', 
                 'age_component', 'age_component_invest', 'age_reg', 
                 'return_ord', 'return_tail']

    # Reshape wide to long
    df_long = pd.wide_to_long(df, 
                             stubnames=base_vars,
                             i=['id_network', 'cat_encode'],
                             j='time',
                             sep='_',
                             suffix='\d+').reset_index()

    # Calculate variables - NO ROUNDING, preserve float precision
    df_long['capcost_sum'] = (df_long['dep_ord'].astype('float64') + 
                             df_long['dep_tail'].astype('float64') + 
                             df_long['return_ord'].astype('float64') + 
                             df_long['return_tail'].astype('float64'))
    df_long['capcost_network'] = df_long.groupby('id_network')['capcost_sum'].transform('sum').astype('float64')

    # Convert time to int16
    df_long['time'] = df_long['time'].astype('int16')

    # Sort the data
    df_long = df_long.sort_values(['id_network', 'cat_encode', 'time'])

    # Order columns
    final_cols = ['age_component', 'age_component_invest', 'age_reg', 'capcost_network', 'capcost_sum',
                  'cat_encode', 'dep_ord', 'dep_tail', 'id_network', 'nuav_ord', 'nuav_tail',
                  'return_ord', 'return_tail', 'time']
    df_final = df_long[final_cols]

    # Save to parquet
    output_path = Path(output_file)
    df_final.to_parquet(output_file)
    
    # Also save as Excel
    excel_file = output_path.with_suffix('.xlsx')
    df_final.to_excel(excel_file, index=False)
    
    print(f"Saved {output_file}: {df_final.shape[0]} rows, {df_final.shape[1]} columns")
    print(f"Saved {excel_file}: {df_final.shape[0]} rows, {df_final.shape[1]} columns")
    
    return df_final

if __name__ == "__main__":
    # Setup paths
    BASE_DIR = Path("kapitalbas") / "datafiler"
    PROC_DIR = BASE_DIR / "mellandata"
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    
    depreciation_file = PROC_DIR / "depreciation_compress_sample_1_and_3035.parquet"
    returns_file = PROC_DIR / "returns_compress_sample_1_and_3035.parquet"
    output_file = PROC_DIR / "capcost_a_sample_1_and_3035.parquet"
    
    compile_capcost(depreciation_file, returns_file, output_file)