# Python code to process Stata data and create capbase_b.parquet
import pandas as pd
import numpy as np
from pathlib import Path

# ==============================
# Basmappar
# ==============================
BASE_DIR = Path("ny_kapitalbas") / "datafiler"
RAW_DIR  = BASE_DIR / "rådata"
PROC_DIR = BASE_DIR / "mellandata"
PROC_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# Läs in rådata
# ==============================
capbase_a_path = RAW_DIR / "capbase_a_sample.parquet"

def process_capbase_data(input_file, output_file):
    """
    Process capbase_a.parquet to create capbase_b.parquet with calculated variables
    for time periods 229-236, sorted by id_component.
    """
    # Load the Stata file
    print(f"Loading data from {input_file}...")
    df = pd.read_parquet(input_file)
    print(f"Data loaded successfully: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Process each time period from 229 to 236
    for time in range(229, 237):
        df = process_time_period(df, time)
    
    # Sort the dataframe by id_component to match the test file
    df = df.sort_values('id_component')
    
    # Save the result to a Stata file
    print(f"Saving data to {output_file}...")
    df.to_parquet(output_file, index=False)
    print(f"Data saved successfully to {output_file}")
    
    return df

def process_time_period(df, time):
    """
    Process a single time period, calculating all required variables.
    """
    print(f"Processing time period {time}...")
    
    # Age on components
    df[f'age_component_{time}'] = time - df['time_from']
    df[f'age_component_{time}_invest'] = np.where(df['capbase_existing'] == 0, 
                                                 time - df['time_invest'], 
                                                 np.nan)
    
    # Initial capital base ordinary
    df[f'base_ord_{time}'] = 0
    mask = (df[f'age_component_{time}'] <= df['ekdep']) & (df[f'age_component_{time}'] > 0) & (df['capbase_existing'] == 1)
    df.loc[mask, f'base_ord_{time}'] = 1
    
    # Investments and retirements ordinary
    mask = (df[f'age_component_{time}'] <= df['ekdep']) & (df[f'age_component_{time}_invest'] > 0) & (df['capbase_existing'] == 0)
    df.loc[mask, f'base_ord_{time}'] = 1
    
    mask = (df[f'age_component_{time}'] > df['ekdep']) & (df['capbase_existing'] == 0)
    df.loc[mask, f'base_ord_{time}'] = 0
    
    # Calculate nuav_ord
    df[f'nuav_ord_{time}'] = 0
    df.loc[df[f'base_ord_{time}'] == 1, f'nuav_ord_{time}'] = df['nuav_2022'] * df[f'base_ord_{time}']
    
    # Initial capital base tail
    df[f'base_tail_{time}'] = 0
    mask = (df[f'age_component_{time}'] <= df['maxdep']) & (df[f'age_component_{time}'] > df['ekdep']) & (df['capbase_existing'] == 1)
    df.loc[mask, f'base_tail_{time}'] = 1
    
    # Investments and retirements tail
    mask = (df[f'age_component_{time}'] <= df['maxdep']) & (df[f'age_component_{time}'] > df['ekdep']) & (df['time_invest'] < time) & (~df['invest'].isna())
    df.loc[mask, f'base_tail_{time}'] = 1
    
    # Calculate nuav_tail
    df[f'nuav_tail_{time}'] = df['nuav_2022'] * df[f'base_tail_{time}']
    
    # Summarize - ordinary capital base
    # Group by cat_encode and id_network, then sum nuav_ord
    sum_nuav_ord = df.groupby(['cat_encode', 'id_network'])[f'nuav_ord_{time}'].sum().reset_index(name=f'sum_nuav_ord_{time}')
    
    # Merge the sums back to the original dataframe
    df = df.merge(sum_nuav_ord, on=['cat_encode', 'id_network'], how='left')
    
    # Convert to thousands and round
    df[f'sum_nuav_ord_{time}'] = df[f'sum_nuav_ord_{time}'] / 1000
    df[f'sum_nuav_ord_{time}'] = df[f'sum_nuav_ord_{time}'].round()
    
    # Summarize - tail
    # Group by cat_encode and id_network, then sum nuav_tail
    sum_nuav_tail = df.groupby(['cat_encode', 'id_network'])[f'nuav_tail_{time}'].sum().reset_index(name=f'sum_nuav_tail_{time}')
    
    # Merge the sums back to the original dataframe
    df = df.merge(sum_nuav_tail, on=['cat_encode', 'id_network'], how='left')
    
    # Convert to thousands and round
    df[f'sum_nuav_tail_{time}'] = df[f'sum_nuav_tail_{time}'] / 1000
    df[f'sum_nuav_tail_{time}'] = df[f'sum_nuav_tail_{time}'].round()
    
    return df

if __name__ == "__main__":
    input_file = capbase_a_path
    output_file = PROC_DIR / "capbase_b_sample.parquet"
    process_capbase_data(input_file, output_file)
