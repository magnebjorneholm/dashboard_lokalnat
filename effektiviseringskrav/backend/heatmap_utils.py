import geopandas as gpd
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Optional, Set

# Konstanter
REQUIRED_COLUMNS = ["FöretagNa", "Orgnr", "Redovisnin", "Länktillp"]
EXPECTED_CRS = 3006  # SWEREF99 TM
SHAPEFILE_PATH = "effektiviseringskrav/data/Samtliga nätföretags del- och verksamhetsområden.shp"
RECONCILIATION_PATH = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"


def load_valid_reid_registry() -> Tuple[Set[str], Set[str], pd.DataFrame]:
    """
    Laddar den auktoritativa listan över giltiga REId från reconciliation-filen.
    
    Returns:
        Tuple med:
        - Set av alla giltiga REId (159 st)
        - Set av REId som förväntas ha DEA-data (exkl. RER med motsvarande REL)
        - Full DataFrame med reconciliation-data
    """
    try:
        df_recon = pd.read_csv(RECONCILIATION_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Reconciliation-fil hittades inte: {RECONCILIATION_PATH}\n"
            "Denna fil är obligatorisk och definierar vilka REId som är giltiga."
        )
    
    # Alla giltiga REId
    valid_reid = set(df_recon['id_network_string'].dropna().unique())
    
    # REId som förväntas ha DEA-data (in_data_modeller=True)
    expected_dea_mask = (df_recon['in_data_modeller'] == True) | (df_recon['in_data_modeller'] == "True")
    expected_dea_reid = set(df_recon.loc[expected_dea_mask, 'id_network_string'].dropna().unique())
    
    # VIKTIGT: Ta bort RER som har motsvarande REL för samma DMU
    # Dessa RER ska INTE förväntas ha DEA-data eftersom DEA använder REL-IDt
    rer_with_dmu = df_recon[
        (df_recon['id_network_string'].str.startswith('RER')) & 
        (expected_dea_mask) &
        (df_recon['DMU'].notna())
    ]
    
    for _, rer_row in rer_with_dmu.iterrows():
        dmu = rer_row['DMU']
        # Kolla om samma DMU har en REL
        has_rel = df_recon[
            (df_recon['DMU'] == dmu) & 
            (df_recon['id_network_string'].str.startswith('REL'))
        ].shape[0] > 0
        
        if has_rel:
            # Ta bort denna RER från expected_dea_reid
            expected_dea_reid.discard(rer_row['id_network_string'])
    
    return valid_reid, expected_dea_reid, df_recon


