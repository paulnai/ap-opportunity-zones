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

BUSINESSES = {
    "agr": dict(name="Agriculture", score_kind="0-100", score_label="Agriculture composite (0–100)",
                score_help="The Agriculture team's score: the four pillars standardised and weighted equally.",
                nodata="Not scored: needs all four pillars, and Electricity is missing here.",
                source="Agriculture analysis and report",
                measures=[("z_market", "Market access (z-score)", "idx"), ("z_electricity", "Electricity (z-score)", "idx"),
                          ("z_water", "Water (z-score)", "idx"), ("z_connectivity", "Connectivity (z-score)", "idx")],
                caveats=["323 mandals: only those with all four pillars."]),
    "liv": dict(name="Livestock", score_kind="index", score_label="Livestock scale score (PC1)",
                score_help="Higher = more livestock and larger small-ruminant herds. It measures scale, not dairy "
                           "suitability.",
                nodata="Not in the Livestock file (newer urban split or new mandal).",
                source="Livestock Analysis report v3",
                measures=[("tlu", "Tropical livestock units", "num"), ("buffalo_ratio", "Buffalo ratio", "num"),
                          ("small_ruminant", "Small-ruminant specialisation", "num"),
                          ("catchment_tlu", "Livestock within 15 km (TLU)", "num"),
                          ("vet_support", "Vet support per 1,000 TLU", "num"),
                          ("demand_density", "Commercial demand density", "num")],
                caveats=["Matched to the map by mandal name (no LGD code in the file).",
                         "Delta dairy mandals score low: the score rewards total herd scale, not buffalo dairy."]),
    "ser": dict(name="Rural Services", score_kind="index", score_label="Rural services score (PC1)",
                score_help="Higher = more civic, education, health, PDS, tourism and transport footfall anchors.",
                nodata="Not in the Rural Services file (newer urban split or new mandal).",
                source="Rural Services Analysis report",
                measures=[("civic", "Civic and admin footfall", "num"), ("education", "Education anchors", "num"),
                          ("health", "Healthcare capacity", "num"), ("pds", "Nutrition / PDS network", "num"),
                          ("tourism", "Heritage and tourism pull", "num"), ("transport", "Transport junctions", "num")],
                caveats=["Matched to the map by mandal name (no LGD code in the file)."]),
    "aqu": dict(name="Aquaculture", score_kind="index", score_label="Aquaculture score (PC1)",
                score_help="Higher = larger commercial aquaculture scale and intensity.",
                nodata="Not in the Aquaculture file (newer urban split or new mandal).",
                source="Aquaculture Mandal Analysis report (679 mandals) and notebook",
                measures=[("production", "Production scale (ha)", "num"), ("headroom", "Expansion headroom (ha)", "num"),
                          ("saltpan", "Saltpan capacity (ha)", "num"), ("intensity", "Pond intensity ratio", "num"),
                          ("landing", "Marine landing anchor", "num")],
                caveats=["Matched to the map by mandal name (no LGD code in the file).",
                         "Re-run of the team's notebook; matches the 679-mandal report's six regions."]),
}
LAYERS = {**PILLARS, **BUSINESSES}

# Draft weights for combining the four pillars per business (Low 1 · Medium 2 · High 3)
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
</style>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# 2. DATA
# ════════════════════════════════════════════════════════════════════════════
def tercile(pct):
    return np.where(pd.isna(pct), None, np.where(pct > 200 / 3, "High", np.where(pct > 100 / 3, "Medium", "Low")))


@st.cache_data
def load():
    df = pd.read_csv(DATA / "mandals.csv")
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


def draft_series(b, weights, allow_three):
    P = DF[[f"{p}_pct" for p in PK]].to_numpy()
    w = np.array([weights[p] for p in PK], dtype=float)
    have = ~np.isnan(P)
    den = (have * w).sum(axis=1)
    score = np.where(den > 0, np.nansum(P * w, axis=1) / np.where(den == 0, 1, den), np.nan)
    ok = have.all(axis=1) | (allow_three & have[:, [0, 2, 3]].all(axis=1) & ~have[:, 1])
    return pd.Series(np.where(ok, score, np.nan), index=DF.index)


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


