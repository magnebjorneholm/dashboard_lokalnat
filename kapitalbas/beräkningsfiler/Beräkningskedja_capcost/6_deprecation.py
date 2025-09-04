import pandas as pd
import numpy as np
from pathlib import Path

def compute_depreciation(input_file, output_file):
    # Load the input data
    df = pd.read_parquet(input_file)
    print("Loaded " + str(input_file) + ": " + str(df.shape[0]) + " rows, " + str(len(df.columns)) + " columns")
    
    result_dfs = []
    
    # Process all time periods
    for t in range(229, 237):
        # 1. Compute dep_ord
        nuav_col = f'nuav_ord_{t}'
        comp_dep = df[nuav_col] / df['ekdep']
        df[f'comp_dep_{t}'] = comp_dep
        
        # Aggregate dep_ord by group
        aggr_ord = df.groupby(['cat_encode', 'id_network'])[f'comp_dep_{t}'].sum().reset_index()
        # NO ROUNDING - just convert to thousands
        aggr_ord[f'dep_ord_{t}'] = aggr_ord[f'comp_dep_{t}'] / 1000
        
        # 2. Compute dep_tail
        age_comp = f'age_component_{t}'
        age_reg = f'age_reg_{t}'
        
        # Convert age_component to numeric
        df[age_comp] = pd.to_numeric(df[age_comp], errors='coerce')
        
        # Compute age_reg
        adjustment = np.where((df[age_comp] % 2 == 1), 
                            np.where(df[age_comp] > 0, 1, -1), 
                            0)
        df[age_reg] = df[age_comp] + adjustment
        
        # Ensure age_reg is numeric
        df[age_reg] = pd.to_numeric(df[age_reg], errors='coerce')
        
        # Compute comp_dep_tail using safe division
        tail_col = f'nuav_tail_{t}'
        df[tail_col] = pd.to_numeric(df[tail_col], errors='coerce')
        denominator = df[age_reg].to_numpy().astype(float)
        numerator = df[tail_col].to_numpy().astype(float)
        comp_dep_tail = np.divide(numerator, denominator, 
                                out=np.zeros_like(denominator, dtype=float), 
                                where=(denominator != 0))
        df[f'comp_dep_tail_{t}'] = comp_dep_tail
        
        # Aggregate dep_tail by group
        aggr_tail = df.groupby(['cat_encode', 'id_network'])[f'comp_dep_tail_{t}'].sum().reset_index()
        # NO ROUNDING - just convert to thousands
        aggr_tail[f'dep_tail_{t}'] = aggr_tail[f'comp_dep_tail_{t}'] / 1000
        
        # Merge ord and tail results
        aggr = pd.merge(
            aggr_ord[['id_network', 'cat_encode', f'dep_ord_{t}']], 
            aggr_tail[['id_network', 'cat_encode', f'dep_tail_{t}']], 
            on=['id_network', 'cat_encode']
        )
        
        result_dfs.append(aggr)
    
    # Merge all time periods
    merged = result_dfs[0]
    for agg_df in result_dfs[1:]:
        merged = pd.merge(merged, agg_df, on=['id_network', 'cat_encode'], how='outer')
    
    # Sort and save
    merged = merged.sort_values(['id_network', 'cat_encode']).reset_index(drop=True)
    
    # Save to parquet
    output_path = Path(output_file)
    merged.to_parquet(output_file)
    
    # Also save as Excel
    excel_file = output_path.with_suffix('.xlsx')
    merged.to_excel(excel_file, index=False)
    
    print("Saved " + str(output_file) + ": " + str(merged.shape[0]) + " rows, " + str(len(merged.columns)) + " columns")
    print("Saved " + str(excel_file) + ": " + str(merged.shape[0]) + " rows, " + str(len(merged.columns)) + " columns")
    
    return merged

if __name__ == "__main__":
    # Setup paths
    BASE_DIR = Path("kapitalbas") / "datafiler"
    PROC_DIR = BASE_DIR / "mellandata"
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    
    input_file = PROC_DIR / "capbase_b_sample_1_and_3035.parquet"
    output_file = PROC_DIR / "depreciation_compress_sample_1_and_3035.parquet"
    compute_depreciation(str(input_file), str(output_file))