@st.cache_data
def load_shapes_for_dea() -> Tuple[gpd.GeoDataFrame, Dict]:
    """
    Laddar shapefile och filtrerar till ENDAST giltiga REId enligt reconciliation-filen.
    
    KRITISKT: Använder reconciliation_id_network_firm_dmu.csv som auktoritativ källa
    för vilka REId som är giltiga (159 st totalt).
    
    Returns:
        Tuple[GeoDataFrame med endast giltiga REId, metadata]
    """
    # Ladda auktoritativ lista över giltiga REId
    valid_reid, expected_dea_reid, df_recon = load_valid_reid_registry()
    
    try:
        gdf = gpd.read_file(SHAPEFILE_PATH)
    except Exception as e:
        raise FileNotFoundError(f"Kunde inte läsa shapefile: {SHAPEFILE_PATH}. Fel: {e}")
    
    # Validera kolumner
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in gdf.columns]
    if missing_cols:
        raise ValueError(
            f"Shapefile saknar obligatoriska kolumner: {missing_cols}\n"
            f"Tillgängliga kolumner: {list(gdf.columns)}"
        )
    
    # Validera och fixa CRS
    if gdf.crs is None:
        raise ValueError("Shapefile saknar CRS-information (.prj-fil saknas?)")
    
    if gdf.crs.to_epsg() != EXPECTED_CRS:
        st.warning(f"Konverterar CRS från {gdf.crs} till EPSG:{EXPECTED_CRS}")
        gdf = gdf.to_crs(EXPECTED_CRS)
    
    # Hantera ogiltiga geometrier
    invalid_mask = ~gdf.geometry.is_valid
    n_invalid = invalid_mask.sum()
    if n_invalid > 0:
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)
    
    # Spara originalantal för metadata
    n_original = len(gdf)
    
    # Dela upp rader med flera REId (explosion)
    gdf["REId_list"] = gdf["Redovisnin"].astype(str).str.split(",")
    gdf = gdf.explode("REId_list").reset_index(drop=True)
    gdf["REId"] = gdf["REId_list"].str.strip()
    gdf = gdf.drop(columns=["REId_list", "Redovisnin"])
    
    n_after_explode = len(gdf)
    
    # Analysera FÖRE filtrering
    shapefile_reid = set(gdf["REId"].unique())
    
    # KRITISK FILTRERING: Behåll ENDAST REId från reconciliation-filen
    gdf_filtered = gdf[gdf["REId"].isin(valid_reid)].copy()
    
    n_filtered_out = n_after_explode - len(gdf_filtered)
    excluded_reid = shapefile_reid - valid_reid
    
    # Skapa stabilt geometri-ID
    gdf_filtered["geom_id"] = gdf_filtered["geometry"].apply(lambda g: g.wkb_hex)
    
    # Analysera vad som exkluderades
    excluded_by_type = {}
    for reid in excluded_reid:
        net_type = reid[:3] if len(reid) >= 3 else "Okänd"
        excluded_by_type[net_type] = excluded_by_type.get(net_type, 0) + 1
    
    # Analysera vad som behölls
    kept_by_type = {}
    for reid in gdf_filtered["REId"].unique():
        net_type = reid[:3]
        kept_by_type[net_type] = kept_by_type.get(net_type, 0) + 1
    
    # Metadata för transparent rapportering
    metadata = {
        "shapefile_path": SHAPEFILE_PATH,
        "reconciliation_path": RECONCILIATION_PATH,
        "crs": str(gdf_filtered.crs),
        "n_polygons_original": n_original,
        "n_rows_after_explode": n_after_explode,
        "n_filtered_out": n_filtered_out,
        "n_valid_remaining": len(gdf_filtered),
        "n_unique_valid_reid": gdf_filtered["REId"].nunique(),
        "n_unique_geoms": gdf_filtered["geom_id"].nunique(),
        "n_invalid_fixed": n_invalid,
        "valid_reid_total": len(valid_reid),
        "expected_dea_reid_total": len(expected_dea_reid),
        "excluded_reid": list(excluded_reid),
        "excluded_by_type": excluded_by_type,
        "kept_by_type": kept_by_type,
    }
    
    return gdf_filtered, metadata


