"""
Beräknar geografisk grannsnittseffektivitet och effektivitetsgap (eff_gap) med valbar metod.

Modellspecifikation:
- Relativ effektivitet definieras som skillnaden mellan ett företags effektivitet och medeleffektiviteten bland geografiska grannar.
- Två metoder stöds:
    - KNN: närmaste k grannar baserat på centroidavstånd.
    - DistanceBand: alla grannar inom angivet avstånd (t.ex. 50 km).

Motivering:
Jämförelse med geografiska grannar möjliggör identifiering av lokal förbättringspotential respektive strukturella hinder.

Parametrar:
- gdf: GeoDataFrame med kolumnerna 'REId', 'geometry' och t.ex. 'Effektivitet'
- indikator: vilken kolumn som ska analyseras (default = 'Effektivitet')
- method: 'knn' eller 'distanceband' (default = 'knn')
- k: antal grannar (om method='knn')
- distance_threshold: gräns i meter (om method='distanceband')

Returnerar:
- GeoDataFrame med kolumnerna 'grannsnitt' och 'eff_gap'
"""

import geopandas as gpd
import numpy as np
from libpysal.weights import KNN, DistanceBand

def lägg_till_grannsnitt(gdf, indikator="Effektivitet", method="knn", k=4, distance_threshold=50000, avståndsviktning=False):
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError("Förväntar GeoDataFrame som input")
    if gdf.crs is None:
        raise ValueError("GeoDataFrame saknar CRS – projicera innan du räknar avstånd")

    gdf = gdf.copy()
    gdf["centroid"] = gdf.geometry.centroid
    värden = gdf[indikator].values

    if method == "knn":
        w = KNN.from_dataframe(gdf.set_geometry("centroid"), k=k)
        dists = w.full()[1]
    elif method == "distanceband":
        w = DistanceBand.from_dataframe(
            gdf.set_geometry("centroid"),
            threshold=distance_threshold,
            silence_warnings=True,
            binary=not avståndsviktning
        )
        dists = w.full()[1]
    else:
        raise ValueError("Ogiltig metod. Välj 'knn' eller 'distanceband'.")

    if avståndsviktning:
        weights = 1 / np.maximum(dists, 1)  # undvik delning med 0
        weighted_vals = w.sparse.multiply(weights) @ värden
        norm = w.sparse.multiply(weights).sum(axis=1).A1
        grannsnitt = weighted_vals / norm
    else:
        card = np.array(list(w.cardinalities.values()))
        grannsnitt = (w.sparse @ värden) / card

    gdf["grannsnitt"] = grannsnitt
    gdf["eff_gap"] = gdf[indikator] - gdf["grannsnitt"]
    gdf = gdf.drop(columns=["centroid"])

    return gdf
