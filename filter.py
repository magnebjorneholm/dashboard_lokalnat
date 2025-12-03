from data_loaders.baseline_data import load_baseline_data
baseline = load_baseline_data()
print("SDF IR kolumner:", baseline.sdf_ir.columns.tolist())
print("SDF Påverkbara kolumner:", baseline.sdf_paverkbara.columns.tolist())