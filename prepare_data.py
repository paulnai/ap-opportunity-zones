"""
Prepares the data files the dashboard reads.

You only need to run this again when a pillar's results change or a new pillar is added.
It reads the raw outputs (in the "source" folder) and writes small, fast files to "data":

    data/mandals.csv          one row per mandal (all 688), keyed by LGD code
    data/mandals.geojson      simplified mandal boundaries (for the map)
    data/districts.geojson    district outlines, made by merging mandals

Run with:  python prepare_data.py
"""
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry.polygon import orient
from shapely.geometry import MultiPolygon, Polygon

HERE = Path(__file__).parent
SRC, OUT = HERE / "source", HERE / "data"
OUT.mkdir(exist_ok=True)

# ---------- 1. Mandal boundaries (all 688) ----------
geo = gpd.read_file(SRC / "AP_Mandals_688.geojson")
if geo.crs is None:
    geo = geo.set_crs(4326)
geo = geo.to_crs(4326)[["mandal_lgd", "mandal_name", "district_name", "district_lgd", "revenue_division", "geometry"]]
geo["mandal_lgd"] = geo["mandal_lgd"].astype(int)

# Area in km² from an equal-area projection (used in the profile panel)
geo["area_km2"] = geo.to_crs(7755).area / 1e6

# ---------- 2. Connectivity pillar results (612 analysed mandals) ----------
con = pd.read_csv(SRC / "connectivity_mandal_results.csv")
rename = {
    "C1 % habitations with all-weather road": "con_C1",
    "C2 % population with bus service": "con_C2",
    "C3 % road length all-weather": "con_C3",
    "C4 % road length paved": "con_C4",
    "C5 % road length PCI 3+": "con_C5",
    "C6 Road density (km/100 km²)": "con_C6",
    "C7 Highway density (km/100 km²)": "con_C7",
    "connectivity_score": "con_score",
    "score_rank": "con_rank",
    "score_critic": "con_score_critic",
    "score_entropy": "con_score_entropy",
    "region": "con_region",
    "region_name": "con_region_name",
    "n_outlier_vars": "con_n_outlier_vars",
    "city": "con_city",
}
con = con.rename(columns=rename)
keep = ["mandal_lgd"] + list(rename.values())
con = con[keep]

# Regions are grouped into three plain-language levels, exactly as in Part 12 of the notebook
LEVEL_BY_REGION = {
    "Visakhapatnam urban core": "Well connected",
    "Vijayawada urban core": "Well connected",
    "Krishna–Godavari delta and plains": "Well connected",
    "Palnadu–Prakasam uplands": "Average",
    "Rayalaseema and south": "Average",
    "North coastal Andhra": "Average",
    "Godavari agency (hill) belt": "Poorly connected",
    "Annamayya–Sri Sathya Sai pocket": "Poorly connected",
}
con["con_level"] = con["con_region_name"].map(LEVEL_BY_REGION)
assert con["con_level"].notna().all(), "A region name is not in LEVEL_BY_REGION"

# ---------- 3. Join everything on LGD code ----------
# Later pillars (Electricity, Water infrastructure, Water availability, Market access)
# are read here the same way and merged on "mandal_lgd".
attrs = geo.drop(columns="geometry").merge(con, on="mandal_lgd", how="left")
attrs["con_level"] = attrs["con_level"].fillna("Not assessed")
attrs["con_city"] = attrs["con_city"].fillna(False).astype(bool)
assert len(attrs) == 688 and attrs["mandal_lgd"].is_unique
assert (attrs["con_level"] != "Not assessed").sum() == 612

# Markapuram's condition ratings are flagged as suspect in the report
attrs["con_flag_markapuram"] = (attrs["district_name"] == "Markapuram") & attrs["con_score"].notna()

attrs.to_csv(OUT / "mandals.csv", index=False)

# Plotly's map engine (d3) expects outer rings drawn clockwise; otherwise each shape "fills the world".
def clockwise(geom):
    if isinstance(geom, Polygon):
        return orient(geom, sign=-1.0)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in geom.geoms])
    return geom


# ---------- 4. Simplified shapes for a fast map ----------
g = geo[["mandal_lgd", "geometry"]].copy()
g["geometry"] = g.geometry.simplify(0.0015, preserve_topology=True)
g["geometry"] = g.geometry.apply(clockwise)
g.to_file(OUT / "mandals.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)

d = geo.dissolve(by="district_name", as_index=False)[["district_name", "geometry"]]
d["geometry"] = d.geometry.buffer(0).simplify(0.003, preserve_topology=True)
d["geometry"] = d.geometry.apply(clockwise)
d.to_file(OUT / "districts.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)

print("Mandals:", len(attrs), "| analysed:", (attrs.con_level != "Not assessed").sum())
print(attrs["con_level"].value_counts().to_string())
for f in ["mandals.csv", "mandals.geojson", "districts.geojson"]:
    print(f, round((OUT / f).stat().st_size / 1e6, 2), "MB")