def merge_dea_with_geodata(
    gdf_shapes: gpd.GeoDataFrame, 
    df_dea: pd.DataFrame,
    value_column: str = "Effektivitet"
) -> Tuple[gpd.GeoDataFrame, Dict]:
    """
    Mergar DEA-resultat med geodata och rapporterar matchningskvalitet.
    
    Använder in_data_modeller-flaggan från reconciliation för intelligent validering:
    - REId med in_data_modeller=True FÖRVÄNTAS ha DEA-data
    - REId med in_data_modeller=False behöver INTE ha DEA-data (OK att saknas)
    
    Args:
        gdf_shapes: GeoDataFrame från load_shapes_for_dea()
        df_dea: DataFrame med DEA-resultat
        value_column: Kolumn att merga (t.ex. "Effektivitet")
    
    Returns:
        Tuple[GeoDataFrame med merged data, matchningsstatistik]
    """
    # Ladda reconciliation för intelligent validering
    valid_reid, expected_dea_reid, df_recon = load_valid_reid_registry()
    
    # Förbered DEA-data
    required_cols = ["REId", value_column]
    
    # Hantera företagskolumn flexibelt
    foretag_col = None
    for col in df_dea.columns:
        if any(variant in col.lower() for variant in ['företag', 'foretag']):
            foretag_col = col
            break
    
    if foretag_col:
        required_cols.append(foretag_col)
    
    missing_cols = [c for c in required_cols if c not in df_dea.columns]
    if missing_cols:
        raise ValueError(f"DEA-resultat saknar kolumner: {missing_cols}")
    
    df_merge = df_dea[required_cols].copy()
    df_merge["REId"] = df_merge["REId"].str.strip().str.upper()
    
    if foretag_col and foretag_col != "Företag":
        df_merge = df_merge.rename(columns={foretag_col: "Företag"})
    
    # Analysera matchning FÖRE merge
    shape_reid = set(gdf_shapes["REId"].str.strip().str.upper())
    dea_reid = set(df_merge["REId"])
    
    matched_reid = shape_reid & dea_reid
    only_in_shape = shape_reid - dea_reid
    only_in_dea = dea_reid - shape_reid
    
    # INTELLIGENT KATEGORISERING av saknade
    # Dela upp "only_in_shape" baserat på in_data_modeller
    expected_but_missing = only_in_shape & expected_dea_reid
    ok_to_miss = only_in_shape - expected_dea_reid
    
    # Merge
    gdf_shapes_clean = gdf_shapes.copy()
    gdf_shapes_clean["REId"] = gdf_shapes_clean["REId"].str.strip().str.upper()
    
    gdf_merged = gdf_shapes_clean.merge(df_merge, on="REId", how="left")
    
    # Beräkna missing efter merge
    missing_rows = gdf_merged[value_column].isna().sum()
    total_rows = len(gdf_merged)
    
    # Detaljerad statistik
    match_stats = {
        "total_shapes": len(shape_reid),
        "total_dea": len(dea_reid),
        "matched": len(matched_reid),
        "match_rate": len(matched_reid) / len(shape_reid) if len(shape_reid) > 0 else 0,
        
        # Intelligent kategorisering
        "expected_but_missing": list(expected_but_missing),
        "ok_to_miss": list(ok_to_miss),
        "only_in_dea": list(only_in_dea),
        
        # Legacy för bakåtkompatibilitet
        "only_in_shapes": list(only_in_shape),
        
        # Rad-nivå statistik
        "missing_rows_after_merge": missing_rows,
        "missing_rate_rows": missing_rows / total_rows if total_rows > 0 else 0,
        
        # Från reconciliation
        "total_valid_reid": len(valid_reid),
        "total_expected_dea_reid": len(expected_dea_reid),
    }
    
    return gdf_merged, match_stats


def aggregate_to_unique_geometries(
    gdf: gpd.GeoDataFrame,
    value_column: str = "Effektivitet"
) -> gpd.GeoDataFrame:
    """
    Aggregerar till unika geometrier (för företag med flera REId per polygon).
    
    OBS: För företag med både RER och REL på samma geometri kommer endast
    REL-värdet (som har DEA-data) att användas efter aggregering.
    """
    preserve_cols = {
        "geometry": "first",
        value_column: "mean"
    }
    
    if "Företag" in gdf.columns:
        preserve_cols["Företag"] = "first"
    
    if "REId" in gdf.columns:
        preserve_cols["REId"] = lambda x: ", ".join(x.unique())
    
    gdf_agg = gdf.groupby("geom_id").agg(preserve_cols).reset_index()
    gdf_agg = gpd.GeoDataFrame(gdf_agg, geometry="geometry", crs=gdf.crs)
    
    return gdf_agg