if "weights" not in st.session_state:
    st.session_state.weights = {b: {p: WORD[x] for p, x in d["w"].items()} for b, d in DRAFT.items()}

# ════════════════════════════════════════════════════════════════════════════
# 3. SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Opportunity Zones Explorer")
    st.caption("Problem Statement 2 · SERP × ISB capstone")
    section = st.radio("Section", ["Infrastructure pillars", "Business areas"],
                       captions=["Water, Electricity, Connectivity, Market access",
                                 "Agriculture, Livestock, Rural Services, Aquaculture"])
    allow_three = False
    scope = "one"
    if section == "Infrastructure pillars":
        pick = st.radio("Pillar on the map", PK + ["all"],
                        format_func=lambda k: "🧩  All four pillars" if k == "all"
                        else f"{PILLARS[k]['icon']}  {PILLARS[k]['name']}",
                        help="One pillar at a time, or all four pillars read together. Each mandal's result on "
                             "all four pillars is always in its profile.")
        scope, layer = ("all", "con") if pick == "all" else ("one", pick)
        view = "team"
    else:
        layer = st.selectbox("Business area", list(BUSINESSES), format_func=lambda k: BUSINESSES[k]["name"])
        view = st.radio("Show", ["team", "draft"],
                        format_func=lambda v: {"team": "Team's analysis", "draft": "Draft opportunity score"}[v],
                        help="Team's analysis = the business team's own score. Draft opportunity score = the four "
                             "pillars combined with draft weights for this business.")
        if view == "draft":
            with st.expander("Draft weights", expanded=False):
                st.caption(f"Source: {DRAFT[layer]['src']}. Low = 1, Medium = 2, High = 3. Changes are not saved.")
                for p in PK:
                    st.session_state.weights[layer][p] = st.slider(
                        PILLARS[p]["name"], 0.0, 3.0, float(st.session_state.weights[layer][p]), 0.5,
                        key=f"w_{layer}_{p}", help=f"Default: {DRAFT[layer]['w'][p]}")
                if st.button("Reset", use_container_width=True):
                    st.session_state.weights[layer] = {p: WORD[x] for p, x in DRAFT[layer]["w"].items()}
                    for p in PK:
                        st.session_state.pop(f"w_{layer}_{p}", None)
                    st.rerun()
            allow_three = st.toggle("Also score mandals without Electricity", value=False,
                                    help="Electricity covers 397 mandals. When on, the south is scored on the other "
                                         "three pillars.")
    MODES = {
        "level": ("Level (High / Medium / Low)", "Compared with the whole state"),
        "dlevel": ("Level within the district", "Compared with mandals in the same district"),
        "score": ("Score (shading)", "Finer detail than three levels"),
        "measure": ("A single measure", "One input to the score, e.g. canal coverage"),
        "nhigh": ("Number of pillars at High (0–4)", "Overall infrastructure strength"),
        "weak": ("Weakest pillar (bottleneck)", "What is holding each mandal back"),
        "cover": ("Data coverage (0–4 pillars with data)", "Where data is missing"),
    }
    one = ["level", "score", "dlevel"] + (["measure"] if view == "team" and layer != "ele" and LAYERS[layer]["measures"] else [])
    avail = one if scope == "one" else ["nhigh", "weak", "cover"]
    colour_by = st.radio("Colour the map by", avail, format_func=lambda m: MODES[m][0],
                         captions=[MODES[m][1] for m in avail])
    measure_pick = None
    if colour_by == "measure":
        ms = LAYERS[layer]["measures"]
        measure_pick = st.selectbox("Measure", range(len(ms)), format_func=lambda i: ms[i][1])
    st.divider()
    districts = st.multiselect("Districts", sorted(DF["district_name"].unique()), placeholder="All 26 districts",
                               help="Leave empty for the whole state. The map zooms to the districts you pick.")
    st.caption("Grey on every map means **no data**, never a low score.")

# Current layer
if view == "draft":
    DF["cur_score"] = draft_series(layer, st.session_state.weights[layer], allow_three)
    META = dict(name=f"{BUSINESSES[layer]['name']}: draft opportunity score", score_kind="0-100",
                score_label="Draft opportunity score (0–100)",
                score_help="The four pillars, each as a percentile, combined with this business's draft weights.",
                nodata="Not scored: a pillar is missing here (mostly Electricity in the south).", measures=[],
                level_rule="Levels are thirds of the scored mandals.")
