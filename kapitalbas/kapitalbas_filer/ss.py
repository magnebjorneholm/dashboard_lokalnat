import pandas as pd

def analysera_sample_vs_full(final_df, sample_df):
    # Nätverk att analysera
    nat_ids = [7, 160, 3035]
    results = {}

    for nat_id in nat_ids:
        print("="*40)
        print(f"Nät {nat_id}")
        print("="*40)

        # Filtrera till aktuellt nät och släng nuav==0
        sample_n = sample_df[(sample_df['id_network'] == nat_id) & (sample_df['nuav'] != 0)].copy()
        full_n = final_df[(final_df['id_network'] == nat_id) & (final_df['nuav'] != 0)].copy()

        # Säker konvertering av datum
        sample_n["time_to_parsed"] = pd.to_datetime(sample_n["time_to"], errors='coerce')
        full_n["time_to_parsed"] = pd.to_datetime(full_n["time_to"], errors='coerce')

        # Flaggor
        sample_n["flag_neg_nuav"] = sample_n["nuav"] < 0
        sample_n["flag_maxdep"] = sample_n["maxdep"] == 1
        sample_n["flag_old"] = sample_n["time_to_parsed"] < pd.Timestamp("2024-01-01")
        sample_n["flag_inaktiv"] = sample_n[["flag_neg_nuav", "flag_maxdep", "flag_old"]].any(axis=1)

        # Filtrera
        sample_neg = sample_n[sample_n["flag_inaktiv"]].copy()
        relevant_cats = sample_neg["cat"].dropna().unique()

        # Samma sak i full_df
        full_n["flag_neg_nuav"] = full_n["nuav"] < 0
        full_n["flag_maxdep"] = full_n["maxdep"] == 1
        full_n["flag_old"] = full_n["time_to_parsed"] < pd.Timestamp("2024-01-01")
        full_n["flag_inaktiv"] = full_n[["flag_neg_nuav", "flag_maxdep", "flag_old"]].any(axis=1)

        full_neg = full_n[(full_n["flag_inaktiv"]) & (full_n["cat"].isin(relevant_cats))].copy()
        balancing = full_n[(full_n["cat"].isin(relevant_cats)) & (full_n["nuav"] > 0)].copy()

        # Sammanställning
        result = {
            "sample_count_inaktiv": len(sample_neg),
            "sample_sum_nuav": sample_neg["nuav"].sum(),
            "full_count_inaktiv": len(full_neg),
            "full_sum_nuav": full_neg["nuav"].sum(),
            "balancing_summary": balancing.groupby("cat")["nuav"].agg(["count", "sum"]).reset_index()
        }
        results[nat_id] = result

        # === Utskrifter ===
        print(f" Inaktiva i sample: {len(sample_neg)} st, total nuav: {sample_neg['nuav'].sum():,.0f} SEK")
        print(f" Inaktiva i full:   {len(full_neg)} st, total nuav: {full_neg['nuav'].sum():,.0f} SEK")
        print("\n Balansposter i full_df (positivt nuav i samma kategorier):")
        print(result["balancing_summary"].sort_values("sum", ascending=False).to_string(index=False))

        print("\n Exempel från sample med negativt nuav eller maxdep:")
        print(sample_neg[["id_component", "cat", "nuav", "maxdep", "time_to"]].head(10).to_string(index=False))
        print("\n")

    return results

# === LADDA FILER OCH KÖR ===
final_df = pd.read_parquet("kapitalbas_filer/final_capbase.parquet")
sample_df = pd.read_parquet("kapitalbas_filer/final_capbase_sample.parquet")
resultat = analysera_sample_vs_full(final_df, sample_df)
