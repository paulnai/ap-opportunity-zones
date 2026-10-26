"""
Entrepreneurial Opportunity Zones — results explorer (Problem Statement 2)
ISB AMPBA Capstone · SERP, Government of Andhra Pradesh

Built around the professor's review (24 Oct 2026):
  · one pillar on the map at a time, with a few simple colours
  · each mandal's performance across all four pillars side by side
Business areas (Agriculture, Livestock, Rural Services, Aquaculture) follow as a second section.

Start it with:   streamlit run app.py
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent
DATA = HERE / "data"
st.set_page_config(page_title="AP Opportunity Zones Explorer", page_icon="🗺️", layout="wide",
                   initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════════════════════════
# 1. SETTINGS — every label, colour, caveat and weight lives here
# ════════════════════════════════════════════════════════════════════════════
INK, INK2, MUTED = "#22211f", "#55534d", "#8a877f"
NO_DATA = "#e4e2dc"
LEVEL_COLOURS = {"High": "#1c5cab", "Medium": "#aaa596", "Low": "#c0392b"}   # same three as the Connectivity POC
LEVEL_TEXT = {"High": "#ffffff", "Medium": INK, "Low": "#ffffff"}
CON_LEVEL_WORD = {"Well connected": "High", "Average": "Medium", "Poorly connected": "Low"}

PILLARS = {
    "con": dict(name="Connectivity", icon="🛣️", question="Can inputs and outputs move?",
                score_kind="index", score_label="Connectivity score",
                score_help="PCA score of seven road measures; 0 = average analysed mandal, higher = better connected.",
                level_rule="Levels from the Connectivity report: Well connected (High), Average (Medium), "
                           "Poorly connected (Low).",
                nodata="Not assessed: road data missing (mostly the old Visakhapatnam district). Not the same as poor roads.",
                source="Connectivity (Roads) pillar report and notebook",
                measures=[("C1", "Villages with all-weather road", "pct"), ("C2", "People with a bus service", "pct"),
                          ("C3", "Road length all-weather", "pct"), ("C4", "Road length paved", "pct"),
                          ("C5", "Road length in fair+ condition", "pct"), ("C6", "Road density (km/100 km²)", "num"),
                          ("C7", "Highway density (km/100 km²)", "num")],
                caveats=["76 mandals not assessed: 39 in the old Visakhapatnam district (Anakapalli, Alluri Sitharama "
                         "Raju, Visakhapatnam) with blank village and bus records, 25 missing one measure, 12 cities "
                         "with too little town-road data.",
                         "City mandals (15): village access and bus service assumed 100%; road condition is a "
                         "district estimate. Markapuram condition ratings look unreliable."]),
    "ele": dict(name="Electricity", icon="⚡", question="Can the enterprise operate?",
                score_kind="index", score_label="Electricity score (PC1)",
                score_help="First principal component of transformer (DTR) measures and night-time light; "
                           "0 = average analysed mandal, higher = more electrified.",
                level_rule="Levels are thirds of the 397 scored mandals: top third High, middle Medium, bottom Low.",
                nodata="No electricity data (APSPDCL area or no transformer records). Not the same as low electricity.",
                source="Electricity Dimension report",
                measures=[("PC2", "Agricultural vs industrial load (PC2)", "idx"),
                          ("PC3", "Industrial load vs network density (PC3)", "idx")],
                caveats=["Only 397 mandals (APEPDCL and APCPDCL areas). No usable data for nine districts: "
                         "Ananthapuramu, YSR Kadapa, Kurnool, Annamayya, Nandyal, Sri Sathya Sai, Nellore, Tirupati "
                         "and Chittoor.",
                         "Transformer records show infrastructure, not reliable supply."]),
    "wat": dict(name="Water", icon="💧", question="Can production be supported?",
                score_kind="0-100", score_label="Water score (0–100)",
                score_help="PCA score of five water measures, rescaled 0–100; higher = more water available.",
                level_rule="Levels are thirds of the 661 scored mandals: top third High, middle Medium, bottom Low.",
                nodata="Not scored (reason shown in the profile). Not the same as low water.",
                source="Water Pillar report (score and regions)",
                measures=[("canal", "Area under canal command", "pct"), ("multiseason", "Multi-season cropping", "pct"),
                          ("borewells", "Borewells per 1,000 ha", "num"), ("tanks", "MI tanks per 1,000 ha", "num"),
                          ("boredepth", "Median borewell depth (ft)", "num"),
                          ("gw_extraction", "Groundwater extraction (% of recharge)", "num")],
                caveats=["27 mandals not scored: post-2011 urban splits with no separate boundary, or under "
                         "10 km² of cropland."]),
    "mkt": dict(name="Market access", icon="🏪", question="Can it reach markets?",
                score_kind="0-100", score_label="Market access score (0–100)",
                score_help="PC1 of Rythu Bharosa Kendra density, Rythu Bazaars and market yards, rescaled 0–100; "
                           "higher = more selling and procurement points.",
                level_rule="Levels are thirds of all 688 mandals: top third High, middle Medium, bottom Low.",
                nodata="—", source="Agriculture Market Access analysis",
                measures=[("rbk", "Rythu Bharosa Kendras", "int"), ("rbk_density", "Kendras per km²", "num"),
                          ("bazaars", "Rythu Bazaars", "int"), ("yards", "Market yards", "int")],
                caveats=["Measures facility presence, not turnover, prices or travel time."]),
}

_OPP_NODATA = ("Not in the team's opportunity model: it covers the 323 mandals with data on all four pillars "
               "(mostly Electricity is missing in the south). A data gap, not a low score.")
_OPP_LEVEL = "Levels are thirds of the 323 scored mandals: top third High, middle Medium, bottom Low."
_OPP_SRC = "Integrated clustering report and notebook (Shareen)"
BUSINESSES = {
    "agr": dict(name="Agriculture", icon="🌾", score_kind="0-100", score_label="Opportunity score (0–100)",
                score_help="The team's opportunity score: market access, electricity, water and connectivity, "
                           "standardised and weighted equally, rescaled 0–100.",
                level_rule=_OPP_LEVEL, nodata=_OPP_NODATA, source=_OPP_SRC,
                measures=[("z_market", "Market access (z-score)", "idx"), ("z_electricity", "Electricity (z-score)", "idx"),
                          ("z_water", "Water (z-score)", "idx"), ("z_connectivity", "Connectivity (z-score)", "idx")],
                caveats=["323 mandals: only those with all four pillars.",
                         "Same file as before; the Integrated clustering folder did not change it."]),
    "liv": dict(name="Livestock", icon="🐄", score_kind="0-100", score_label="Opportunity score (0–100)",
                score_help="The team's opportunity score: livestock scale plus market access, electricity, water and "
                           "connectivity, standardised and weighted equally, rescaled 0–100.",
                level_rule=_OPP_LEVEL, nodata=_OPP_NODATA, source=_OPP_SRC,
                measures=[("act", "Business activity score (livestock scale, PC1)", "idx"),
                          ("tlu", "Tropical livestock units", "num"), ("buffalo_ratio", "Buffalo ratio", "num"),
                          ("small_ruminant", "Small-ruminant specialisation", "num"),
                          ("catchment_tlu", "Livestock within 15 km (TLU)", "num"),
                          ("vet_support", "Vet support per 1,000 TLU", "num"),
                          ("demand_density", "Commercial demand density", "num")],
                caveats=["Opportunity score covers 323 mandals (all four pillars).",
                         "Business activity score and its measures cover 679 mandals, matched by name (no LGD code)."]),
    "ser": dict(name="Rural Services", icon="🏥", score_kind="0-100", score_label="Opportunity score (0–100)",
                score_help="The team's opportunity score: rural services market plus electricity, water and "
                           "connectivity, standardised and weighted equally, rescaled 0–100.",
                level_rule=_OPP_LEVEL, nodata=_OPP_NODATA, source=_OPP_SRC,
                measures=[("act", "Business activity score (services, PC1)", "idx"),
                          ("civic", "Civic and admin footfall", "num"), ("education", "Education anchors", "num"),
                          ("health", "Healthcare capacity", "num"), ("pds", "Nutrition / PDS network", "num"),
                          ("tourism", "Heritage and tourism pull", "num"), ("transport", "Transport junctions", "num")],
                caveats=["Opportunity score covers 323 mandals; it does not use the Market access pillar.",
                         "Business activity score and its measures cover 679 mandals, matched by name (no LGD code)."]),
    "aqu": dict(name="Aquaculture", icon="🐟", score_kind="0-100", score_label="Opportunity score (0–100)",
                score_help="The team's opportunity score: aquaculture scale plus electricity, water and connectivity, "
                           "standardised and weighted equally, rescaled 0–100.",
                level_rule=_OPP_LEVEL, nodata=_OPP_NODATA, source=_OPP_SRC,
                measures=[("act", "Business activity score (aquaculture, PC1)", "idx"),
                          ("production", "Production scale (ha)", "num"), ("headroom", "Expansion headroom (ha)", "num"),
                          ("saltpan", "Saltpan capacity (ha)", "num"), ("intensity", "Pond intensity ratio", "num"),
                          ("landing", "Marine landing anchor", "num")],
                caveats=["Opportunity score covers 323 mandals; it does not use the Market access pillar.",
                         "Business activity score and its measures cover 679 mandals, matched by name (no LGD code)."]),
}
# The team's integrated opportunity models (Integrated clustering folder): file, score column, rank column
COMPOSITE = {"agr": ("agriculture_mandal_composite_scored.csv", "agri_composite_score_0_100"),
             "liv": ("livestock_mandal_composite_scored.csv", "live_composite_score_0_100"),
             "ser": ("rural_services_mandal_composite_scored.csv", "services_composite_score_0_100"),
             "aqu": ("aquaculture_mandal_composite_scored.csv", "aqua_composite_score_0_100")}
# Each zone's possible SHG enterprises and support range, from the four Integrated clustering reports
ZONE_INFO = {
    "agr": {1: ("Drying yards, mini dal mills, vegetable crating, sprayer hiring", "₹1.5–3.0 lakh per SHG / VO"),
            2: ("Pulse cleaning and packing, vermicompost, seed counters", "₹1.0–2.5 lakh per SHG / VO"),
            3: ("Turmeric and ginger processing, forest-produce cleaning, solar drying", "₹0.8–2.0 lakh per tribal SHG"),
            4: ("Cashew grading, mango pulp and pickle units, solar fruit dryers", "₹1.0–2.5 lakh per SHG / PG"),
            5: ("Millet destoners, flour mills, community seed banks", "₹0.5–1.5 lakh per SHG")},
    "liv": {1: ("Milk testing kiosks, mini bulk milk coolers, curd and ghee units", "₹1.5–3.0 lakh per SHG / VO"),
            2: ("Fodder silage bags, cattle feed retail, doorstep animal health kits", "₹1.0–2.5 lakh per SHG / VO"),
            3: ("Sheep and goat rearing groups, meat stalls, mineral feed blocks", "₹1.0–2.5 lakh per SHG / PG"),
            4: ("Desi cow ghee, solar milk coolers, backyard poultry", "₹0.8–2.0 lakh per SHG"),
            5: ("Native poultry mother units, backyard goat and piggery, fodder groups", "₹0.5–1.5 lakh per tribal SHG")},
    "ser": {1: ("MeeSeva and banking kiosks, delivery points, chilled storage", "₹1.5–3.0 lakh per SHG / VO"),
            2: ("Community RO water ATMs, farm tool hiring, solar crop dryers", "₹1.5–2.5 lakh per SHG / VO"),
            3: ("Multi-utility village kiosks, solar lantern rental, cashew and forest-produce aggregation", "₹0.6–1.5 lakh per SHG"),
            4: ("Solar mini dal and flour mills, feed kiosks, solar pump leasing", "₹1.0–2.0 lakh per SHG"),
            5: ("Off-grid solar outlets, bio-sand water filters, mobile health and vet kits", "₹0.5–1.5 lakh per SHG")},
    "aqu": {1: ("Shrimp sorting and deveining sheds, insulated ice boxes, fish pickles", "₹1.5–3.0 lakh per SHG"),
            2: ("Fingerling nurseries, live fish vending", "₹1.0–2.5 lakh per SHG / VO"),
            3: ("Minor-tank fish aggregation, fresh fish stalls", "₹0.5–1.5 lakh per SHG"),
            4: ("Solar fish drying racks, dry-fish packing, ice boxes", "₹0.8–2.0 lakh per SHG"),
            5: ("Not suited to aquaculture: the report suggests millets, poultry or goats instead",
                "Not eligible for aquaculture grants")},
}
LAYERS = {**PILLARS, **BUSINESSES}

# What each business needs from each pillar (used only for the infrastructure check, not for any score)
WORD = {"Low": 1.0, "Low/Medium": 1.5, "Medium": 2.0, "Medium/High": 2.5, "High": 3.0}
DRAFT = {
    "agr": dict(w={"wat": "High", "ele": "Medium", "con": "High", "mkt": "High"}, src="mid-review deck, slide 14"),
    "liv": dict(w={"wat": "High", "ele": "High", "con": "High", "mkt": "High"}, src="mid-review deck, slide 14"),
    "ser": dict(w={"wat": "Low", "ele": "High", "con": "Medium/High", "mkt": "High"}, src="mid-review deck, slide 14"),
    "aqu": dict(w={"wat": "High", "ele": "High", "con": "Medium/High", "mkt": "Medium"},
                src="Claude's suggestion, approved by Nairita; pending team review"),
}
PK = list(PILLARS)

st.markdown("""
<style>
  .block-container {padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1500px;}
  .eyebrow {font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:#8a877f; margin-bottom:.1rem;}
  .kpi {border:1px solid #e3e1da; border-radius:10px; padding:.65rem .9rem; background:#fff; height:100%;}
  .kpi .n {font-size:1.45rem; font-weight:650; line-height:1.15; color:#22211f;}
  .kpi .l {font-size:.8rem; color:#55534d; margin-top:.15rem;}
  .sw {display:inline-block; width:.7rem; height:.7rem; border-radius:3px; margin-right:.35rem; vertical-align:-1px;}
  .pc {border:1px solid #e3e1da; border-radius:10px; padding:.6rem .75rem; background:#fff; margin-bottom:.55rem;}
  .pc.sel {border:2px solid #22211f;}
  .pc .t {font-size:.8rem; color:#55534d;}
  .pc .lv {display:inline-block; padding:.08rem .5rem; border-radius:999px; font-size:.78rem; font-weight:650; margin:.25rem 0;}
  .pc .bar {height:6px; background:#efeee9; border-radius:3px; margin-top:.3rem;}
  .pc .bar div {height:6px; border-radius:3px;}
  .pc .s {font-size:.76rem; color:#8a877f; margin-top:.2rem;}
  .card {border:1px solid #e3e1da; border-radius:10px; padding:.8rem 1rem; background:#fff; margin-bottom:.6rem;}
  .muted {color:#8a877f; font-size:.85rem;}
  .note {background:#f7f6f2; border-left:3px solid #bdbab1; padding:.5rem .75rem; border-radius:4px; font-size:.86rem; color:#55534d; margin:.4rem 0;}
  .draft {background:#fff6e5; border-left:3px solid #e3a008; padding:.55rem .8rem; border-radius:4px; font-size:.88rem; color:#5c4400; margin:.4rem 0;}
  div[data-testid="stMetricValue"] {font-size:1.35rem;}
  .sq {font-size:18px; margin:1rem 0 .5rem 0; color:#22211f;}
  .sbox {border:1px solid #d6d3cb; border-radius:10px; padding:.8rem 1rem; background:#fff; height:100%;
         font-size:15px; color:#22211f;}
  .sbox .sh {font-size:16px; font-weight:700;}
  .sbox .sl {margin:.35rem 0 .55rem 0;}
  .sbox .big {font-size:26px; font-weight:700;}
  .sbox .sm, .sm {font-size:13px; color:#55534d;}
  .sbox .kv {margin:.25rem 0; line-height:1.45;}
  .bdg {display:inline-block; padding:2px 10px; border-radius:12px; font-weight:600; font-size:14px; white-space:nowrap;}
  table.st {width:100%; border-collapse:collapse; font-size:14px;}
  table.st th {text-align:left; color:#55534d; font-weight:600; border-bottom:1px solid #d6d3cb; padding:4px 6px;}
  table.st td {border-bottom:1px solid #eeece6; padding:5px 6px; vertical-align:middle;}
  .chips {display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:.2rem 0 .4rem 0;}
  .chip {border:1px solid #e3e1da; border-radius:14px; padding:3px 10px; background:#fff; font-size:14px; white-space:nowrap;}
  .mapcap {text-align:center; font-size:16px; color:#22211f; margin-top:-1.6rem; position:relative;}
</style>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# 2. DATA
# ════════════════════════════════════════════════════════════════════════════
def tercile(pct):
    return np.where(pd.isna(pct), None, np.where(pct > 200 / 3, "High", np.where(pct > 100 / 3, "Medium", "Low")))


@st.cache_data
def load():
    df = pd.read_csv(DATA / "mandals.csv")
    for b, (f, sc) in COMPOSITE.items():
        c = pd.read_csv(HERE / "source" / "integrated" / f)[["mandal_lgd", sc, "opportunity_zone_name"]]
        c = c.rename(columns={sc: f"{b}_opp", "opportunity_zone_name": f"{b}_zone"})
        assert c["mandal_lgd"].is_unique and c["mandal_lgd"].isin(df["mandal_lgd"]).all(), b
        df = df.merge(c, on="mandal_lgd", how="left")
        df[f"{b}_act"] = df[f"{b}_score"]            # the business team's own score (business data only)
        df[f"{b}_score"] = df[f"{b}_opp"]            # the map and levels use the opportunity score
        df[f"{b}_region"] = df[f"{b}_zone"]
        df[f"{b}_zone_no"] = df[f"{b}_zone"].str.extract(r"Zone (\d)", expand=False).astype(float)
    for k, v in LAYERS.items():
        s = df[f"{k}_score"]
        df[f"{k}_pct"] = s.rank(pct=True) * 100
        df[f"{k}_rk"] = s.rank(ascending=False, method="min")
        df[f"{k}_lvl"] = tercile(df[f"{k}_pct"])
        for col, *_ in v["measures"]:
            df[f"{k}_{col}_pct"] = df[f"{k}_{col}"].rank(pct=True) * 100
    df["con_lvl"] = df["con_level"].map(CON_LEVEL_WORD)       # Connectivity keeps its report's levels
    df["label"] = df["mandal_name"] + " (" + df["district_name"] + ")"
    return df, json.loads((DATA / "mandals.geojson").read_text()), json.loads((DATA / "districts.geojson").read_text())


DF, MANDAL_GEO, DISTRICT_GEO = load()
N = {k: int(DF[f"{k}_score"].notna().sum()) for k in LAYERS}


def lvl(v):
    return v if isinstance(v, str) else "no data"


def fmt_score(kind, v):
    if pd.isna(v):
        return "no data"
    return f"{v:.0f}" if kind == "0-100" else f"{v:+.2f}"


def fmt_measure(kind, v, star=False):
    if pd.isna(v):
        return "—"
    if kind == "pct":
        return f"{v*100:.0f}%" + ("*" if star else "")
    if kind == "int":
        return f"{v:,.0f}"
    if kind == "idx":
        return f"{v:+.2f}"
    return f"{v:,.2f}" if abs(v) < 100 else f"{v:,.0f}"



# ════════════════════════════════════════════════════════════════════════════
# 3. SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Opportunity Zones Explorer")
    # Nothing picked = the opening overview (both maps side by side). A button brings it back.
    section = st.radio("Section", ["Infrastructure pillars", "Business areas"], index=None, key="section_radio",
                       captions=["Water, Electricity, Connectivity, Market access",
                                 "Agriculture, Livestock, Rural Services, Aquaculture"])
    if section is None:
        section = "Overview"
    else:
        st.button("↩ Back to the Andhra Pradesh overview", use_container_width=True,
                  on_click=lambda: st.session_state.update(section_radio=None, mandal_lgd=None))
    scope = "one"
    if section == "Infrastructure pillars":
        pick = st.selectbox("Pillar on the map", PK, index=None, placeholder="Select a pillar",
                            format_func=lambda k: f"{PILLARS[k]['icon']}  {PILLARS[k]['name']}",
                            help="Leave blank to see all four pillars together (the opening map). Pick one pillar "
                                 "to see it on its own. Select a mandal to see it on all four pillars side by side.")
        # Blank = the four pillars read together; "con" is only a placeholder layer for that view
        scope, layer = ("all", "con") if pick is None else ("one", pick)
        view = "team"
    elif section == "Overview":
        scope, layer, view = "all", "con", "team"
    else:
        pickb = st.selectbox("Business area", list(BUSINESSES), index=None, placeholder="Select a business area",
                             format_func=lambda k: f"{BUSINESSES[k]['icon']}  {BUSINESSES[k]['name']}",
                             help="Leave blank to see all four business areas together (the opening map). Pick one "
                                  "to see its opportunity score on its own.")
        scope, layer = ("all", "agr") if pickb is None else ("one", pickb)
        view = "team"
    MODES = {
        "level": ("Level (High / Medium / Low)", "Compared with the whole state"),
        "dlevel": ("Level within the district", "Compared with mandals in the same district"),
        "score": ("Score (shading)", "Finer detail than three levels"),
        "measure": ("A single measure", "One input to the score, e.g. canal coverage"),
        "best": ("Strongest pillar", "The pillar each mandal scores highest on"),
        "nhigh": ("How many pillars are strong", "Strong = top third of the state on that pillar"),
        "bbest": ("Strongest business area", "The business each mandal scores highest on"),
        "bnhigh": ("How many business areas are strong", "Strong = top third of the opportunity score"),
        "weak": ("Weakest pillar (bottleneck)", "What is holding each mandal back"),
        "cover": ("Data coverage (0–4 pillars with data)", "Where data is missing"),
    }
    one = ["level", "score", "dlevel"] + (["measure"] if view == "team" and layer != "ele" and LAYERS[layer]["measures"] else [])
    avail = one if scope == "one" else (["best", "nhigh", "weak", "cover"] if section == "Infrastructure pillars"
                                        else ["bbest", "bnhigh"])
    colour_by = "level" if section == "Overview" else \
        st.radio("Colour the map by", avail, format_func=lambda m: MODES[m][0], captions=[MODES[m][1] for m in avail])
    measure_pick = None
    if colour_by == "measure":
        ms = LAYERS[layer]["measures"]
        measure_pick = st.selectbox("Measure", range(len(ms)), format_func=lambda i: ms[i][1])
    st.divider()
    # When a mandal opens the four-pillar view, fill in its district here. "Back to the state map" puts back
    # whatever the filter held before.
    _sel = st.session_state.get("mandal_lgd")
    _ss = st.session_state
    if _ss.pop("restore_districts", False) and _ss.get("auto_dist_for") is not None:
        _ss.districts_ms = _ss.get("prev_districts", [])
        _ss.auto_dist_for = None
    if _sel is not None and section == "Infrastructure pillars" and _ss.get("auto_dist_for") != _sel:
        _hits = DF.loc[DF["mandal_lgd"] == _sel, "district_name"]
        if not _hits.empty:
            if _ss.get("auto_dist_for") is None:
                _ss.prev_districts = list(_ss.get("districts_ms", []))
            _ss.districts_ms = [_hits.iloc[0]]
            _ss.auto_dist_for = _sel
    districts = st.multiselect("Districts", sorted(DF["district_name"].unique()), placeholder="All 26 districts",
                               key="districts_ms",
                               help="Leave empty for the whole state. The map zooms to the districts you pick. "
                                    "Filled in automatically when you select a mandal.")
    st.caption("Grey on every map means **no data**, never a low score.")

# Current layer
DF["cur_score"] = DF[f"{layer}_score"]
META = LAYERS[layer]
DF["cur_pct"] = DF["cur_score"].rank(pct=True) * 100
DF["cur_rk"] = DF["cur_score"].rank(ascending=False, method="min")
DF["cur_lvl"] = DF["con_lvl"] if (view == "team" and layer == "con") else tercile(DF["cur_pct"])
N_CUR = int(DF["cur_score"].notna().sum())
DF["cur_dpct"] = DF.groupby("district_name")["cur_score"].rank(pct=True) * 100
DF["cur_dlvl"] = tercile(DF["cur_dpct"])
# All-pillar views compare like with like: every pillar, Connectivity included, split into thirds
for _p in PK:
    DF[f"{_p}_t3"] = tercile(DF[f"{_p}_pct"])
_lv = DF[[f"{p}_t3" for p in PK]]
DF["n_data"] = _lv.notna().sum(axis=1)
DF["n_high"] = (_lv == "High").sum(axis=1)


def _weakest(r):
    lows = [p for p in PK if r[f"{p}_t3"] == "Low"]
    if not lows:
        return "No bottleneck" if r["n_data"] > 0 else None
    return PILLARS[min(lows, key=lambda p: r[f"{p}_pct"])]["name"]


DF["weak"] = DF.apply(_weakest, axis=1)


def _strongest(r):
    """The pillar a mandal scores highest on, among the pillars where it is High (top third)."""
    highs = [p for p in PK if r[f"{p}_t3"] == "High"]
    if not highs:
        return "Not strong on any pillar" if r["n_data"] > 0 else None
    return PILLARS[max(highs, key=lambda p: r[f"{p}_pct"])]["name"]


DF["best"] = DF.apply(_strongest, axis=1)
# Business areas read together: the same idea, using each business's opportunity score
BK = list(BUSINESSES)
for _b in BK:
    DF[f"{_b}_t3"] = tercile(DF[f"{_b}_pct"])
_bl = DF[[f"{b}_t3" for b in BK]]
DF["b_data"] = _bl.notna().sum(axis=1)
DF["b_high"] = (_bl == "High").sum(axis=1)


def _strongest_biz(r):
    highs = [b for b in BK if r[f"{b}_t3"] == "High"]
    if not highs:
        return "Not strong in any business area" if r["b_data"] > 0 else None
    return BUSINESSES[max(highs, key=lambda b: r[f"{b}_pct"])]["name"]


DF["bbest"] = DF.apply(_strongest_biz, axis=1)
# Which pillars / business areas are strong, written out (for hover, the breakdown table and highlighting)
DF["p_combo"] = DF.apply(lambda r: " + ".join(PILLARS[p]["name"] for p in PK if r[f"{p}_t3"] == "High"), axis=1)
DF["b_combo"] = DF.apply(lambda r: " + ".join(BUSINESSES[b]["name"] for b in BK if r[f"{b}_t3"] == "High"), axis=1)


def strong_line(r, biz):
    """Hover line: which pillars (or business areas) are strong for this mandal."""
    if (r["b_data"] if biz else r["n_data"]) == 0:
        return "Data not available"
    combo = r["b_combo"] if biz else r["p_combo"]
    if not combo:
        return "Not strong in any business area" if biz else "Not strong on any pillar"
    return ("Strong in: " if biz else "Strong on: ") + "<b>" + combo.replace(" + ", ", ") + "</b>"


def strong_label(n, biz):
    if biz:
        return ("Strong in all 4 business areas" if n == 4 else "Not strong in any business area" if n == 0
                else f"Strong in {n} business area{'s' if n > 1 else ''}")
    return ("Strong on all 4 pillars" if n == 4 else "Not strong on any pillar" if n == 0
            else f"Strong on {n} pillar{'s' if n > 1 else ''}")
RG = f"{layer}_region" if (view == "team" and scope == "one") else None

df = DF if not districts else DF[DF["district_name"].isin(districts)]
scored = df[df["cur_score"].notna()]
# No mandal is selected at start: the state map shows as before. Selecting a mandal (click or search)
# switches the map area to that mandal's four-pillar view.
if "mandal_lgd" not in st.session_state:
    st.session_state.mandal_lgd = None
if "map_ver" not in st.session_state:
    st.session_state.map_ver = 0          # bumping this resets the maps' click state
if st.session_state.mandal_lgd is not None and st.session_state.mandal_lgd not in set(df["mandal_lgd"]):
    st.session_state.mandal_lgd = None    # the user filtered the mandal out: keep their filter
    st.session_state.auto_dist_for = None


def select_mandal(lgd):
    st.session_state.mandal_lgd = None if lgd is None else int(lgd)
    if lgd is None:
        st.session_state.restore_districts = True   # applied before the Districts box is drawn
    st.session_state.map_ver += 1
    st.rerun()


if section != "Overview":
    # ════════════════════════════════════════════════════════════════════════════
    # 4. HEADER
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="eyebrow">Entrepreneurial Opportunity Zones · Andhra Pradesh · mandal level</div>',
                unsafe_allow_html=True)
    BIZ = section == "Business areas"
    if BIZ:
        title = ("Andhra Pradesh Business Opportunity Overview" if scope == "all"
                 else f"{BUSINESSES[layer]['icon']} {BUSINESSES[layer]['name']} — opportunity score")
        sub = ("Agriculture, Livestock, Rural Services and Aquaculture read together, using each team's opportunity score."
               if scope == "all" else META["score_help"])
    else:
        title = ("Andhra Pradesh Infrastructure Overview" if scope == "all" else
                 f"{PILLARS[layer]['icon']} {PILLARS[layer]['name']} — {PILLARS[layer]['question']}")
        sub = ("Water, Electricity, Connectivity and Market access read together for each mandal."
               if scope == "all" else META["score_help"])
    st.markdown(f"## {title}")
    st.caption(f"{', '.join(districts) if districts else 'All of Andhra Pradesh'} · {sub}")

    cnt = scored["cur_lvl"].value_counts()
    if scope == "all" and BIZ:
        cols = st.columns(5)
        cols[0].markdown(f'<div class="kpi"><div class="n">{len(df):,}</div><div class="l">Mandals in total<br>'
                         f'<span style="opacity:.75">{int((df["b_data"] > 0).sum()):,} in the teams\' opportunity '
                         f'models</span></div></div>', unsafe_allow_html=True)
        for c, b in zip(cols[1:], BK):
            n_hi = int((df[f"{b}_t3"] == "High").sum())
            n_dat = int(df[f"{b}_t3"].notna().sum())
            sw = f'<span class="sw" style="background:{LEVEL_COLOURS["High"]};border:1px solid #cfcdc6"></span>'
            c.markdown(f'<div class="kpi"><div class="n">{n_hi:,}</div><div class="l">{sw}{BUSINESSES[b]["icon"]} '
                       f'{BUSINESSES[b]["name"]}: High<br><span style="opacity:.75">of {n_dat:,} mandals scored</span>'
                       f'</div></div>', unsafe_allow_html=True)
        st.caption(f"High = top third of the mandals each team scored. {int((df['b_high'] == 4).sum()):,} mandals are "
                   "High on all four. Pick a business area in the sidebar for its High / Medium / Low split.")
    elif scope == "all":
        # Opening view: one figure per pillar, so no single pillar dominates the header
        cols = st.columns(5)
        n_any = int((df["n_data"] > 0).sum())
        cols[0].markdown(f'<div class="kpi"><div class="n">{len(df):,}</div><div class="l">Mandals in total<br>'
                         f'<span style="opacity:.75">{n_any:,} analysed on at least 1 pillar · '
                         f'{int((df["n_data"] == 4).sum()):,} on all 4</span></div></div>', unsafe_allow_html=True)
        for c, p in zip(cols[1:], PK):
            n_hi = int((df[f"{p}_t3"] == "High").sum())
            n_dat = int(df[f"{p}_t3"].notna().sum())
            sw = f'<span class="sw" style="background:{LEVEL_COLOURS["High"]};border:1px solid #cfcdc6"></span>'
            c.markdown(f'<div class="kpi"><div class="n">{n_hi:,}</div><div class="l">{sw}{PILLARS[p]["icon"]} '
                       f'{PILLARS[p]["name"]}: High<br><span style="opacity:.75">of {n_dat:,} mandals with data</span>'
                       f'</div></div>', unsafe_allow_html=True)
        st.caption(f"High = top third of mandals with data on that pillar (Connectivity included, so the four compare "
                   f"like with like). {int((df['n_high'] == 4).sum()):,} mandals are High on all four. "
                   f"Pick a pillar in the sidebar for its High / Medium / Low split.")
    else:
        cols = st.columns(5)
        tiles = [(f"{len(scored):,}", f"Mandals with data (of {len(df)})", None)] + \
                [(f"{cnt.get(lv, 0):,}", lv if not (view == "team" and layer == "con") else
                  {"High": "Well connected", "Medium": "Average", "Low": "Poorly connected"}[lv], LEVEL_COLOURS[lv])
                 for lv in ["High", "Medium", "Low"]] + [(f"{len(df) - len(scored):,}", "No data (grey)", NO_DATA)]
        for c, (n, l, colr) in zip(cols, tiles):
            sw = f'<span class="sw" style="background:{colr};border:1px solid #cfcdc6"></span>' if colr else ""
            c.markdown(f'<div class="kpi"><div class="n">{n}</div><div class="l">{sw}{l}</div></div>',
                       unsafe_allow_html=True)
        st.caption(META.get("level_rule", "Levels are thirds of the scored mandals: top third High, middle Medium, bottom Low."))

    tabs = st.tabs(["🗺️  Map and mandal profile", "⚖️  Compare mandals", "📋  All mandals", "🧭  Regions",
                    "ℹ️  About and limitations"])


# ════════════════════════════════════════════════════════════════════════════
# 5. MAP
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data
def district_label_points():
    """District name positions, precomputed inside each district (data/district_labels.csv).
    Long names are split over two lines so they don't run into neighbouring districts."""
    lab = pd.read_csv(DATA / "district_labels.csv")
    short = {"Dr.B.R.Ambedkar Konaseema": "Konaseema", "Sri Potti Sriramulu Nellore": "Nellore",
             "Alluri Sitharama Raju": "Alluri Sitharama<br>Raju", "Parvathipuram Manyam": "Parvathipuram<br>Manyam"}
    lab["text"] = lab["district"].map(lambda n: short.get(n, n))
    return lab


@st.cache_data
def mandal_label_points():
    return pd.read_csv(DATA / "mandal_labels.csv").set_index("mandal_lgd")


# Map text: dark, semi-bold, with a white halo so it stays readable over any colour
HALO = "1px 1px 2px #fff, -1px -1px 2px #fff, 1px -1px 2px #fff, -1px 1px 2px #fff, 0 0 3px #fff"
DIST_FONT = dict(size=12, color="#1d1c1a", weight=600, shadow=HALO)
SEL_FONT = dict(size=13, color="#000", weight=700, shadow=HALO)


def mandal_name_trace(lgd, name):
    """The selected mandal's name, written on the map next to its outline."""
    pt = mandal_label_points().loc[int(lgd)]
    return go.Scattergeo(lon=[pt["lab_lon"]], lat=[pt["lab_lat"]], text=[name], mode="text", textfont=SEL_FONT,
                         textposition="top center", hoverinfo="skip", showlegend=False)


def district_lines(sel):
    lons, lats = [], []
    for f in DISTRICT_GEO["features"]:
        if sel and f["properties"]["district_name"] not in sel:
            continue
        g = f["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            ring = np.array(poly[0])
            lons += ring[:, 0].tolist() + [None]
            lats += ring[:, 1].tolist() + [None]
    return lons, lats


def nodata_reason(r):
    if view == "team" and layer == "wat" and isinstance(r.get("wat_exclusion_reason"), str):
        return "Not scored: " + r["wat_exclusion_reason"]
    return META["nodata"]


def hover(d):
    out = []
    for _, r in d.iterrows():
        t = f"<b>{r['mandal_name']}</b><br>{r['district_name']} district<br>"
        if scope == "all":
            out.append(t + strong_line(r, BIZ))
            continue
        if pd.isna(r["cur_score"]):
            t += f"<i>{nodata_reason(r)}</i>"
        else:
            t += (f"{META['score_label']}: <b>{fmt_score(META['score_kind'], r['cur_score'])}</b> "
                  f"(rank {int(r['cur_rk'])} of {N_CUR})<br>Level: <b>{r['cur_lvl']}</b>")
            if RG and isinstance(r[RG], str):
                t += f"<br>{'Zone' if BIZ else 'Region'}: {r[RG].replace('Zone ', '', 1) if BIZ else r[RG]}"
            if BIZ and r["cur_rk"] <= 15:
                t += "<br>★ Top 15 pilot mandal"
            if colour_by == "dlevel" and isinstance(r["cur_dlvl"], str):
                t += f"<br>Within {r['district_name']}: <b>{r['cur_dlvl']}</b>"
        out.append(t)
    return out


def build_map(d):
    fig, trace_lgd = go.Figure(), []
    common = dict(geojson=MANDAL_GEO, featureidkey="properties.mandal_lgd", marker_line_color="white",
                  marker_line_width=0.35, hoverinfo="text")

    def cat(sub, colour, name):
        if sub.empty:
            return
        fig.add_trace(go.Choropleth(locations=sub["mandal_lgd"], z=np.ones(len(sub)), text=hover(sub),
                                    colorscale=[[0, colour], [1, colour]], showscale=False, name=name,
                                    showlegend=True, **common))
        trace_lgd.append(sub["mandal_lgd"].tolist())

    nod = d[d["cur_score"].isna()]
    has = d[d["cur_score"].notna()]
    con_names = {"High": "Well connected", "Medium": "Average", "Low": "Poorly connected"}
    names = con_names if (view == "team" and layer == "con") else {k: k for k in LEVEL_COLOURS}

    def shade(sub, z, scale, title, extra=None, zmax=100):
        if sub.empty:
            return
        txt = hover(sub)
        if extra is not None:
            txt = [a + b for a, b in zip(txt, extra)]
        fig.add_trace(go.Choropleth(
            locations=sub["mandal_lgd"], z=z, text=txt, colorscale=scale, zmin=0, zmax=zmax, showlegend=False,
            colorbar=dict(title=dict(text=title, font=dict(size=11)), thickness=12, len=0.55, x=0.99, y=0.5,
                          outlinewidth=0, tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=11)), **common))
        trace_lgd.append(sub["mandal_lgd"].tolist())

    BLUE = [[0, "#eef4fc"], [0.5, "#5598e7"], [1, "#0d366b"]]
    if colour_by == "level":
        for lv in ["High", "Medium", "Low"]:
            cat(d[d["cur_lvl"] == lv], LEVEL_COLOURS[lv], names[lv])
        cat(nod, NO_DATA, "No data")
    elif colour_by == "dlevel":
        for lv in ["High", "Medium", "Low"]:
            cat(d[d["cur_dlvl"] == lv], LEVEL_COLOURS[lv], f"{lv} in its district")
        cat(nod, NO_DATA, "No data")
    elif colour_by == "measure":
        col, lbl, kind = LAYERS[layer]["measures"][measure_pick]
        cat(d[d[f"{layer}_{col}"].isna()], NO_DATA, "No data")
        sub = d[d[f"{layer}_{col}"].notna()]
        shade(sub, sub[f"{layer}_{col}_pct"], BLUE, "Percentile<br>(higher =<br>more)",
              [f"<br><b>{lbl}: {fmt_measure(kind, v, c and col == 'C5')}</b>"
               for v, c in zip(sub[f"{layer}_{col}"], sub["con_city"])])
    elif colour_by == "nhigh":
        steps = {4: "#0d366b", 3: "#2a6fc4", 2: "#6da7ec", 1: "#b7d3f6", 0: "#eef4fc"}
        for n_, c_ in steps.items():
            cat(d[(d["n_high"] == n_) & (d["n_data"] > 0)], c_, strong_label(n_, False))
        cat(d[d["n_data"] == 0], NO_DATA, "Data not available")
    elif colour_by == "best":
        BEST = {"Water": "#2a78d6", "Electricity": "#eda100", "Connectivity": "#1f9e89",
                "Market access": "#8a5cc4", "Not strong on any pillar": "#ece9e2"}
        for w_, c_ in BEST.items():
            cat(d[d["best"] == w_], c_, w_ if w_.startswith("No") else f"Strongest: {w_}")
        cat(d[d["best"].isna()], NO_DATA, "No data")
    elif colour_by == "bbest":
        BB = {"Agriculture": "#3f8f29", "Livestock": "#9a5b1e", "Rural Services": "#8a5cc4",
              "Aquaculture": "#1f9ec4", "Not strong in any business area": "#c9c2ae"}
        for w_, c_ in BB.items():
            cat(d[d["bbest"] == w_], c_, w_ if w_.startswith("No") else f"Strongest: {w_}")
        cat(d[d["bbest"].isna()], NO_DATA, "Data not available")
    elif colour_by == "bnhigh":
        steps = {4: "#0d366b", 3: "#2a6fc4", 2: "#6da7ec", 1: "#b7d3f6", 0: "#eef4fc"}
        for n_, c_ in steps.items():
            cat(d[(d["b_high"] == n_) & (d["b_data"] > 0)], c_, strong_label(n_, True))
        cat(d[d["b_data"] == 0], NO_DATA, "Data not available")
    elif colour_by == "weak":
        WEAK = {"Water": "#2a78d6", "Electricity": "#eda100", "Connectivity": "#eb6834",
                "Market access": "#8a5cc4", "No bottleneck": "#cde8d6"}
        for w_, c_ in WEAK.items():
            cat(d[d["weak"] == w_], c_, w_ if w_ == "No bottleneck" else f"Weakest: {w_}")
        cat(d[d["weak"].isna()], NO_DATA, "No data")
    elif colour_by == "cover":
        steps = {4: "#3d3a33", 3: "#7d786c", 2: "#b3ad9f", 1: "#d9d4c7", 0: "#f4f3ef"}
        for n_, c_ in steps.items():
            cat(d[d["n_data"] == n_], c_, f"{n_} of 4 pillars with data")
    else:
        cat(nod, NO_DATA, "No data")
        shade(has, has["cur_pct"], [[0, "#fdf3e1"], [0.5, "#e3a008"], [1, "#6b3f00"]] if view == "draft" else BLUE,
              "Percentile<br>(higher =<br>better)")

    lons, lats = district_lines(districts)
    fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode="lines", line=dict(color="#4a4843", width=0.8),
                                hoverinfo="skip", showlegend=False))
    trace_lgd.append([])
    if BIZ and scope == "one":
        top = d[d["cur_rk"] <= 15]
        if not top.empty:
            pts = mandal_label_points().loc[top["mandal_lgd"].astype(int)]
            fig.add_trace(go.Scattergeo(lon=pts["lab_lon"], lat=pts["lab_lat"], mode="markers",
                                        marker=dict(symbol="star", size=13, color="#ffd23f",
                                                    line=dict(color="#3b2f00", width=1)),
                                        text=hover(top), hoverinfo="text", name="Top 15 pilot mandals"))
            trace_lgd.append(top["mandal_lgd"].tolist())
    lab = district_label_points()
    if districts:
        lab = lab[lab["district"].isin(districts)]
    fig.add_trace(go.Scattergeo(lon=lab["lon"], lat=lab["lat"], text=lab["text"], mode="text",
                                textfont=DIST_FONT, hoverinfo="skip", showlegend=False))
    trace_lgd.append([])
    sel = d[d["mandal_lgd"] == st.session_state.mandal_lgd]
    if not sel.empty:
        fig.add_trace(go.Choropleth(locations=sel["mandal_lgd"], z=[1], geojson=MANDAL_GEO,
                                    featureidkey="properties.mandal_lgd",
                                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                                    marker_line_color="#111", marker_line_width=2.2, showscale=False,
                                    hoverinfo="skip", showlegend=False))
        trace_lgd.append([])
        fig.add_trace(mandal_name_trace(sel["mandal_lgd"].iloc[0], sel["mandal_name"].iloc[0]))
        trace_lgd.append([])
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      legend=dict(x=0.01, y=0.99, xanchor="left", yanchor="top", bgcolor="rgba(255,255,255,0.9)",
                                  bordercolor="#e3e1da", borderwidth=1, font=dict(size=12)),
                      hoverlabel=dict(bgcolor="white", font=dict(size=13, color="#22211f"), bordercolor="#cfcdc6"))
    return fig, trace_lgd


MAP_CONFIG = {"displayModeBar": False, "scrollZoom": False}
if st.get_option("server.enableStaticServing"):
    MAP_CONFIG["topojsonURL"] = "app/static/"



# ════════════════════════════════════════════════════════════════════════════
# OPENING OVERVIEW: infrastructure and business opportunity side by side
# ════════════════════════════════════════════════════════════════════════════
def overview_fig(groups, hover_txt, caption, height=440):
    fig = go.Figure()
    for sub, colour, name in groups:
        if sub.empty:
            continue
        fig.add_trace(go.Choropleth(locations=sub["mandal_lgd"], z=np.ones(len(sub)), hoverinfo="skip",  # no hover box
                                    geojson=MANDAL_GEO, featureidkey="properties.mandal_lgd",
                                    colorscale=[[0, colour], [1, colour]], showscale=False, name=name, showlegend=True,
                                    marker_line_color="white", marker_line_width=0.35))
    lons, lats = district_lines(districts)
    fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode="lines", line=dict(color="#4a4843", width=0.8),
                                hoverinfo="skip", showlegend=False))
    lab = district_label_points()
    if districts:
        lab = lab[lab["district"].isin(districts)]
    fig.add_trace(go.Scattergeo(lon=lab["lon"], lat=lab["lat"], text=lab["text"], mode="text",
                                textfont=dict(DIST_FONT, size=10), hoverinfo="skip", showlegend=False))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      legend=dict(x=0.01, y=0.99, xanchor="left", yanchor="top", bgcolor="rgba(255,255,255,0.9)",
                                  bordercolor="#e3e1da", borderwidth=1, font=dict(size=12)),
                      hoverlabel=dict(bgcolor="white", font=dict(size=13, color="#22211f"), bordercolor="#cfcdc6"),
                      # The caption sits inside the map's frame, in the empty bottom-right corner next to the coast
                      annotations=[dict(text=caption, x=0.99, y=0.03, xref="paper", yref="paper", xanchor="right",
                                        yanchor="bottom", showarrow=False, align="right",
                                        font=dict(size=15, color="#22211f"))])
    return fig


def _hov_infra(d):
    return [f"<b>{r['mandal_name']}</b><br>{r['district_name']} district<br>{strong_line(r, False)}"
            for _, r in d.iterrows()]


def _hov_biz(d):
    return [f"<b>{r['mandal_name']}</b><br>{r['district_name']} district<br>{strong_line(r, True)}"
            for _, r in d.iterrows()]


if section == "Overview":
    st.markdown('<div class="eyebrow">Entrepreneurial Opportunity Zones · Andhra Pradesh · mandal level</div>',
                unsafe_allow_html=True)
    st.markdown("## Andhra Pradesh")
    st.markdown("#### Infrastructure & Business Opportunity Overview")
    st.caption(f"{', '.join(districts) if districts else 'All of Andhra Pradesh'} · Left: each mandal's strongest "
               "infrastructure pillar. Right: each mandal's strongest business opportunity. Pick a Section in the "
               "sidebar to explore one in depth.")
    L, R = st.columns(2, gap="large")
    with L:
        chips = "".join(f'<span class="chip"><b>{int((df[f"{p}_t3"] == "High").sum())}</b> {PILLARS[p]["icon"]} '
                        f'{PILLARS[p]["name"]}</span>' for p in PK)
        st.markdown(f'<div class="chips"><span class="chip"><b>{len(df):,}</b> mandals</span>{chips}'
                    '<span class="sm">at High</span></div>', unsafe_allow_html=True)
        BP = {"Water": "#2a78d6", "Electricity": "#eda100", "Connectivity": "#1f9e89", "Market access": "#8a5cc4",
              "Not strong on any pillar": "#ece9e2"}
        g = [(df[df["best"] == w], c, w if w.startswith("No") else f"Strongest: {w}") for w, c in BP.items()] + \
            [(df[df["best"].isna()], NO_DATA, "No data")]
        st.plotly_chart(overview_fig(g, _hov_infra, "🏗️ <b>Infrastructure Overview</b><br>strongest pillar"),
                        use_container_width=True, config=MAP_CONFIG, key="ov_infra")
    with R:
        chips = "".join(f'<span class="chip"><b>{int((df[f"{b}_t3"] == "High").sum())}</b> {BUSINESSES[b]["icon"]} '
                        f'{BUSINESSES[b]["name"]}</span>' for b in BK)
        st.markdown(f'<div class="chips"><span class="chip"><b>{int((df["b_data"] > 0).sum()):,}</b> scored</span>'
                    f'{chips}<span class="sm">at High</span></div>', unsafe_allow_html=True)
        BB = {"Agriculture": "#3f8f29", "Livestock": "#9a5b1e", "Rural Services": "#c2477a", "Aquaculture": "#1f9ec4",
              "Not strong in any business area": "#c9c2ae"}
        g = [(df[df["bbest"] == w], c, w if w.startswith("No") else f"Strongest: {w}") for w, c in BB.items()] + \
            [(df[df["bbest"].isna()], NO_DATA, "Data not available")]
        st.plotly_chart(overview_fig(g, _hov_biz, "💼 <b>Business Opportunity Overview</b><br>strongest business area"),
                        use_container_width=True, config=MAP_CONFIG, key="ov_biz")
    st.caption("Strongest = the pillar (or business) where the mandal is in the top third and scores highest. "
               "Grey = no data, never a low score. The business map covers the 323 mandals in the teams' opportunity "
               "models (all four pillars needed), so the south is grey there.")
    st.stop()




def pillar_card(r, p, selected):
    v = PILLARS[p]
    lvl, pct = r[f"{p}_lvl"], r[f"{p}_pct"]
    if not isinstance(lvl, str):
        body = '<span class="lv" style="background:#e4e2dc;color:#55534d">No data</span>'
        bar, sub = "", "Not the same as a low score"
    else:
        lab = r["con_level"] if p == "con" else lvl
        body = (f'<span class="lv" style="background:{LEVEL_COLOURS[lvl]};color:{LEVEL_TEXT[lvl]}">{lab}</span>')
        bar = (f'<div class="bar"><div style="width:{pct:.0f}%;background:{LEVEL_COLOURS[lvl]}"></div></div>')
        sub = (f"Score {fmt_score(v['score_kind'], r[f'{p}_score'])} · rank {int(r[f'{p}_rk'])} of {N[p]} · "
               f"percentile {pct:.0f}")
    return (f'<div class="pc{" sel" if selected else ""}"><div class="t">{v["icon"]} <b>{v["name"]}</b></div>'
            f'{body}{bar}<div class="s">{sub}</div></div>')


NEED_RANK = {"High": 3, "Medium/High": 2.5, "Medium": 2, "Low/Medium": 1.5, "Low": 1}
RESULT = {"meets": ("✓", "Meets", "#14632d"), "partly": ("~", "Partly", "#7a5000"),
          "gap": ("✗", "Gap", "#a3241a"), "unknown": ("?", "Unknown", "#55534d")}


def pillar_check(need, have):
    """Agreed rule. Needed High (Medium/High counts as High): High meets, Medium partly, Low gap.
    Needed Medium: High or Medium meets, Low partly. Needed Low: any level meets. No data: unknown."""
    if not isinstance(have, str):
        return "unknown"
    n = NEED_RANK[need]
    if n >= 2.5:
        return {"High": "meets", "Medium": "partly", "Low": "gap"}[have]
    if n >= 1.5:
        return {"High": "meets", "Medium": "meets", "Low": "partly"}[have]
    return "meets"


def infra_verdict(r, b):
    res = {p: pillar_check(DRAFT[b]["w"][p], r[f"{p}_lvl"]) for p in PK}
    gaps = sum(v == "gap" for v in res.values())
    unknown = sum(v == "unknown" for v in res.values())
    verdict = "Suitable" if gaps == 0 else "Partly suitable" if gaps == 1 else "Not suitable"
    return verdict, gaps, unknown, res


VERDICT_STYLE = {"Suitable": ("✓", "#d8f0de", "#14532d"), "Partly suitable": ("~", "#fdf0c8", "#6b4a00"),
                 "Not suitable": ("✗", "#fadbd8", "#7f1d1d")}
LEVEL_BADGE = {"High": ("#dbe8fb", "#0d366b"), "Medium": ("#ecebe7", "#3b3a36"), "Low": ("#fadbd8", "#7f1d1d")}


def badge(text, bg, fg):
    return f'<span class="bdg" style="background:{bg};color:{fg}">{text}</span>'


def verdict_badge(v):
    ic, bg, fg = VERDICT_STYLE[v]
    return badge(f"{ic} {v}", bg, fg)


def suitability_band(r, b):
    """Under the map: infrastructure check (left) and the team's opportunity score (right), side by side."""
    v = BUSINESSES[b]
    verdict, gaps, unknown, res = infra_verdict(r, b)
    rows = []
    for p in PK:
        have = r[f"{p}_lvl"]
        shown = (r["con_level"] if p == "con" else have) if isinstance(have, str) else "No data"
        ic, word, col = RESULT[res[p]]
        rows.append(f'<tr><td>{PILLARS[p]["name"]}</td><td>{DRAFT[b]["w"][p]}</td><td>{shown}</td>'
                    f'<td style="color:{col};font-weight:700">{ic} {word}</td></tr>')
    left_html = (
        '<div class="sbox"><div class="sh">① Infrastructure check</div>'
        f'<div class="sl">{verdict_badge(verdict)} <span class="sm">{gaps} gap{"s" if gaps != 1 else ""}'
        + (f", {unknown} unknown" if unknown else "") + '</span></div>'
        '<table class="st"><thead><tr><th scope="col">Pillar</th><th scope="col">Needs</th><th scope="col">Has</th>'
        '<th scope="col">Result</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
        f'<div class="sm" style="margin-top:.45rem">What the business needs: {DRAFT[b]["src"]} (not validated '
        'with SERP).</div></div>')
    if pd.notna(r[f"{b}_score"]):
        zone_no = int(r[f"{b}_zone_no"])
        ideas, support = ZONE_INFO[b][zone_no]
        lbg, lfg = LEVEL_BADGE[r[f"{b}_lvl"]]
        rank = int(r[f"{b}_rk"])
        right_html = (
            '<div class="sbox"><div class="sh">② Opportunity score <span class="sm">(team\'s model)</span></div>'
            f'<div class="sl"><span class="big">{r[f"{b}_score"]:.0f}</span><span class="sm"> / 100 · rank {rank} '
            f'of {N[b]}</span> {badge(r[f"{b}_lvl"], lbg, lfg)}'
            + (f' {badge("★ Top 15 pilot mandal", "#fff3c4", "#5c4400")}' if rank <= 15 else "") + '</div>'
            f'<div class="kv"><b>Zone {zone_no}:</b> {r[f"{b}_zone"].split(": ", 1)[-1]}</div>'
            f'<div class="kv"><b>Possible SHG enterprises:</b> {ideas}</div>'
            f'<div class="kv"><b>Support range:</b> {support}</div>'
            f'<div class="sm" style="margin-top:.45rem">{v["score_help"]} Source: {v["source"]}.</div></div>')
    else:
        right_html = ('<div class="sbox"><div class="sh">② Opportunity score <span class="sm">(team\'s model)</span>'
                      f'</div><div class="kv" style="margin-top:.45rem">{_OPP_NODATA}</div></div>')
    st.markdown(f'<div class="sq">Is <b>{r["mandal_name"]}</b> suitable for <b>{v["name"]}</b>?</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    c1.markdown(left_html, unsafe_allow_html=True)
    c2.markdown(right_html, unsafe_allow_html=True)


def all_business_lines(r):
    """No business picked: one line per business area, strongest first."""
    rows = []
    for b in BK:
        verdict, gaps, unknown, _ = infra_verdict(r, b)
        has = pd.notna(r[f"{b}_score"])
        lv_ = r[f"{b}_lvl"] if has else None
        opp = (f'{r[f"{b}_score"]:.0f} / 100 {badge(lv_, *LEVEL_BADGE[lv_])}'
               + (f' {badge("★ Top 15", "#fff3c4", "#5c4400")}' if r[f"{b}_rk"] <= 15 else "")) if has \
            else '<span class="sm">Not in the team\'s model</span>'
        zone = r[f"{b}_zone"].split(": ", 1)[-1] if has else "—"
        key = ({"High": 0, "Medium": 1, "Low": 2}.get(lv_, 3), -(r[f"{b}_score"] if has else -1))
        rows.append((key, f'<tr><td><b>{BUSINESSES[b]["icon"]} {BUSINESSES[b]["name"]}</b></td>'
                          f'<td>{verdict_badge(verdict)}</td><td>{opp}</td><td>{zone}</td></tr>'))
    rows.sort(key=lambda x: x[0])
    st.markdown(f'<div class="sq">Which business areas suit <b>{r["mandal_name"]}</b>?</div>', unsafe_allow_html=True)
    st.markdown('<div class="sbox"><table class="st"><thead><tr><th scope="col">Business area</th>'
                '<th scope="col">① Infrastructure check</th><th scope="col">② Opportunity score</th>'
                '<th scope="col">Zone</th></tr></thead><tbody>' + "".join(x[1] for x in rows) + '</tbody></table>'
                '<div class="sm" style="margin-top:.45rem">Strongest first. Pick a business area in the sidebar for '
                'the full explanation, possible SHG enterprises and support range.</div></div>',
                unsafe_allow_html=True)


def profile(lgd):
    r = DF[DF["mandal_lgd"] == lgd].iloc[0]
    st.markdown(f'<div class="eyebrow">{r["district_name"]} district · {r["revenue_division"]} division · '
                f'LGD {int(lgd)}</div><h3 style="margin:.1rem 0 .5rem 0">{r["mandal_name"]}</h3>',
                unsafe_allow_html=True)
    st.markdown("**Performance across the four pillars**")
    c1, c2 = st.columns(2)
    for i, p in enumerate(PK):
        (c1 if i % 2 == 0 else c2).markdown(pillar_card(r, p, section == "Infrastructure pillars" and scope == "one" and p == layer),
                                            unsafe_allow_html=True)
    n_low = sum(r[f"{p}_lvl"] == "Low" for p in PK)
    n_high = sum(r[f"{p}_lvl"] == "High" for p in PK)
    n_nd = sum(not isinstance(r[f"{p}_lvl"], str) for p in PK)
    st.caption(f"High on {n_high}, Low on {n_low}" + (f", no data on {n_nd}" if n_nd else "") + " of 4 pillars.")

    if scope == "all":
        st.caption("Pick a business area in the sidebar to see its details for this mandal." if BIZ else
                   "Pick a pillar under **Pillar on the map** to see that pillar's measures for this mandal.")
    else:
        from contextlib import nullcontext
        # Business areas: the details fold away so the suitability answer sits right under the map
        holder = st.expander(f"{BUSINESSES[layer]['name']}: score details and business activity measures") \
            if BIZ else nullcontext()
        holder.__enter__()
        if not BIZ:
            st.markdown(f"**{PILLARS[layer]['name']}: details**")
        if pd.isna(r["cur_score"]):
            st.markdown(f'<div class="note">{nodata_reason(r)}</div>', unsafe_allow_html=True)
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Score", fmt_score(META["score_kind"], r["cur_score"]), help=META["score_help"])
            m2.metric("Rank", f"{int(r['cur_rk'])} of {N_CUR}")
            m3.metric("Level", r["cur_lvl"], help=META.get("level_rule", "Thirds of the scored mandals."))
            if RG and isinstance(r[RG], str):
                st.markdown(f'<div class="muted">{"Opportunity zone" if BIZ else "Region"}: <b>{r[RG]}</b></div>',
                            unsafe_allow_html=True)
            if META["measures"]:
                mt = pd.DataFrame([{"Measure": lbl,
                                    "Value": fmt_measure(kind, r[f"{layer}_{col}"], r["con_city"] and col == "C5"),
                                    "Percentile": None if pd.isna(r[f"{layer}_{col}_pct"]) else round(r[f"{layer}_{col}_pct"])}
                                   for col, lbl, kind in META["measures"]])
                st.dataframe(mt, hide_index=True, use_container_width=True,
                             column_config={"Percentile": st.column_config.ProgressColumn(min_value=0, max_value=100,
                                                                                          format="%d")})
        if BIZ and pd.isna(r["cur_score"]) and META["measures"]:
            # Outside the opportunity model, the business team's own measures may still exist
            mt = pd.DataFrame([{"Measure": lbl, "Value": fmt_measure(kind, r[f"{layer}_{col}"]),
                                "Percentile": None if pd.isna(r[f"{layer}_{col}_pct"]) else round(r[f"{layer}_{col}_pct"])}
                               for col, lbl, kind in META["measures"]])
            st.dataframe(mt, hide_index=True, use_container_width=True,
                         column_config={"Percentile": st.column_config.ProgressColumn(min_value=0, max_value=100,
                                                                                      format="%d")})
        if layer == "con" and r["con_city"]:
            st.markdown('<div class="note">City mandal: village access and bus service assumed 100%; road condition '
                        '(*) is the district median.</div>', unsafe_allow_html=True)
        holder.__exit__(None, None, None)

    if BIZ:
        return
    with st.expander("Recommended Business Areas for this Mandal"):
        rows = []
        order = {"High": 0, "Medium": 1, "Low": 2}
        for b, v in BUSINESSES.items():
            lv_ = r[f"{b}_lvl"]
            verdict = infra_verdict(r, b)[0]
            rows.append({"Business": ("★ " if lv_ == "High" else "") + v["name"],
                         "Opportunity level": lvl(lv_),
                         "Opportunity score": fmt_score("0-100", r[f"{b}_score"]),
                         "Infrastructure check": verdict,
                         "_o": order.get(lv_, 3), "_p": -(r[f"{b}_pct"] if pd.notna(r[f"{b}_pct"]) else -1)})
        tb = pd.DataFrame(rows).sort_values(["_o", "_p"]).drop(columns=["_o", "_p"])
        st.dataframe(tb, hide_index=True, use_container_width=True)
        st.caption("Sorted from the strongest level down. ★ = High (top third) on the team's opportunity score. "
                   "Pick Business areas in the sidebar for the full explanation.")


def clicked_lgd(ev, tl):
    pts = getattr(getattr(ev, "selection", None), "points", None) or \
        ((ev or {}).get("selection", {}).get("points", []) if isinstance(ev, dict) else [])
    if not pts:
        return None
    p = pts[0]
    lgd = p.get("location")
    if lgd is None:
        try:
            lgd = tl[p["curve_number"]][p["point_index"]]
        except (KeyError, IndexError, TypeError):
            lgd = None
    return lgd


def small_map(d, p, dist, legend=False):
    """One pillar's levels for the selected mandal's district, in the same colours as the profile cards.
    legend=True draws the one shared legend (used on the top-left map only)."""
    fig, tl = go.Figure(), []
    names = ({"High": "Well connected", "Medium": "Average", "Low": "Poorly connected"} if p == "con"
             else {k: k for k in LEVEL_COLOURS})
    groups = [(d[d[f"{p}_lvl"] == lv], LEVEL_COLOURS[lv], names[lv]) for lv in ["High", "Medium", "Low"]] + \
             [(d[d[f"{p}_lvl"].isna()], NO_DATA, "No data")]
    for sub, colour, nm in groups:
        if sub.empty:
            continue
        txt = [f"<b>{r['mandal_name']}</b><br>{PILLARS[p]['name']}: <b>{nm}</b>"
               + ("" if pd.isna(r[f"{p}_score"]) else
                  f"<br>Score {fmt_score(PILLARS[p]['score_kind'], r[f'{p}_score'])} · rank {int(r[f'{p}_rk'])} of {N[p]}")
               for _, r in sub.iterrows()]
        fig.add_trace(go.Choropleth(locations=sub["mandal_lgd"], z=np.ones(len(sub)), text=txt, hoverinfo="text",
                                    geojson=MANDAL_GEO, featureidkey="properties.mandal_lgd",
                                    colorscale=[[0, colour], [1, colour]], showscale=False, showlegend=False,
                                    marker_line_color="white", marker_line_width=0.6))
        tl.append(sub["mandal_lgd"].tolist())
    lons, lats = district_lines([dist])
    fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode="lines", line=dict(color="#6b6862", width=0.8),
                                hoverinfo="skip", showlegend=False))
    tl.append([])
    sel = d[d["mandal_lgd"] == st.session_state.mandal_lgd]
    if not sel.empty:
        fig.add_trace(go.Choropleth(locations=sel["mandal_lgd"], z=[1], geojson=MANDAL_GEO,
                                    featureidkey="properties.mandal_lgd",
                                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                                    marker_line_color="#111", marker_line_width=3, showscale=False,
                                    hoverinfo="skip", showlegend=False))
        tl.append([])
        fig.add_trace(mandal_name_trace(sel["mandal_lgd"].iloc[0], sel["mandal_name"].iloc[0]))
        tl.append([])
    if legend:
        # One legend for all four maps: every level always listed, whatever this district contains
        for lab, colour in [("High / Well connected", LEVEL_COLOURS["High"]),
                            ("Medium / Average", LEVEL_COLOURS["Medium"]),
                            ("Low / Poorly connected", LEVEL_COLOURS["Low"]), ("No data", NO_DATA)]:
            fig.add_trace(go.Scattergeo(lon=[None], lat=[None], mode="markers", name=lab, showlegend=True,
                                        hoverinfo="skip", marker=dict(symbol="square", size=11, color=colour,
                                                                      line=dict(color="#cfcdc6", width=1))))
            tl.append([])
    # The legend sits in a strip on the left of the top-left map so it never covers a mandal
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)",
                    domain=dict(x=[0.34, 1] if legend else [0, 1], y=[0, 1]))
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      showlegend=legend,
                      legend=dict(x=0, y=0.02, xanchor="left", yanchor="bottom", bgcolor="rgba(255,255,255,0.9)",
                                  bordercolor="#e3e1da", borderwidth=1, font=dict(size=11),
                                  itemclick=False, itemdoubleclick=False),
                      hoverlabel=dict(bgcolor="white", font=dict(size=13, color="#22211f"), bordercolor="#cfcdc6"))
    return fig, tl


with tabs[0]:
    left, right = st.columns([1.5, 1], gap="large")
    sel_lgd = st.session_state.mandal_lgd
    four_view = sel_lgd is not None and section == "Infrastructure pillars"
    with left:
        if four_view:
            r0 = DF[DF["mandal_lgd"] == sel_lgd].iloc[0]
            dist = r0["district_name"]
            h1, h2 = st.columns([2.3, 1.7])
            h1.markdown(f"**{r0['mandal_name']} across the four pillars** · {dist} district")
            if h2.button("↩ Back to the state map", use_container_width=True):
                select_mandal(None)
            dd = DF[DF["district_name"] == dist]
            # One legend for all four maps, in the top-left corner, beside the grid so the maps stay equal in size
            lcol, gcol = st.columns([0.24, 1], gap="small")
            items = "".join(
                f'<div style="margin:3px 0"><span class="sw" style="background:{c};border:1px solid #cfcdc6"></span>{n}</div>'
                for n, c in [("High", LEVEL_COLOURS["High"]), ("Medium", LEVEL_COLOURS["Medium"]),
                             ("Low", LEVEL_COLOURS["Low"]), ("No data", NO_DATA)])
            lcol.markdown('<div style="margin-top:2.2rem;padding:6px 8px;background:#fff;border:1px solid #e3e1da;'
                          f'font-size:12px;line-height:1.3">{items}<div style="margin-top:6px;color:#6b6862;'
                          'font-size:11px">Connectivity: High = Well connected, Medium = Average, Low = Poorly '
                          'connected</div></div>', unsafe_allow_html=True)
            for row in (PK[:2], PK[2:]):
                cols_ = gcol.columns(2)
                for c_, p in zip(cols_, row):
                    with c_:
                        st.markdown(f"**{PILLARS[p]['icon']} {PILLARS[p]['name']}**")
                        f_, tl_ = small_map(dd, p, dist)
                        ev_ = st.plotly_chart(f_, use_container_width=True, on_select="rerun", selection_mode="points",
                                              key=f"four_{p}_{st.session_state.map_ver}", config=MAP_CONFIG)
                        lg = clicked_lgd(ev_, tl_)
                        if lg is not None and int(lg) != sel_lgd:
                            select_mandal(lg)
            st.caption(f"Each small map is one pillar for {dist} district, in the same colours as the profile cards "
                       "(one legend, top left, for all four). "
                       f"{r0['mandal_name']} is outlined in black. Click another mandal to switch to it.")
        else:
            if sel_lgd is not None:
                # What is selected, and the way back, above the map (same as the four-pillar view)
                r0 = DF[DF["mandal_lgd"] == sel_lgd].iloc[0]
                h1, h2 = st.columns([2.3, 1.7])
                h1.markdown(f"**{r0['mandal_name']}** · {r0['district_name']} district · outlined on the map")
                if h2.button("↩ Back to the state map", use_container_width=True, key="back_single"):
                    select_mandal(None)
            fig, trace_lgd = build_map(df)
            ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points",
                                 key=f"map_{st.session_state.map_ver}", config=MAP_CONFIG)
            lg = clicked_lgd(ev, trace_lgd)
            if lg is not None and int(lg) != sel_lgd:
                select_mandal(lg)
            MODE_NOTE = {
                "dlevel": "Each mandal compared only with mandals in its own district (top, middle, bottom third).",
                "best": "Each mandal is coloured by the pillar it scores highest on, among the pillars where it is in the "
                        "state's top third (High). Pale = High on no pillar. Many mandals are High on more than one "
                        "pillar; the map shows only the strongest one, and the profile shows all four.",
                "nhigh": "How many of the four pillars each mandal is strong on (top third of the state). Hover a mandal to "
                         "see which. Mandals missing a pillar can't reach 4.",
                "weak": "The pillar each mandal does worst on, among pillars in the bottom third. Light green = no bottleneck. Only pillars with data are compared.",
                "cover": "How many of the four pillars have data for each mandal. Darker = more complete.",
                "bbest": "Each mandal is coloured by the business area it scores highest on, among those where it is in "
                         "the top third (High) of the team's opportunity score. Taupe = High on none. Grey = data not "
                         "available (outside the 323 mandals the teams scored).",
                "bnhigh": "How many of the four business areas each mandal is strong in (top third of the opportunity "
                          "score). Hover to see which. Grey = data not "
                          "available (outside the 323 mandals the teams scored).",
            }
            if BIZ and scope == "one":
                MODE_NOTE["level"] = ("★ = the team's top 15 pilot mandals. Grey = outside the team's model "
                                      "(323 mandals with all four pillars), not a low score.")
            if colour_by in MODE_NOTE:
                st.caption(MODE_NOTE[colour_by])
            st.caption("Hover for details · **click a mandal** to "
                       + (("see which business areas suit it" if scope == "all" else "see whether it suits this business")
                          if BIZ else "see it on all four pillars")
                       + " · click a legend item to hide it.")
    with right:
        # In the four-pillar view the filter holds only the selected district; still let any mandal be searched
        opts = (DF if four_view else df).sort_values(["district_name", "mandal_name"])
        labels, lgds = opts["label"].tolist(), opts["mandal_lgd"].tolist()
        cur = lgds.index(sel_lgd) if sel_lgd in lgds else None
        chosen = st.selectbox("Find a mandal", labels, index=cur, placeholder="Type a mandal name…",
                              help="Type to search, or click a mandal on the map.",
                              key=f"find_{st.session_state.map_ver}")
        if chosen is not None and lgds[labels.index(chosen)] != sel_lgd:
            select_mandal(lgds[labels.index(chosen)])
        if sel_lgd is None:
            st.markdown('<div class="card"><h4>Select a mandal</h4>Click a mandal on the map or type its name above. '
                        + ("Its profile appears here, and under the map you will see whether it suits "
                           + ("this business area." if scope == "one" else "each business area.") if BIZ else
                           "The map will then show it on all four pillars, side by side, and its profile appears here.")
                        + '</div>', unsafe_allow_html=True)
        else:
            profile(sel_lgd)
    if sel_lgd is not None and BIZ:
        # Full width under the map, the two answers side by side
        _r = DF[DF["mandal_lgd"] == sel_lgd].iloc[0]
        if scope == "one":
            suitability_band(_r, layer)
        else:
            all_business_lines(_r)

# ════════════════════════════════════════════════════════════════════════════
# 6. COMPARE
# ════════════════════════════════════════════════════════════════════════════
# Two colour families so pillars and business areas are never confused: blues = pillars, oranges = business areas
P_COL = {"con": "#0d366b", "ele": "#2a6fc4", "wat": "#5598e7", "mkt": "#9ec5f4"}
B_COL = {"agr": "#7a3e00", "liv": "#c25e0a", "ser": "#ec9230", "aqu": "#f7c784"}
ROW_TINT = {"Infrastructure pillar": "#e8f0fb", "Business area": "#fdf0de"}

with tabs[1]:
    st.markdown("#### Compare up to five mandals")
    pool = DF.sort_values(["district_name", "mandal_name"])
    lab = dict(zip(pool["mandal_lgd"], pool["label"]))
    _sel = st.session_state.mandal_lgd
    default = ([_sel] if _sel is not None else []) + \
        [x for x in DF.sort_values("agr_rk")["mandal_lgd"] if x != _sel][:3 - (1 if _sel is not None else 0)]
    picked = st.multiselect("Mandals", pool["mandal_lgd"].tolist(), default=default, max_selections=5,
                            format_func=lambda x: lab.get(x, str(x)))
    cmode = st.radio("Compare on", ["Infrastructure pillars", "Business areas", "Choose my own"], horizontal=True,
                     index=1 if BIZ else 0, key="cmp_mode",
                     help="Pillars and business areas are compared separately. 'Choose my own' lets you pick from both; "
                          "pillars are then shown in blue and business areas in orange.")
    if cmode == "Infrastructure pillars":
        keys = list(PK)
    elif cmode == "Business areas":
        keys = list(BK)
    else:
        # All eight on one line, right under the radio: four pillars (blue) then four business areas (orange)
        g1, g2 = st.columns(2)
        g1.markdown("<div class='sm'><b style='color:#2a6fc4'>■ Infrastructure pillars</b></div>", unsafe_allow_html=True)
        g2.markdown("<div class='sm'><b style='color:#c25e0a'>■ Business areas</b></div>", unsafe_allow_html=True)
        cb = st.columns(8, gap="small")
        keys = [p for i, p in enumerate(PK) if cb[i].checkbox(PILLARS[p]["name"], value=p in ("con", "wat"), key=f"cmp_{p}")] + \
               [b for i, b in enumerate(BK) if cb[4 + i].checkbox(BUSINESSES[b]["name"], value=b in ("agr", "liv"), key=f"cmp_{b}")]
    if not picked:
        st.info("Pick at least one mandal to compare.")
    elif not keys:
        st.info("Tick at least one pillar or business area.")
    else:
        sub = DF.set_index("mandal_lgd").loc[picked]
        names = [lab[l].replace(" (", "<br>(") for l in picked]
        fig = go.Figure()
        for k in keys:
            isp = k in PILLARS
            v = LAYERS[k]
            fig.add_trace(go.Bar(
                x=names, y=[sub.loc[l, f"{k}_pct"] for l in picked], name=v["name"],
                marker_color=(P_COL if isp else B_COL)[k], marker_line_color="white", marker_line_width=1.5,
                legendgroup="p" if isp else "b",
                legendgrouptitle_text=("Infrastructure pillars" if isp else "Business areas (opportunity score)")
                if k == next(x for x in keys if (x in PILLARS) == isp) else None,
                customdata=[[v["name"], fmt_score(v["score_kind"], sub.loc[l, f"{k}_score"]),
                             (sub.loc[l, "con_level"] if k == "con" and isinstance(sub.loc[l, "con_lvl"], str)
                              else lvl(sub.loc[l, f"{k}_lvl"]))] for l in picked],
                hovertemplate="<b>%{x}</b><br>%{customdata[0]}: %{customdata[2]} (score %{customdata[1]})"
                              "<br>Percentile %{y:.0f}<extra></extra>"))
        for y in (100 / 3, 200 / 3):
            fig.add_hline(y=y, line_dash="dot", line_color="#cfccc4")
        fig.update_layout(barmode="group", height=400, margin=dict(l=0, r=0, t=10, b=0), barcornerradius=3,
                          bargap=0.25, bargroupgap=0.06, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          yaxis=dict(range=[0, 104], title="Percentile (higher = better)", gridcolor="rgba(0,0,0,0)",
                                     tickvals=[0, 33, 67, 100], tickfont=dict(size=11, color=MUTED)),
                          xaxis=dict(tickfont=dict(size=12, color=INK2)),
                          legend=dict(orientation="v", x=1.01, y=1, font=dict(size=12), groupclick="toggleitem"),
                          hoverlabel=dict(bgcolor="white", font=dict(size=13, color="#22211f"), bordercolor="#cfcdc6"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Each group of bars is one mandal. Bars are percentiles (100 = best among mandals with data); dotted "
                   "lines mark the Low / Medium / High thirds. A missing bar means data not available"
                   + (" (business areas cover the 323 mandals the teams scored)." if any(k in BK for k in keys) else "."))
        rows = []
        for k in keys:
            isp = k in PILLARS
            row = {"Group": "Infrastructure pillar" if isp else "Business area", "Compared on": LAYERS[k]["name"]}
            for l in picked:
                r = sub.loc[l]
                lv_ = (r["con_level"] if k == "con" and isinstance(r["con_lvl"], str) else lvl(r[f"{k}_lvl"]))
                row[lab[l]] = "Data not available" if lv_ == "no data" else \
                    f"{lv_} · {fmt_score(LAYERS[k]['score_kind'], r[f'{k}_score'])}"
            rows.append(row)
        tbl = pd.DataFrame(rows)
        sty = tbl.style.apply(lambda r: [f"background-color: {ROW_TINT[r['Group']]}"] * len(r), axis=1)
        st.dataframe(sty, hide_index=True, use_container_width=True)
        st.caption("Each cell: level · score. Blue rows = infrastructure pillars (team scores); orange rows = business "
                   "areas (team opportunity scores, 0–100).")

# ════════════════════════════════════════════════════════════════════════════
# 7. ALL MANDALS
# ════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("#### All mandals across the four pillars")
    st.caption("Follows the district filter. Use the filter to find, for example, mandals that are Low on Water.")
    f1, f2 = st.columns([1, 1])
    fp = f1.selectbox("Filter on pillar", ["(none)"] + PK, format_func=lambda k: k if k == "(none)" else PILLARS[k]["name"])
    fl = f2.multiselect("Level", ["High", "Medium", "Low", "No data"], default=["High", "Medium", "Low", "No data"],
                        disabled=fp == "(none)")
    t = df.copy()
    if fp != "(none)":
        t = t[t[f"{fp}_lvl"].fillna("No data").isin(fl)]
    out = pd.DataFrame({"Mandal": t["mandal_name"], "District": t["district_name"]})
    for p in PK:
        out[f"{PILLARS[p]['name']} level"] = t[f"{p}_lvl"].fillna("No data")
        out[f"{PILLARS[p]['name']} percentile"] = t[f"{p}_pct"].round()
    out["Pillars High"] = sum((t[f"{p}_lvl"] == "High").astype(int) for p in PK)
    out["Pillars Low"] = sum((t[f"{p}_lvl"] == "Low").astype(int) for p in PK)
    out["LGD code"] = t["mandal_lgd"]
    st.dataframe(out.sort_values(["Pillars High", "Pillars Low"], ascending=[False, True]), hide_index=True,
                 use_container_width=True, height=520,
                 column_config={**{f"{PILLARS[p]['name']} percentile": st.column_config.ProgressColumn(
                     PILLARS[p]["name"] + " %ile", min_value=0, max_value=100, format="%d") for p in PK},
                     "LGD code": st.column_config.NumberColumn(format="%d")})
    c1, c2, _ = st.columns([1, 1.3, 2])
    c1.download_button("⬇ This table (CSV)", out.to_csv(index=False).encode("utf-8-sig"), "eoz_pillars.csv",
                       "text/csv", use_container_width=True)
    full = DF[["mandal_lgd", "mandal_name", "district_name"] +
              [f"{k}_{s}" for k in LAYERS for s in ("score", "lvl", "region")] + [f"{b}_act" for b in BK]]
    c2.download_button("⬇ Pillars + business areas (CSV)", full.to_csv(index=False).encode("utf-8-sig"),
                       "eoz_all_layers.csv", "text/csv", use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# 8. REGIONS
# ════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    if not RG:
        st.info("Regions belong to one pillar or one business area. Pick a pillar under **Pillar on the map**, or a "
                "**Business area**, to see them.")
    elif BIZ:
        b = layer
        st.markdown(f"#### {BUSINESSES[b]['name']}: opportunity zones from the team's model")
        st.caption("Five zones per business from the Integrated clustering reports, ordered by zone number. "
                   "Possible SHG enterprises and support ranges are the reports' suggestions.")
        Z = (DF[DF[f"{b}_score"].notna()].groupby(f"{b}_zone_no")
             .agg(Zone=(f"{b}_zone", "first"), Mandals=("mandal_lgd", "size"), Median=(f"{b}_score", "median"),
                  Districts=("district_name", lambda s: ", ".join(s.value_counts().index[:3])))
             .reset_index())
        Z["Possible SHG enterprises"] = [ZONE_INFO[b][int(z)][0] for z in Z[f"{b}_zone_no"]]
        Z["Support range"] = [ZONE_INFO[b][int(z)][1] for z in Z[f"{b}_zone_no"]]
        Z["Median score"] = Z["Median"].round()
        # An HTML table so the long texts wrap instead of being cut off
        st.markdown('<div class="sbox"><table class="st"><thead><tr><th scope="col">Zone</th><th scope="col">Mandals</th>'
                    '<th scope="col">Median score</th><th scope="col">Possible SHG enterprises</th>'
                    '<th scope="col">Support range</th><th scope="col">Main districts</th></tr></thead><tbody>'
                    + "".join(f'<tr><td><b>{z["Zone"]}</b></td><td>{z["Mandals"]}</td><td>{z["Median score"]:.0f}</td>'
                              f'<td>{z["Possible SHG enterprises"]}</td><td>{z["Support range"]}</td>'
                              f'<td>{z["Districts"]}</td></tr>' for _, z in Z.iterrows())
                    + '</tbody></table></div>', unsafe_allow_html=True)
        st.markdown(f"#### Top 15 pilot mandals for {BUSINESSES[b]['name']}")
        T = DF[DF[f"{b}_rk"] <= 15].sort_values(f"{b}_rk")
        st.dataframe(pd.DataFrame({"Rank": T[f"{b}_rk"].astype(int), "Mandal": T["mandal_name"],
                                   "District": T["district_name"], "Opportunity score": T[f"{b}_score"].round(1),
                                   "Zone": T[f"{b}_zone"]}), hide_index=True, use_container_width=True,
                     height=36 * (len(T) + 1) + 3)
        st.caption(f"{N[b]} mandals are in the team's model; {len(DF) - N[b]} are outside it (no data on all four "
                   "pillars), shown grey on the map.")
    else:
        st.markdown(f"#### {LAYERS[layer]['name']}: regions from the team's analysis")
        st.caption("Ordered by median score. Region borders are approximate; use each mandal's own score for local "
                   "decisions.")
        R = (DF[DF["cur_score"].notna()].groupby(RG)
             .agg(Mandals=("mandal_lgd", "size"), Median=("cur_score", "median"),
                  High=("cur_lvl", lambda s: (s == "High").mean() * 100),
                  Districts=("district_name", lambda s: ", ".join(s.value_counts().index[:3])))
             .sort_values("Median", ascending=False).reset_index().rename(columns={RG: "Region"}))
        R["Median score"] = [fmt_score(META["score_kind"], v) for v in R["Median"]]
        R["% High"] = R["High"].round()
        st.dataframe(R[["Region", "Mandals", "Median score", "% High", "Districts"]], hide_index=True,
                     use_container_width=True, column_config={
                         "% High": st.column_config.ProgressColumn("Mandals at High level", min_value=0,
                                                                   max_value=100, format="%d%%"),
                         "Districts": st.column_config.TextColumn("Main districts")})
        st.caption(f"{N_CUR} mandals in regions; {len(DF) - N_CUR} have no data.")

# ════════════════════════════════════════════════════════════════════════════
# 9. ABOUT
# ════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    a, b = st.columns([1.1, 1], gap="large")
    with a:
        st.markdown("#### How to read this dashboard")
        st.markdown(
            "- **Four infrastructure pillars:** Water, Electricity, Connectivity and Market access. The map shows "
            "**one pillar at a time** in three levels (High, Medium, Low) plus grey for no data.\n"
            "- **Each mandal's profile** shows its level on **all four pillars side by side**, so you can see "
            "where it is strong and where it lags.\n"
            "- **Levels:** Connectivity uses the levels in its report. The other pillars split their scored "
            "mandals into thirds, so High means the top third of mandals with data.\n"
            "- **Business areas:** Agriculture, Livestock, Rural Services and Aquaculture. The map shows each team's "
            "**opportunity score** (0–100): the business's own data combined with the infrastructure pillars, "
            "weighted equally (Integrated clustering reports). Selecting a mandal shows an **infrastructure "
            "check** (what the business needs against what the mandal has) next to the opportunity score, its zone, "
            "possible SHG enterprises and support range.\n"
            "- **Business activity score:** each business team's earlier score from business data only (679 "
            "mandals). It is under *A single measure* and in each mandal's details.")
        st.markdown("#### Layers and sources")
        st.dataframe(pd.DataFrame([{"Layer": v["name"], "Type": "Pillar" if k in PILLARS else "Business area",
                                    "Mandals with data": N[k], "Score": v["score_label"], "Source": v["source"]}
                                   for k, v in LAYERS.items()]), hide_index=True, use_container_width=True)
        st.markdown("#### What each business needs (used for the infrastructure check)")
        st.dataframe(pd.DataFrame([{"Business": BUSINESSES[b]["name"],
                                    **{PILLARS[p]["name"]: d["w"][p] for p in PK}, "Source": d["src"]}
                                   for b, d in DRAFT.items()]), hide_index=True, use_container_width=True)
        st.caption("Rule: needed High (Medium/High counts as High) — High meets, Medium partly, Low gap. Needed "
                   "Medium — Low is partly. Needed Low — any level meets. No data — unknown. Verdict: no gaps = "
                   "Suitable, 1 gap = Partly suitable, 2 or more = Not suitable.")
    with b:
        st.markdown("#### Limitations")
        st.markdown(
            "- **Missing data is a limitation, not a low score.** It is shown in grey on every map.\n"
            "  - **Connectivity:** 76 mandals, mostly the old Visakhapatnam district (Anakapalli, Alluri "
            "Sitharama Raju, Visakhapatnam).\n"
            "  - **Electricity:** 291 mandals in nine districts: Ananthapuramu, YSR Kadapa, Kurnool, Annamayya, "
            "Nandyal, Sri Sathya Sai, Nellore, Tirupati and Chittoor.\n"
            "  - **Water:** 27 mandals (urban splits, very little cropland).\n"
            "- **Connectivity levels come from its regions**, so a mandal takes its region's level. A few weak "
            "mandals sit in an Average region (and a few strong ones in a weaker region); check the mandal's own score "
            "and rank.\n"
            "- **Each team uses its own scale.** Compare pillars by level or percentile, not raw score.\n"
            "- **Opportunity scores** cover 323 mandals (those with all four pillars); the rest, mostly in the "
            "south where Electricity data is missing, are grey on the business maps. Rural Services and "
            "Aquaculture do not use the Market access pillar.\n"
            "- **What each business needs** (for the infrastructure check) comes from the mid-review deck; "
            "Aquaculture's ratings are Claude's suggestion. None are validated with SERP.\n"
            "- **Livestock, Rural Services and Aquaculture** files have no LGD codes; they were matched by name "
            "(611 exact, 68 spelling variants).")
        st.markdown("#### Caveats by layer")
        for k, v in LAYERS.items():
            with st.expander(v["name"]):
                st.markdown("\n".join(f"- {c}" for c in v["caveats"]))
