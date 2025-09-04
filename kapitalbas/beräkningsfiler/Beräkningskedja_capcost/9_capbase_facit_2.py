import pandas as pd
from pathlib import Path

def create_verification_diff(depreciation_file, returns_file, facit_file, output_file):
    """
    Create verification file with diff variables comparing calculated values to facit.
    """
    print("Loading files...")
    
    # Load all input files
    depreciation_df = pd.read_parquet(depreciation_file)
    returns_df = pd.read_parquet(returns_file)
    facit_df = pd.read_parquet(facit_file)
    
    print(f"Loaded {len(depreciation_df)} rows from depreciation file")
    print(f"Loaded {len(returns_df)} rows from returns file")
    print(f"Loaded {len(facit_df)} rows from facit file")
    
    # Merge all calculated data files
    print("Merging calculated data...")
    merged_calc = depreciation_df.merge(
        returns_df, 
        on=['id_network', 'cat_encode'], 
        how='outer'
    )
    
    print(f"Merged calculated data: {len(merged_calc)} rows")
    
    # Merge with facit data
    print("Merging with facit...")
    full_df = merged_calc.merge(
        facit_df, 
        on=['id_network', 'cat_encode'], 
        how='left'  # Keep all calculated rows, even if not in facit
    )
    
    print(f"Final merged data: {len(full_df)} rows")
    
    # Create diff variables
    print("Creating diff variables...")
    
    # Time codes to process
    time_codes = ['229', '230', '231', '232', '233', '234', '235', '236']
    
    # Direct comparisons for each time code
    for time_code in time_codes:
        # Return ord and tail
        full_df[f'diff_return_ord_{time_code}'] = (
            full_df[f'return_ord_{time_code}'] - full_df[f'return_ord_{time_code}_f']
        )
        full_df[f'diff_return_tail_{time_code}'] = (
            full_df[f'return_tail_{time_code}'] - full_df[f'return_tail_{time_code}_f']
        )
        
        # Depreciation ord and tail
        full_df[f'diff_dep_ord_{time_code}'] = (
            full_df[f'dep_ord_{time_code}'] - full_df[f'dep_ord_{time_code}_f']
        )
        full_df[f'diff_dep_tail_{time_code}'] = (
            full_df[f'dep_tail_{time_code}'] - full_df[f'dep_tail_{time_code}_f']
        )

    # Select columns for output (only key columns and diff variables)
    diff_cols = [col for col in full_df.columns if col.startswith('diff_')]
    key_cols = ['id_network', 'cat_encode']
    
    # Select final columns
    final_cols = key_cols + diff_cols
    
    output_df = full_df[final_cols]
    
    # Save to Excel
    print(f"Saving to Excel: {output_file}")
    output_df.to_excel(output_file, index=False)
    
    # Print summary
    print("\nVerification Summary:")
    print(f"Total rows processed: {len(output_df)}")
    print(f"Total diff variables created: {len(diff_cols)}")
    
    # Count non-zero diffs (excluding NAs)
    for diff_col in diff_cols:
        non_zero_count = (output_df[diff_col] != 0).sum()
        na_count = output_df[diff_col].isna().sum()
        print(f"{diff_col}: {non_zero_count} non-zero diffs, {na_count} NAs")
    
    print(f"\nOutput saved to: {output_file}")


if __name__ == "__main__":
    # Setup paths
    BASE_DIR = Path("kapitalbas") / "datafiler"
    PROC_DIR = BASE_DIR / "mellandata"
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    
    # Input files
    depreciation_file = PROC_DIR / "depreciation_compress_sample_1_and_3035.parquet"
    returns_file = PROC_DIR / "returns_compress_sample_1_and_3035.parquet"
    facit_file = PROC_DIR / "facit_id_1_3035.parquet"
    
    # Output file
    output_file = PROC_DIR / "verification_diff_sample_1_and_3035.xlsx"
    
    create_verification_diff(depreciation_file, returns_file, facit_file, output_file)