"""
Prepares the data the dashboard reads. Run again only when a pillar's or sector's results change:

    python prepare_data.py

Reads the team's result files in "source/" and writes to "data/":
    data/mandals.csv          one row per mandal (all 688), every layer side by side, keyed by LGD code
    data/mandals.geojson      simplified mandal boundaries (for the map)
    data/districts.geojson    district outlines
    data/name_matching.csv    how files without LGD codes were matched to the official mandals (for checking)

Layer prefixes:  con_ Connectivity · ele_ Electricity · wat_ Water · mkt_ Market access   (infrastructure pillars)
                 agr_ Agriculture · liv_ Livestock · ser_ Rural Services                      (business sectors)
                 aqu_ Aquaculture                                                             (business area)
"""
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

from crosswalk import build

HERE = Path(__file__).parent
SRC, OUT = HERE / "source", HERE / "data"
OUT.mkdir(exist_ok=True)

# ---------- Official mandal map (688) ----------
geo = gpd.read_file(SRC / "AP_Mandals_688.geojson")
geo = (geo.set_crs(4326) if geo.crs is None else geo).to_crs(4326)
geo = geo[["mandal_lgd", "mandal_name", "district_name", "revenue_division", "geometry"]]
geo["mandal_lgd"] = geo["mandal_lgd"].astype(int)
base = geo.drop(columns="geometry").copy()
matching = []


def add(df, prefix, rename, lgd_col="mandal_lgd"):
    """Join one layer's columns onto the 688-mandal table."""
    global base
    d = df.rename(columns={lgd_col: "mandal_lgd"})[["mandal_lgd"] + list(rename)].rename(
        columns={k: f"{prefix}_{v}" for k, v in rename.items()})
    d["mandal_lgd"] = d["mandal_lgd"].astype(int)
    assert d["mandal_lgd"].is_unique, prefix
    unknown = set(d["mandal_lgd"]) - set(base["mandal_lgd"])
    assert not unknown, f"{prefix}: LGD codes not on the map: {sorted(unknown)[:5]}"
    base = base.merge(d, on="mandal_lgd", how="left")


# ---------- Pillar 1: Connectivity (612 analysed) ----------
con = pd.read_csv(SRC / "connectivity_mandal_results.csv")
LEVEL = {"Visakhapatnam urban core": "Well connected", "Vijayawada urban core": "Well connected",
         "Krishna–Godavari delta and plains": "Well connected", "Palnadu–Prakasam uplands": "Average",
         "Rayalaseema and south": "Average", "North coastal Andhra": "Average",
         "Godavari agency (hill) belt": "Poorly connected", "Annamayya–Sri Sathya Sai pocket": "Poorly connected"}
con["level"] = con["region_name"].map(LEVEL)
add(con, "con", {
    "connectivity_score": "score", "score_rank": "rank", "region_name": "region", "level": "level", "city": "city",
    "n_outlier_vars": "n_outlier_vars",
    "C1 % habitations with all-weather road": "C1", "C2 % population with bus service": "C2",
    "C3 % road length all-weather": "C3", "C4 % road length paved": "C4", "C5 % road length PCI 3+": "C5",
    "C6 Road density (km/100 km²)": "C6", "C7 Highway density (km/100 km²)": "C7"})

# ---------- Pillar 2: Electricity (397 analysed; PC1 is the score, per the Electricity report §7.2) ----------
ele = pd.read_csv(SRC / "electricity_mandal_results.csv")
ELE_NAMES = {3: "Visakhapatnam urban", 2: "Vijayawada–Guntur–Krishna", 0: "Coastal / delta",
             4: "North agricultural", 1: "South agricultural", 5: "Hill belt (Polavaram, ASR)"}
ele["region"] = ele["electricity_cluster"].map(ELE_NAMES)
assert ele.groupby("region").size().to_dict() == {"Visakhapatnam urban": 10, "Vijayawada–Guntur–Krishna": 15,
    "Coastal / delta": 128, "North agricultural": 101, "South agricultural": 118, "Hill belt (Polavaram, ASR)": 25}
add(ele, "ele", {"PC1": "score", "region": "region", "PC2": "PC2", "PC3": "PC3"})

# ---------- Pillar 3: Water (688 rows; 661 in the scored sample) ----------
wat = pd.read_csv(SRC / "water_pillar_mandal_scores.csv")
add(wat, "wat", {"water_score": "score", "water_rank": "rank", "water_region": "region",
                 "canal_command_share": "canal", "multi_season_cropping_share": "multiseason",
                 "borewells_per_1000ha": "borewells", "mi_tanks_per_1000ha": "tanks",
                 "median_bore_depth_ft": "boredepth", "ingres_stage_of_extraction_pct": "gw_extraction",
                 "ingres_category": "gw_category", "exclusion_reason": "exclusion_reason"},
    lgd_col="LGD Mandal Code")