else:
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
    st.session_state.mandal_lgd = None


def select_mandal(lgd):
    st.session_state.mandal_lgd = None if lgd is None else int(lgd)
    st.session_state.map_ver += 1
    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# 4. HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="eyebrow">Entrepreneurial Opportunity Zones · Andhra Pradesh · mandal level</div>',
            unsafe_allow_html=True)
title = ("All four pillars together" if scope == "all" else
         f"{PILLARS[layer]['icon']} {PILLARS[layer]['name']} — {PILLARS[layer]['question']}"
         if section == "Infrastructure pillars" else META["name"])
st.markdown(f"## {title}")
st.caption(f"{', '.join(districts) if districts else 'All of Andhra Pradesh'} · " +
           ("Water, Electricity, Connectivity and Market access read together for each mandal."
            if scope == "all" else META["score_help"]))
if view == "draft":
    wv = st.session_state.weights[layer]
    st.markdown(f'<div class="draft"><b>Draft, not validated with SERP.</b> Weights: '
                + " · ".join(f"{PILLARS[p]['name']} {wv[p]:g}" for p in PK)
                + f" (source: {DRAFT[layer]['src']}).</div>", unsafe_allow_html=True)

cnt = scored["cur_lvl"].value_counts()
cols = st.columns(5)
if scope == "all":
    tiles_all = [(f"{len(df):,}", "Mandals", None),
                 (f"{(df['n_high'] == 4).sum():,}", "High on all 4 pillars", "#0d366b"),
                 (f"{df['weak'].isin([PILLARS[p]['name'] for p in PK]).sum():,}", "Low on at least 1 pillar", LEVEL_COLOURS["Low"]),
                 (f"{(df['n_data'] == 4).sum():,}", "Data on all 4 pillars", "#3d3a33"),
                 (f"{(df['n_data'] < 4).sum():,}", "Missing 1 or more pillars", NO_DATA)]
tiles = [(f"{len(scored):,}", f"Mandals with data (of {len(df)})", None)] + \
        [(f"{cnt.get(lv, 0):,}", lv if not (view == "team" and layer == "con") else
          {"High": "Well connected", "Medium": "Average", "Low": "Poorly connected"}[lv], LEVEL_COLOURS[lv])
         for lv in ["High", "Medium", "Low"]] + [(f"{len(df) - len(scored):,}", "No data (grey)", NO_DATA)]
for c, (n, l, colr) in zip(cols, tiles_all if scope == "all" else tiles):
    sw = f'<span class="sw" style="background:{colr};border:1px solid #cfcdc6"></span>' if colr else ""
    c.markdown(f'<div class="kpi"><div class="n">{n}</div><div class="l">{sw}{l}</div></div>', unsafe_allow_html=True)
st.caption("In this view every pillar, Connectivity included, is split into thirds of the mandals with data, so the four are compared like with like." if scope == "all" else META.get("level_rule", "Levels are thirds of the scored mandals: top third High, middle Medium, bottom Low."))

tabs = st.tabs(["🗺️  Map and mandal profile", "⚖️  Compare mandals", "📋  All mandals", "🧭  Regions",
                "ℹ️  About and limitations"])


