# Python code to process parquet data and create capbase_b with calculated variables
import pandas as pd
import numpy as np
from pathlib import Path

def process_capbase_data(input_file, output_file):
    """
    Process capbase_a.parquet to create capbase_b.parquet with calculated variables
    for time periods 229-236, sorted by id_component.
    
    Parameters:
    -----------
    input_file : str or Path
        Path to the input parquet file (capbase_a.parquet)
    output_file : str or Path
        Path to the output parquet file (capbase_b.parquet)
    """
    # Load the parquet file
    print(f"Loading data from {input_file}...")
    df = pd.read_parquet(input_file)
    print(f"Data loaded successfully: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Process each time period from 229 to 236
    for time in range(229, 237):
        df = process_time_period(df, time)
    
    # Sort the dataframe by id_component to match the test file
    df = df.sort_values('id_component')
    
    # Save the result to parquet and excel files
    output_path = Path(output_file)
    
    print(f"Saving data to {output_file}...")
    df.to_parquet(output_file)
    
    # Also save as Excel
    excel_file = output_path.with_suffix('.xlsx')
    print(f"Saving data to {excel_file}...")
    df.to_excel(excel_file, index=False)
    
    print(f"Data saved successfully to {output_file} and {excel_file}")
    
    return df

def process_time_period(df, time):
    """
    Process a single time period, calculating all required variables.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe to process
    time : int
        The time period to process (e.g., 229)
        
    Returns:
    --------
    pandas.DataFrame
        The processed dataframe with new columns for the time period
    """
    print(f"Processing time period {time}...")
    
    # Collect all new columns in a dictionary for efficient addition
    new_cols = {}
    
    # Age on components
    new_cols[f'age_component_{time}'] = time - df['time_from']
    new_cols[f'age_component_{time}_invest'] = np.where(df['capbase_existing'] == 0, 
                                                 time - df['time_invest'], 
                                                 np.nan)
    
    # Initial capital base ordinary
    new_cols[f'base_ord_{time}'] = 0
    mask = (new_cols[f'age_component_{time}'] <= df['ekdep']) & (new_cols[f'age_component_{time}'] > 0) & (df['capbase_existing'] == 1)
    base_ord = new_cols[f'base_ord_{time}'].copy()
    base_ord[mask] = 1
    new_cols[f'base_ord_{time}'] = base_ord
    
    # Investments and retirements ordinary
    mask = (new_cols[f'age_component_{time}'] <= df['ekdep']) & (new_cols[f'age_component_{time}_invest'] > 0) & (df['capbase_existing'] == 0)
    base_ord = new_cols[f'base_ord_{time}'].copy()
    base_ord[mask] = 1
    new_cols[f'base_ord_{time}'] = base_ord
    
    mask = (new_cols[f'age_component_{time}'] > df['ekdep']) & (df['capbase_existing'] == 0)
    base_ord = new_cols[f'base_ord_{time}'].copy()
    base_ord[mask] = 0
    new_cols[f'base_ord_{time}'] = base_ord
    
    # Calculate nuav_ord - FIX: Explicit float64 conversion before assignment
    nuav_ord = np.zeros(len(df), dtype='float64')
    mask = new_cols[f'base_ord_{time}'] == 1
    nuav_ord[mask] = (df['nuav_2022'] * new_cols[f'base_ord_{time}'])[mask]
    new_cols[f'nuav_ord_{time}'] = nuav_ord
    
    # Initial capital base tail
    new_cols[f'base_tail_{time}'] = 0
    mask = (new_cols[f'age_component_{time}'] <= df['maxdep']) & (new_cols[f'age_component_{time}'] > df['ekdep']) & (df['capbase_existing'] == 1)
    base_tail = new_cols[f'base_tail_{time}'].copy()
    base_tail[mask] = 1
    new_cols[f'base_tail_{time}'] = base_tail
    
    # Investments and retirements tail
    mask = (new_cols[f'age_component_{time}'] <= df['maxdep']) & (new_cols[f'age_component_{time}'] > df['ekdep']) & (df['time_invest'] < time) & (~df['invest'].isna())
    base_tail = new_cols[f'base_tail_{time}'].copy()
    base_tail[mask] = 1
    new_cols[f'base_tail_{time}'] = base_tail
    
    # Calculate nuav_tail
    new_cols[f'nuav_tail_{time}'] = df['nuav_2022'] * new_cols[f'base_tail_{time}']
    
    # Add all new columns at once - FIX: More efficient than repeated insert
    df = pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
    
    # Summarize - ordinary capital base
    sum_nuav_ord = df.groupby(['cat_encode', 'id_network'])[f'nuav_ord_{time}'].sum().reset_index(name=f'sum_nuav_ord_{time}')
    df = df.merge(sum_nuav_ord, on=['cat_encode', 'id_network'], how='left')
    
    # Convert to thousands - NO ROUNDING
    df[f'sum_nuav_ord_{time}'] = df[f'sum_nuav_ord_{time}'] / 1000
    
    # Summarize - tail
    sum_nuav_tail = df.groupby(['cat_encode', 'id_network'])[f'nuav_tail_{time}'].sum().reset_index(name=f'sum_nuav_tail_{time}')
    df = df.merge(sum_nuav_tail, on=['cat_encode', 'id_network'], how='left')
    
    # Convert to thousands - NO ROUNDING
    df[f'sum_nuav_tail_{time}'] = df[f'sum_nuav_tail_{time}'] / 1000
    
    return df

if __name__ == "__main__":
    # Setup paths
    BASE_DIR = Path("kapitalkostnad") / "data"
    PROC_DIR = BASE_DIR / "mellandata"
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    
    input_file = PROC_DIR / "capbase_a.parquet"
    output_file = PROC_DIR / "capbase_b.parquet"
    process_capbase_data(input_file, output_file)