# ---------- Pillar 4: Market access (688; 0–100 score, Ward k = 4) ----------
mkt = pd.read_csv(SRC / "ap_mandal_market_access.csv")
MKT_NAMES = {1: "Delta kendra belt", 0: "North-coastal market belt", 2: "Southern low-bazaar block",
             3: "Agency / hill belt"}
mkt["region"] = mkt["cluster_k4"].map(MKT_NAMES)
assert mkt.groupby("region").size().to_dict() == {"Delta kendra belt": 48, "North-coastal market belt": 265,
                                                  "Southern low-bazaar block": 348, "Agency / hill belt": 27}
add(mkt, "mkt", {"score_0_100": "score", "region": "region", "n_rbk": "rbk", "rbk_per_km2": "rbk_density",
                 "n_rythu_bazaar": "bazaars", "n_market_yard": "yards"}, lgd_col="Mandal Code")

assert True
# ---------- Business area: Agriculture (323; the Agriculture team's composite of the 4 pillars) ----------
agr = pd.read_csv(SRC / "agriculture_mandal_composite_scored.csv")
add(agr, "agr", {"agri_composite_score_0_100": "score", "agri_composite_rank": "rank",
                 "opportunity_zone_name": "region", "z_agri_market": "z_market", "z_electricity": "z_electricity",
                 "z_water": "z_water", "z_connectivity": "z_connectivity"})


# ---------- Files without LGD codes: matched by mandal + district name ----------
def add_named(file, prefix, rename, label):
    d = pd.read_csv(SRC / file)
    lgd, how = build(base[["mandal_lgd", "mandal_name", "district_name"]], d, "district_name", "mandal")
    d["mandal_lgd"] = lgd
    assert d["mandal_lgd"].notna().all() and d["mandal_lgd"].is_unique, prefix
    matching.append(pd.DataFrame({"layer": label, "file_district": d["district_name"], "file_mandal": d["mandal"],
                                  "mandal_lgd": d["mandal_lgd"], "match": how}))
    add(d, prefix, rename)


add_named("livestock_mandal_scored.csv", "liv", {
    "livestock_scale_score_pc1": "score", "livestock_region_name": "region", "TLU": "tlu",
    "buffalo_ratio": "buffalo_ratio", "small_ruminant_spec_index": "small_ruminant",
    "catchment_15km_tlu": "catchment_tlu", "vet_support_per_1000_tlu": "vet_support",
    "commercial_offtake_demand_density": "demand_density"}, "Livestock")
add_named("rural_services_mandal_scored.csv", "ser", {
    "service_opportunity_score_pc1": "score", "service_region_name": "region",
    "civic_admin_footfall": "civic", "education_anchor_scale": "education", "healthcare_capacity": "health",
    "nutrition_pds_network": "pds", "heritage_tourism_pull": "tourism",
    "overture_transport_junctions": "transport"}, "Rural Services")
add_named("aquaculture_mandal_scored.csv", "aqu", {
    "aquaculture_opportunity_score_pc1": "score", "aqua_region_name": "region",
    "aqua_production_scale": "production", "aqua_expansion_headroom": "headroom",
    "saltpan_commercial_capacity": "saltpan", "aqua_intensity_ratio": "intensity",
    "marine_landing_anchor": "landing"}, "Aquaculture")

# ---------- Checks against each report ----------
assert len(base) == 688 and base["mandal_lgd"].is_unique
counts = {p: int(base[f"{p}_score"].notna().sum()) for p in ["con", "ele", "wat", "mkt", "agr", "liv", "ser", "aqu"]}
assert counts == {"con": 612, "ele": 397, "wat": 661, "mkt": 688, "agr": 323, "liv": 679, "ser": 679,
                  "aqu": 679}, counts
assert (base.con_level.value_counts().to_dict() == {"Average": 410, "Well connected": 161, "Poorly connected": 41})
base["con_level"] = base["con_level"].fillna("Not assessed")
base["con_city"] = base["con_city"].fillna(False).astype(bool)
base["con_flag_markapuram"] = (base["district_name"] == "Markapuram") & base["con_score"].notna()

base.to_csv(OUT / "mandals.csv", index=False)
pd.concat(matching).to_csv(OUT / "name_matching.csv", index=False)


# ---------- Map shapes (simplified; outer rings clockwise for Plotly's map engine) ----------
def clockwise(gm):
    if isinstance(gm, Polygon):
        return orient(gm, sign=-1.0)
    if isinstance(gm, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in gm.geoms])
    return gm


g = geo[["mandal_lgd", "geometry"]].copy()
g["geometry"] = g.geometry.simplify(0.0015, preserve_topology=True).apply(clockwise)
g.to_file(OUT / "mandals.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)
d = geo.dissolve(by="district_name", as_index=False)[["district_name", "geometry"]]
d["geometry"] = d.geometry.buffer(0).simplify(0.003, preserve_topology=True).apply(clockwise)
d.to_file(OUT / "districts.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)

print("Mandals with a score, by layer:", counts)