# ════════════════════════════════════════════════════════════════════════════
# 5. MAP
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data
def district_label_points():
    rows = []
    for f in DISTRICT_GEO["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        ring = np.array(max(polys, key=lambda p: len(p[0]))[0])
        rows.append((f["properties"]["district_name"], ring[:, 0].mean(), ring[:, 1].mean()))
    return pd.DataFrame(rows, columns=["district", "lon", "lat"])


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
            t += (f"High on <b>{int(r['n_high'])} of {int(r['n_data'])}</b> pillars with data"
                  + (f" · weakest: <b>{r['weak']}</b>" if isinstance(r["weak"], str) else "") + "<br>"
                  + "<br>".join(f"{PILLARS[p]['name']}: {lvl(r[f'{p}_t3'])}" for p in PK))
            out.append(t)
            continue
        if pd.isna(r["cur_score"]):
            t += f"<i>{nodata_reason(r)}</i>"
        else:
            t += (f"{META['score_label']}: <b>{fmt_score(META['score_kind'], r['cur_score'])}</b> "
                  f"(rank {int(r['cur_rk'])} of {N_CUR})<br>Level: <b>{r['cur_lvl']}</b>")
            if RG and isinstance(r[RG], str):
                t += f"<br>Region: {r[RG]}"
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
            cat(d[(d["n_high"] == n_) & (d["n_data"] > 0)], c_, f"{n_} of 4 pillars High")
        cat(d[d["n_data"] == 0], NO_DATA, "No data")
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
    lab = district_label_points()
    if districts:
        lab = lab[lab["district"].isin(districts)]
    fig.add_trace(go.Scattergeo(lon=lab["lon"], lat=lab["lat"], text=lab["district"], mode="text",
                                textfont=dict(size=10, color="#3b3a36"), hoverinfo="skip", showlegend=False))
    trace_lgd.append([])
    sel = d[d["mandal_lgd"] == st.session_state.mandal_lgd]
    if not sel.empty:
        fig.add_trace(go.Choropleth(locations=sel["mandal_lgd"], z=[1], geojson=MANDAL_GEO,
                                    featureidkey="properties.mandal_lgd",
                                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                                    marker_line_color="#111", marker_line_width=2.2, showscale=False,
                                    hoverinfo="skip", showlegend=False))
        trace_lgd.append([])
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      legend=dict(x=0.01, y=0.02, xanchor="left", yanchor="bottom", bgcolor="rgba(255,255,255,0.9)",
                                  bordercolor="#e3e1da", borderwidth=1, font=dict(size=11)),
                      hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#cfcdc6"))
    return fig, trace_lgd


MAP_CONFIG = {"displayModeBar": False, "scrollZoom": False}
if st.get_option("server.enableStaticServing"):
    MAP_CONFIG["topojsonURL"] = "app/static/"


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
        st.caption("Choose **One pillar** in the sidebar to see a pillar's measures for this mandal.")
    else:
        st.markdown(f"**{META['name'] if section == 'Business areas' else PILLARS[layer]['name']}: details**")
        if pd.isna(r["cur_score"]):
            st.markdown(f'<div class="note">{nodata_reason(r)}</div>', unsafe_allow_html=True)
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Score", fmt_score(META["score_kind"], r["cur_score"]), help=META["score_help"])
            m2.metric("Rank", f"{int(r['cur_rk'])} of {N_CUR}")
            m3.metric("Level", r["cur_lvl"], help=META.get("level_rule", "Thirds of the scored mandals."))
            if RG and isinstance(r[RG], str):
                st.markdown(f'<div class="muted">Region: <b>{r[RG]}</b></div>', unsafe_allow_html=True)
            if META["measures"]:
                mt = pd.DataFrame([{"Measure": lbl,
                                    "Value": fmt_measure(kind, r[f"{layer}_{col}"], r["con_city"] and col == "C5"),
                                    "Percentile": None if pd.isna(r[f"{layer}_{col}_pct"]) else round(r[f"{layer}_{col}_pct"])}
                                   for col, lbl, kind in META["measures"]])
                st.dataframe(mt, hide_index=True, use_container_width=True,
                             column_config={"Percentile": st.column_config.ProgressColumn(min_value=0, max_value=100,
                                                                                          format="%d")})
            if view == "draft" and pd.isna(r["ele_pct"]):
                st.markdown('<div class="draft">Scored on three pillars: no electricity data here.</div>',
                            unsafe_allow_html=True)
        if view == "team" and layer == "con" and r["con_city"]:
            st.markdown('<div class="note">City mandal: village access and bus service assumed 100%; road condition '
                        '(*) is the district median.</div>', unsafe_allow_html=True)

    with st.expander("Business areas for this mandal"):
        rows = []
        for b, v in BUSINESSES.items():
            ds = draft_series(b, st.session_state.weights[b], allow_three)
            rows.append({"Business": v["name"], "Team's score": fmt_score(v["score_kind"], r[f"{b}_score"]),
                         "Team level": lvl(r[f"{b}_lvl"]),
                         "Draft opportunity": "no data" if pd.isna(ds.loc[r.name]) else f"{ds.loc[r.name]:.0f}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


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


def small_map(d, p, dist):
    """One pillar's levels for the selected mandal's district, in the same colours as the profile cards."""
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
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#cfcdc6"))
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
            legend = "".join(f'<span class="sw" style="background:{c};border:1px solid #cfcdc6"></span>{n}&nbsp;&nbsp;'
                             for n, c in [("High / Well connected", LEVEL_COLOURS["High"]),
                                          ("Medium / Average", LEVEL_COLOURS["Medium"]),
                                          ("Low / Poorly connected", LEVEL_COLOURS["Low"]), ("No data", NO_DATA)])
            st.markdown(f'<div class="muted">{legend}</div>', unsafe_allow_html=True)
            dd = DF[DF["district_name"] == dist]
            for row in (PK[:2], PK[2:]):
                cols_ = st.columns(2)
                for c_, p in zip(cols_, row):
                    with c_:
                        st.markdown(f"**{PILLARS[p]['icon']} {PILLARS[p]['name']}**")
                        f_, tl_ = small_map(dd, p, dist)
                        ev_ = st.plotly_chart(f_, use_container_width=True, on_select="rerun", selection_mode="points",
                                              key=f"four_{p}_{st.session_state.map_ver}", config=MAP_CONFIG)
                        lg = clicked_lgd(ev_, tl_)
                        if lg is not None and int(lg) != sel_lgd:
                            select_mandal(lg)
            st.caption(f"Each small map is one pillar for {dist} district, in the same colours as the profile cards. "
                       f"{r0['mandal_name']} is outlined in black. Click another mandal to switch to it.")
        else:
            fig, trace_lgd = build_map(df)
            ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points",
                                 key=f"map_{st.session_state.map_ver}", config=MAP_CONFIG)
            lg = clicked_lgd(ev, trace_lgd)
            if lg is not None and int(lg) != sel_lgd:
                select_mandal(lg)
            MODE_NOTE = {
                "dlevel": "Each mandal compared only with mandals in its own district (top, middle, bottom third).",
                "nhigh": "How many of the four pillars each mandal is High on (top third). Mandals missing a pillar can't reach 4.",
                "weak": "The pillar each mandal does worst on, among pillars in the bottom third. Light green = no bottleneck. Only pillars with data are compared.",
                "cover": "How many of the four pillars have data for each mandal. Darker = more complete.",
            }
            if colour_by in MODE_NOTE:
                st.caption(MODE_NOTE[colour_by])
            st.caption("Hover for details · **click a mandal** to see it on all four pillars · click a legend "
                       "item to hide it.")
            if sel_lgd is not None:
                if st.button("Clear the selected mandal"):
                    select_mandal(None)
    with right:
        opts = df.sort_values(["district_name", "mandal_name"])
        labels, lgds = opts["label"].tolist(), opts["mandal_lgd"].tolist()
        cur = lgds.index(sel_lgd) if sel_lgd in lgds else None
        chosen = st.selectbox("Find a mandal", labels, index=cur, placeholder="Type a mandal name…",
                              help="Type to search, or click a mandal on the map.",
                              key=f"find_{st.session_state.map_ver}")
        if chosen is not None and lgds[labels.index(chosen)] != sel_lgd:
            select_mandal(lgds[labels.index(chosen)])
        if sel_lgd is None:
            st.markdown('<div class="card"><h4>Select a mandal</h4>Click a mandal on the map or type its name above. '
                        'The map will then show it on all four pillars, side by side, and its profile appears here.'
                        '</div>', unsafe_allow_html=True)
        else:
            profile(sel_lgd)

# ════════════════════════════════════════════════════════════════════════════
# 6. COMPARE
# ════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("#### Compare up to five mandals across the four pillars")
    st.caption("Bars are percentiles (100 = best among mandals with data). A missing bar means no data.")
    pool = DF.sort_values(["district_name", "mandal_name"])
    lab = dict(zip(pool["mandal_lgd"], pool["label"]))
    _sel = st.session_state.mandal_lgd
    default = ([_sel] if _sel is not None else []) + \
        [x for x in DF.sort_values("agr_rk")["mandal_lgd"] if x != _sel][:3 - (1 if _sel is not None else 0)]
    picked = st.multiselect("Mandals", pool["mandal_lgd"].tolist(), default=default, max_selections=5,
                            format_func=lambda x: lab.get(x, str(x)))
    with_biz = st.checkbox("Also show the four business areas (team scores)", value=False)
    keys = PK + (list(BUSINESSES) if with_biz else [])
    if picked:
        COLS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
        sub = DF.set_index("mandal_lgd").loc[picked]
        fig = go.Figure()
        for i, (lgd, r) in enumerate(sub.iterrows()):
            fig.add_trace(go.Bar(x=[LAYERS[k]["name"] for k in keys], y=[r[f"{k}_pct"] for k in keys], name=lab[lgd],
                                 marker_color=COLS[i], marker_line_color="white", marker_line_width=2,
                                 customdata=[f"{fmt_score(LAYERS[k]['score_kind'], r[f'{k}_score'])} · "
                                             f"{lvl(r[f'{k}_lvl'])}" for k in keys],
                                 hovertemplate="<b>" + lab[lgd] + "</b><br>%{x}: %{customdata}<br>Percentile %{y:.0f}<extra></extra>"))
        for y in (100 / 3, 200 / 3):
            fig.add_hline(y=y, line_dash="dot", line_color="#cfccc4")
        fig.update_layout(barmode="group", height=380, margin=dict(l=0, r=0, t=10, b=0), barcornerradius=4, bargap=0.22,
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          yaxis=dict(range=[0, 104], title="Percentile (higher = better)", gridcolor="rgba(0,0,0,0)",
                                     tickvals=[0, 33, 67, 100], tickfont=dict(size=10, color=MUTED)),
                          xaxis=dict(tickfont=dict(size=12, color=INK2)),
                          legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Dotted lines mark the Low / Medium / High thirds.")
        tbl = pd.DataFrame({"": [LAYERS[k]["name"] for k in keys]})
        for lgd, r in sub.iterrows():
            tbl[lab[lgd]] = [(r["con_level"] if k == "con" and isinstance(r[f"{k}_lvl"], str) else lvl(r[f"{k}_lvl"]))
                             + ("" if pd.isna(r[f"{k}_score"]) else f" · {fmt_score(LAYERS[k]['score_kind'], r[f'{k}_score'])}")
                             for k in keys]
        st.dataframe(tbl, hide_index=True, use_container_width=True)

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
              [f"{k}_{s}" for k in LAYERS for s in ("score", "lvl", "region")]]
    c2.download_button("⬇ Pillars + business areas (CSV)", full.to_csv(index=False).encode("utf-8-sig"),
                       "eoz_all_layers.csv", "text/csv", use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# 8. REGIONS
# ════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    if not RG:
        st.info("Regions belong to one pillar or one business area's own analysis. Choose **One pillar**, or a "
                "business area's **Team's analysis**, to see them.")
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
            "- **Business areas:** Agriculture, Livestock, Rural Services and Aquaculture, each with the team's own "
            "analysis and a **draft opportunity score** that combines the four pillars with draft weights.")
        st.markdown("#### Layers and sources")
        st.dataframe(pd.DataFrame([{"Layer": v["name"], "Type": "Pillar" if k in PILLARS else "Business area",
                                    "Mandals with data": N[k], "Score": v["score_label"], "Source": v["source"]}
                                   for k, v in LAYERS.items()]), hide_index=True, use_container_width=True)
        st.markdown("#### Draft weights (Low 1 · Medium 2 · High 3)")
        st.dataframe(pd.DataFrame([{"Business": BUSINESSES[b]["name"],
                                    **{PILLARS[p]["name"]: d["w"][p] for p in PK}, "Source": d["src"]}
                                   for b, d in DRAFT.items()]), hide_index=True, use_container_width=True)
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
            "- **Draft opportunity scores** cover 323 mandals (all four pillars) unless scoring without "
            "Electricity is switched on. The weights are not validated with SERP.\n"
            "- **Livestock, Rural Services and Aquaculture** files have no LGD codes; they were matched by name "
            "(611 exact, 68 spelling variants).")
        st.markdown("#### Caveats by layer")
        for k, v in LAYERS.items():
            with st.expander(v["name"]):
                st.markdown("\n".join(f"- {c}" for c in v["caveats"]))
