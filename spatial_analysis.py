"""
Beräknar geografisk grannsnittseffektivitet och eff_gap baserat på k-nearest neighbors (centroid).
Förutsätter att GeoDataFrame innehåller kolumnerna 'REId', 'geometry' och indikatorn (t.ex. 'Effektivitet').
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from libpysal.weights import KNN


def lägg_till_grannsnitt(gdf, indikator="Effektivitet", k=4):
    """
    Beräknar medeleffektivitet bland k närmaste geografiska grannar
    och lägger till kolumnerna 'grannsnitt' och 'eff_gap'.
    
    Parametrar:
    - gdf: GeoDataFrame med 'REId', 'geometry' och indikator
    - indikator: kolumn att använda (t.ex. 'Effektivitet')
    - k: antal grannar (standard = 4)

    Returnerar:
    - GeoDataFrame med extra kolumner
    """

    # Kontroll: måste vara GeoDataFrame med CRS
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError("Förväntar GeoDataFrame som input")
    if gdf.crs is None:
        raise ValueError("GeoDataFrame saknar CRS – projicera innan du räknar avstånd")

    # Kopiera och räkna centroids
    gdf = gdf.copy()
    gdf["centroid"] = gdf.geometry.centroid

    # Använd KNN på centroids (räknar på geografiska avstånd)
    w = KNN.from_dataframe(gdf.set_geometry("centroid"), k=k)

    # Hämta värden som array
    värden = gdf[indikator].values

    # Räkna grannsnitt (använder viktmatrisens sparsa representation)
    grannsnitt = w.sparse @ värden / w.cardinalities.values()

    # Lägg till kolumner
    gdf["grannsnitt"] = grannsnitt
    gdf["eff_gap"] = gdf[indikator] - gdf["grannsnitt"]

    # Ta bort centroids (vi vill bara returnera originalgeometri)
    gdf = gdf.drop(columns=["centroid"])

    return gdf