def plot_efficiency_map(
    gdf_agg: gpd.GeoDataFrame,
    value_column: str = "Effektivitet",
    title: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 12)
) -> plt.Figure:
    """
    Skapar en heatmap av effektivitet.
    
    Grå områden = REId utan DEA-data (antingen rena regionnät eller 
    regionnät-delen av företag med både RER och REL).
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    gdf_agg.plot(
        column=value_column,
        cmap="RdYlGn",
        linewidth=0.2,
        ax=ax,
        edgecolor="0.8",
        legend=True,
        missing_kwds={
            "color": "lightgray",
            "edgecolor": "white",
            "label": "Utan DEA-data"
        }
    )
    
    if title is None:
        title = f"{value_column} per geografiskt verksamhetsområde"
    
    ax.set_title(title, fontsize=13, pad=20)
    ax.axis("off")
    
    # Förbättra colorbar
    if len(ax.get_figure().get_axes()) > 1:
        cbar = ax.get_figure().get_axes()[1]
        cbar.set_ylabel(value_column, rotation=270, labelpad=20)
    
    plt.tight_layout()
    return fig


def display_matching_diagnostics(match_stats: Dict, metadata: Dict):
    """
    Visar transparent matchningsdiagnostik med intelligent kategorisering.
    
    Använder in_data_modeller-flaggan för att skilja på:
    - Problematiska saknade (förväntas ha data men saknas)
    - OK saknade (förväntas inte ha data)
    """
    st.write("###  Shapefile-information")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ursprungliga polygoner", metadata["n_polygons_original"])
    with col2:
        st.metric("Efter REId-explosion", metadata["n_rows_after_explode"])
    with col3:
        st.metric("Giltiga REId (reconciliation)", metadata["n_valid_remaining"])
    
    # Visa vad som exkluderades
    if metadata["n_filtered_out"] > 0:
        st.write(f"**Exkluderade från shapefile (ej i reconciliation):** {metadata['n_filtered_out']} rader")
        
        if metadata["excluded_by_type"]:
            excluded_str = ", ".join([f"{k}: {v}" for k, v in metadata["excluded_by_type"].items()])
            st.write(f"  Fördelning: {excluded_str}")
        
        if len(metadata["excluded_reid"]) <= 10:
            st.write(f"  REId: {', '.join(metadata['excluded_reid'])}")
        else:
            with st.expander(f"Visa alla {len(metadata['excluded_reid'])} exkluderade REId"):
                st.write(metadata["excluded_reid"])
    
    # Visa vad som behölls
    st.write("**Behållna nättyper:**")
    for net_type, count in metadata["kept_by_type"].items():
        st.write(f"  - {net_type}: {count} REId")
    
    st.write("###  REId-matchning (Geodata ↔ DEA-resultat)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("REId med geografi", match_stats["total_shapes"])
    with col2:
        st.metric("REId med DEA-data", match_stats["total_dea"])
    with col3:
        match_pct = match_stats["match_rate"] * 100
        st.metric("Matchning", f"{match_pct:.1f}%")
    
    # INTELLIGENT KATEGORISERING AV SAKNADE
    expected_missing = match_stats["expected_but_missing"]
    ok_missing = match_stats["ok_to_miss"]
    no_geo = match_stats["only_in_dea"]
    
    # Problematiska saknade (förväntas ha data)
    if expected_missing:
        n = len(expected_missing)
        st.error(
            f" **{n} REId förväntas ha DEA-data men saknar det**\n\n"
            f"Dessa har `in_data_modeller=True` i reconciliation-filen.\n\n"
            f"Exempel: {', '.join(expected_missing[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} problematiska REId"):
                st.write(expected_missing)
    
    # OK saknade (förväntas inte ha data)
    if ok_missing:
        n = len(ok_missing)
        
        # Analysera typer
        rer_missing = [r for r in ok_missing if r.startswith("RER")]
        ret_missing = [r for r in ok_missing if r.startswith("RET")]
        
        status_icon = "" if n == len(rer_missing) + len(ret_missing) else ""
        
        st.info(
            f"{status_icon} **{n} REId saknar DEA-data (förväntat)**\n\n"
            f"Dessa har `in_data_modeller=False` i reconciliation-filen.\n\n"
            f"Fördelning:\n"
            f"  - RER (regionnät): {len(rer_missing)}\n"
            f"  - RET (transmission): {len(ret_missing)}\n"
            f"  - Övriga: {n - len(rer_missing) - len(ret_missing)}\n\n"
            f"Exempel: {', '.join(ok_missing[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} REId utan DEA-data (OK)"):
                st.write(ok_missing)
    
    # REId med data men utan geografi
    if no_geo:
        n = len(no_geo)
        st.warning(
            f" **{n} REId har DEA-data men saknar geografi**\n\n"
            f"Dessa kan inte visualiseras på kartan.\n\n"
            f"Exempel: {', '.join(no_geo[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} icke-visualiserbara REId"):
                st.write(no_geo)
    
    # Sammanfattning
    if not expected_missing and match_stats["match_rate"] >= 0.85:
        st.success(" Utmärkt matchning - alla förväntade REId har DEA-data")
    elif not expected_missing:
        st.info(" Matchning OK - alla förväntade REId har DEA-data")
    else:
        st.warning(" Problem - vissa förväntade REId saknar DEA-data")