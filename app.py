"""
Entrepreneurial Opportunity Zones — results explorer (Problem Statement 2)
ISB AMPBA Capstone · SERP, Government of Andhra Pradesh

Proof of concept: Connectivity (Roads) pillar.
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

st.set_page_config(
    page_title="AP Opportunity Zones Explorer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════
# 1. SETTINGS — labels, colours and text taken from the Connectivity report
#    (edit here to rename things; no other part of the file needs changing)
# ════════════════════════════════════════════════════════════════════════════
NO_DATA = "#efeee9"          # grey = no data, never "poor"
NO_DATA_CONT = "#cfccc4"     # darker grey on the score / measure maps, so it never looks like "average"

LEVELS = {                   # name: (colour, short description)
    "Well connected":   ("#1c5cab", "Almost every village has an all-weather road, most people have a bus, highways are close."),
    "Average":          ("#aaa596", "Works reasonably well but has one clear weak point."),
    "Poorly connected": ("#c0392b", "Many villages lack an all-weather road, buses are scarce, few highways."),
    "Not assessed":     (NO_DATA,   "No usable data. This does not mean poor connectivity."),
}

# Region number → name, colour, main districts, defining feature, what would help most (report Tables 7 and 11)
REGIONS = {
    1: ("Visakhapatnam urban core", "#083c7d", "Visakhapatnam", "Dense, fully paved city roads",
        "Keep up; city values partly assumed"),
    2: ("Vijayawada urban core", "#1d6cb1", "NTR", "Densest network; most highways",
        "Keep up; city values partly assumed"),
    3: ("Krishna–Godavari delta and plains", "#4f9bcb", "Eluru, Krishna, East and West Godavari",
        "Best rural access and paving", "Paving and resurfacing of village roads"),
    4: ("Palnadu–Prakasam uplands", "#94c4df", "Palnadu, Prakasam, Guntur",
        "Buses reach 95% of people; roads mostly unpaved, poor", "Road repair and resurfacing"),
    5: ("Rayalaseema and south", "#fc9b7c", "Kadapa, Tirupati, Nellore",
        "Near average; fewest highways of large regions", "Links to highways and district roads"),
    6: ("North coastal Andhra", "#f96346", "Vizianagaram, Srikakulam",
        "Weakest bus service (48% of people)", "Bus services; all-weather village links"),
    7: ("Godavari agency (hill) belt", "#de2b25", "Polavaram",
        "Almost no highways", "Basic road and bus access"),
    8: ("Annamayya–Sri Sathya Sai pocket", "#ac1117", "Annamayya, Sri Sathya Sai",
        "Half the villages lack an all-weather road", "All-weather village roads first, then buses"),
}

# The seven road measures: column, short label, full label, kind ("pct" or "density"), weight in score
VARIABLES = [
    ("con_C1", "Villages with all-weather road", "% habitations with an all-weather road", "pct", 27),
    ("con_C2", "People with a bus service", "% population with a bus service", "pct", 17),
    ("con_C3", "Road length all-weather", "% road length all-weather", "pct", 12),
    ("con_C4", "Road length paved", "% road length paved", "pct", 14),
    ("con_C5", "Road length in fair+ condition", "% road length in fair or better condition (PCI ≥ 3)", "pct", 16),
    ("con_C6", "Road density", "Road density, village + town (km per 100 km²)", "density", 9),
    ("con_C7", "Highway density", "Highway density, NH + SH (km per 100 km²)", "density", 5),
]
VAR_BY_COL = {v[0]: v for v in VARIABLES}

BUSINESS_BY_LEVEL = {        # report Table 12
    "Well connected": ("Businesses that move goods daily or in bulk: milk collection and dairy, fruit and vegetables, "
                       "food processing for outside markets.",
                       "Unpaved stretches still slow heavy loads in parts of the delta."),
    "Average": ("Most businesses are workable, if planned around the local weak point.",
                "Palnadu–Prakasam: rough roads raise the cost of moving bulky goods. Rayalaseema: few highways slow "
                "transport outside the district. North coast: few buses make it harder for women to reach markets, "
                "banks and training."),
    "Poorly connected": ("For now, businesses that sell locally or make light, long-lasting goods: tailoring, crafts, "
                         "local services.",
                         "Dairy, fresh produce and processing for outside markets would first need better roads and "
                         "bus links."),
}

# Pillars. Only Connectivity is loaded in this proof of concept; the others appear once their files are added.
PILLARS = {
    "Connectivity (roads)": True,
    "Electricity": False,
    "Water infrastructure": False,
    "Water availability": False,
    "Agricultural market access": False,
}

# The base map file ships in /static so the map works without internet access to plotly's CDN.
# If static serving is off (e.g. the .streamlit folder was not uploaded), fall back to the CDN.
MAP_CONFIG = {"displayModeBar": False, "scrollZoom": False}
if st.get_option("server.enableStaticServing"):
    MAP_CONFIG["topojsonURL"] = "app/static/"

COMPARE_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, MUTED = "#22211f", "#55534d", "#8a877f"

# ════════════════════════════════════════════════════════════════════════════
# 2. STYLE
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
<style>
  .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px;}
  h1, h2, h3 {letter-spacing: -0.01em;}
  .eyebrow {font-size: 0.78rem; text-transform: uppercase; letter-spacing: .08em; color: #8a877f; margin-bottom: .1rem;}
  .kpi {border: 1px solid #e3e1da; border-radius: 10px; padding: .75rem .9rem; background: #ffffff; height: 100%;}
  .kpi .n {font-size: 1.65rem; font-weight: 650; line-height: 1.1; color: #22211f;}
  .kpi .l {font-size: .82rem; color: #55534d; margin-top: .15rem;}
  .kpi .sw {display:inline-block; width:.7rem; height:.7rem; border-radius:3px; margin-right:.35rem; vertical-align: -1px;}
  .pill {display:inline-block; padding:.15rem .6rem; border-radius: 999px; font-size:.8rem; font-weight:600;}
  .card {border: 1px solid #e3e1da; border-radius: 10px; padding: .9rem 1rem; background: #ffffff; margin-bottom: .6rem;}
  .card h4 {margin: 0 0 .3rem 0; font-size: .95rem;}
  .muted {color: #8a877f; font-size: .85rem;}
  .note {background:#f7f6f2; border-left: 3px solid #bdbab1; padding:.55rem .75rem; border-radius: 4px; font-size: .86rem; color:#55534d; margin:.4rem 0;}
  div[data-testid="stMetricValue"] {font-size: 1.45rem;}
</style>
""",
    unsafe_allow_html=True,
)


# ════════════════════════════════════════════════════════════════════════════
# 3. DATA
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load():
    df = pd.read_csv(DATA / "mandals.csv")
    df["con_region"] = df["con_region"].astype("Int64")
    df["con_rank"] = df["con_rank"].astype("Int64")
    mandals_geo = json.loads((DATA / "mandals.geojson").read_text())
    districts_geo = json.loads((DATA / "districts.geojson").read_text())
    # Percentile among analysed mandals (0–100, higher = better) for every measure
    for col, *_ in VARIABLES:
        df[col + "_pct"] = df[col].rank(pct=True) * 100
    df["label"] = df["mandal_name"] + " (" + df["district_name"] + ")"
    return df, mandals_geo, districts_geo


df_all, MANDAL_GEO, DISTRICT_GEO = load()
analysed_all = df_all[df_all["con_level"] != "Not assessed"]
N_ANALYSED = len(analysed_all)


def district_lines(districts):
    """District outlines as one line trace (lon/lat with gaps)."""
    lons, lats, labels = [], [], []
    for f in DISTRICT_GEO["features"]:
        name = f["properties"]["district_name"]
        if districts and name not in districts:
            continue
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ring = np.array(poly[0])
            lons += ring[:, 0].tolist() + [None]
            lats += ring[:, 1].tolist() + [None]
    return lons, lats


@st.cache_data
def district_label_points():
    rows = []
    for f in DISTRICT_GEO["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        big = max(polys, key=lambda p: len(p[0]))
        ring = np.array(big[0])
        rows.append((f["properties"]["district_name"], ring[:, 0].mean(), ring[:, 1].mean()))
    return pd.DataFrame(rows, columns=["district", "lon", "lat"])


def fmt_value(col, v, city=False):
    if pd.isna(v):
        return "—"
    kind = VAR_BY_COL[col][3]
    if kind == "pct":
        s = f"{v*100:.0f}%"
        if city and col == "con_C5":
            s += "*"
        return s
    return f"{v:,.1f}"


def fmt_score(v):
    return "—" if pd.isna(v) else f"{v:+.2f}"


# ════════════════════════════════════════════════════════════════════════════
# 4. SIDEBAR — filters
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Opportunity Zones Explorer")
    st.caption("Problem Statement 2 · SERP × ISB capstone")

    pillar = st.selectbox(
        "Pillar",
        [p for p, ready in PILLARS.items() if ready],
        help="Electricity, the two water pillars and market access will be added here once their results are final.",
    )
    st.caption("Coming next: " + ", ".join(p for p, ready in PILLARS.items() if not ready) + ".")

    st.divider()
    districts = st.multiselect(
        "Districts", sorted(df_all["district_name"].unique()),
        placeholder="All 26 districts",
        help="Leave empty to see the whole state. The map zooms to the districts you pick.",
    )
    levels = st.multiselect(
        "Connectivity level", list(LEVELS), default=list(LEVELS),
        help="Untick a level to hide those mandals from the map, the counts and the table.",
    )

    st.divider()
    colour_options = ["Connectivity level", "Connectivity region (8)", "Connectivity score"] + \
                     [f"{c[-2:]} · {short}" for c, short, *_ in VARIABLES]
    colour_by = st.radio("Colour the map by", colour_options, index=0)

    st.divider()
    st.caption(
        "Grey on every map means **no data**, never poor connectivity. "
        "Source: Connectivity (Roads) pillar report, October 2026."
    )

# Apply filters
df = df_all.copy()
if districts:
    df = df[df["district_name"].isin(districts)]
df = df[df["con_level"].isin(levels)] if levels else df.iloc[0:0]
analysed = df[df["con_level"] != "Not assessed"]

# Remember the chosen mandal across reruns; if filters hide it, jump to the best-ranked mandal still shown
if "mandal_lgd" not in st.session_state:
    st.session_state.mandal_lgd = int(analysed_all.sort_values("con_rank").iloc[0]["mandal_lgd"])
if not df.empty and st.session_state.mandal_lgd not in set(df["mandal_lgd"]):
    pool_ = analysed if not analysed.empty else df
    st.session_state.mandal_lgd = int(pool_.sort_values("con_rank", na_position="last").iloc[0]["mandal_lgd"])

# ════════════════════════════════════════════════════════════════════════════
# 5. HEADER + KPI TILES
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="eyebrow">Entrepreneurial Opportunity Zones · Andhra Pradesh · mandal level</div>',
            unsafe_allow_html=True)
st.markdown("## How well connected is each mandal by road?")
scope = ", ".join(districts) if districts else "All of Andhra Pradesh"
st.caption(f"{scope} · {len(df)} mandals shown · higher score = better connected · "
           f"the score is relative to the average analysed mandal (0)")

k = st.columns(5)
counts = df["con_level"].value_counts()
tiles = [("Mandals scored", len(analysed), None)] + [(lv, counts.get(lv, 0), LEVELS[lv][0]) for lv in LEVELS]
for col, (label, n, colour) in zip(k, tiles):
    sw = f'<span class="sw" style="background:{colour};border:1px solid #cfcdc6"></span>' if colour else ""
    share = f" · {n / len(df) * 100:.0f}%" if len(df) and colour else ""
    col.markdown(f'<div class="kpi"><div class="n">{n:,}</div><div class="l">{sw}{label}{share}</div></div>',
                 unsafe_allow_html=True)
st.write("")

tab_map, tab_compare, tab_rank, tab_regions, tab_about = st.tabs(
    ["🗺️  Map and mandal profile", "⚖️  Compare mandals", "📋  Rankings table", "🧭  Regions", "ℹ️  About the data"]
)


# ════════════════════════════════════════════════════════════════════════════
# 6. MAP
# ════════════════════════════════════════════════════════════════════════════
def hover_text(d):
    t = "<b>" + d["mandal_name"] + "</b><br>" + d["district_name"] + " district<br>"
    assessed = d["con_level"] != "Not assessed"
    body = np.where(
        assessed,
        d["con_level"] + " · " + d["con_region_name"].fillna("") + "<br>Score " +
        d["con_score"].map(fmt_score) + " (rank " + d["con_rank"].astype(str) + f" of {N_ANALYSED})",
        "Not assessed: no usable road data<br><i>(not the same as poor connectivity)</i>",
    )
    return t + body


def build_map(d, colour_by):
    fig = go.Figure()
    trace_lgd = []                       # which mandal each point of each trace is (for click selection)
    common = dict(geojson=MANDAL_GEO, featureidkey="properties.mandal_lgd",
                  marker_line_color="white", marker_line_width=0.35, hoverinfo="text")

    def add_cat(sub, colour, name):
        if sub.empty:
            return
        fig.add_trace(go.Choropleth(
            locations=sub["mandal_lgd"], z=np.ones(len(sub)), text=hover_text(sub),
            colorscale=[[0, colour], [1, colour]], showscale=False, name=name, showlegend=True, **common))
        trace_lgd.append(sub["mandal_lgd"].tolist())

    if colour_by == "Connectivity level":
        for lv, (colour, _) in LEVELS.items():
            add_cat(d[d["con_level"] == lv], colour, lv)
    elif colour_by.startswith("Connectivity region"):
        for r, (name, colour, *_) in REGIONS.items():
            add_cat(d[d["con_region"] == r], colour, f"{r} {name}")
        add_cat(d[d["con_level"] == "Not assessed"], NO_DATA, "No data")
    else:
        add_cat(d[d["con_level"] == "Not assessed"], NO_DATA_CONT, "No data")
        sub = d[d["con_level"] != "Not assessed"]
        if not sub.empty:
            if colour_by == "Connectivity score":
                z, title = sub["con_score"].clip(-2.1, 2.1), "Score"
                scale = [[0, "#ac1117"], [0.25, "#f3a481"], [0.5, "#f8f8f6"], [0.75, "#86b6ef"], [1, "#104281"]]
                zmin, zmax, ticks = -2.1, 2.1, dict(tickvals=[-2, -1, 0, 1, 2], ticktext=["−2", "−1", "0 avg", "+1", "+2"])
            else:
                col = "con_" + colour_by[:2]
                z, title = sub[col + "_pct"], "Percentile<br>(higher =<br>better)"
                scale = [[0, "#eef4fc"], [0.5, "#5598e7"], [1, "#0d366b"]]
                zmin, zmax, ticks = 0, 100, dict(tickvals=[0, 25, 50, 75, 100])
            text = hover_text(sub)
            if colour_by != "Connectivity score":
                text = text + "<br><b>" + VAR_BY_COL[col][1] + ": " + \
                    [fmt_value(col, v, c) for v, c in zip(sub[col], sub["con_city"])] + "</b>"
            fig.add_trace(go.Choropleth(
                locations=sub["mandal_lgd"], z=z, text=text, colorscale=scale, zmin=zmin, zmax=zmax,
                showlegend=False,
                colorbar=dict(title=dict(text=title, font=dict(size=11)), thickness=12, len=0.55,
                              x=0.99, y=0.5, outlinewidth=0, tickfont=dict(size=11), **ticks),
                **common))
            trace_lgd.append(sub["mandal_lgd"].tolist())

    # District outlines and names
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

    # Highlight the selected mandal
    sel = d[d["mandal_lgd"] == st.session_state.mandal_lgd]
    if not sel.empty:
        fig.add_trace(go.Choropleth(locations=sel["mandal_lgd"], z=[1], geojson=MANDAL_GEO,
                                    featureidkey="properties.mandal_lgd", colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                                    marker_line_color="#111", marker_line_width=2.2, showscale=False,
                                    hoverinfo="skip", showlegend=False))
        trace_lgd.append([])

    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        height=640, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="v", x=0.01, y=0.02, xanchor="left", yanchor="bottom",
                    bgcolor="rgba(255,255,255,0.85)", bordercolor="#e3e1da", borderwidth=1, font=dict(size=11),
                    itemclick="toggle", itemdoubleclick="toggleothers"),
        hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#cfcdc6"),
        dragmode=False,
    )
    return fig, trace_lgd


def profile_panel(lgd):
    row = df_all[df_all["mandal_lgd"] == lgd]
    if row.empty:
        st.info("Pick a mandal on the map or from the list above.")
        return
    r = row.iloc[0]
    colour = LEVELS[r["con_level"]][0]
    text_col = "#fff" if r["con_level"] in ("Well connected", "Poorly connected") else INK
    st.markdown(
        f'<div class="eyebrow">{r["district_name"]} district · {r["revenue_division"]} division · LGD {int(r["mandal_lgd"])}</div>'
        f'<h3 style="margin:.1rem 0 .4rem 0">{r["mandal_name"]}</h3>'
        f'<span class="pill" style="background:{colour};color:{text_col}">{r["con_level"]}</span>',
        unsafe_allow_html=True,
    )

    if r["con_level"] == "Not assessed":
        st.markdown(
            '<div class="note">This mandal could not be scored: one or more of the seven road measures is missing '
            '(for example, no village or bus records in the APRIS files, or under 20 km of town road mapped). '
            '<b>Unknown does not mean poor.</b> It needs data before any decision is taken here.</div>',
            unsafe_allow_html=True)
        return

    reg = int(r["con_region"])
    reg_name, reg_col, _, feature, helps = REGIONS[reg]
    reg_rows = analysed_all[analysed_all["con_region"] == reg]

    m1, m2, m3 = st.columns(3)
    m1.metric("Score", fmt_score(r["con_score"]),
              help="0 = the average analysed mandal. Positive = better connected than average.")
    m2.metric("Rank", f"{int(r['con_rank'])} of {N_ANALYSED}", help="1 = best connected.")
    m3.metric("Region median", fmt_score(reg_rows["con_score"].median()))
    st.markdown(
        f'<div class="muted"><span class="sw" style="display:inline-block;width:.65rem;height:.65rem;border-radius:2px;'
        f'background:{reg_col};margin-right:.35rem"></span>Region {reg}: <b>{reg_name}</b> · {feature}</div>',
        unsafe_allow_html=True)

    # Five percentage measures on one 0–100% axis, against state and region medians
    pct_vars = [v for v in VARIABLES if v[3] == "pct"]
    labels = [v[1] for v in pct_vars][::-1]
    vals = [r[v[0]] * 100 for v in pct_vars][::-1]
    state_med = [analysed_all[v[0]].median() * 100 for v in pct_vars][::-1]
    reg_med = [reg_rows[v[0]].median() * 100 for v in pct_vars][::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=vals, orientation="h", name="This mandal", marker_color=colour if colour != LEVELS["Average"][0] else "#8f8b80",
                         marker_line_width=0, width=0.5,
                         text=[f"{v:.0f}%" for v in vals], textposition="outside", cliponaxis=False,
                         textfont=dict(color=INK, size=11),
                         hovertemplate="%{y}: <b>%{x:.0f}%</b><extra>This mandal</extra>"))
    fig.add_trace(go.Scatter(y=labels, x=state_med, mode="markers", name="State median",
                             marker=dict(symbol="line-ns", size=18, line=dict(width=2.5, color=INK)),
                             hovertemplate="State median: %{x:.0f}%<extra></extra>"))
    fig.add_trace(go.Scatter(y=labels, x=reg_med, mode="markers", name="Region median",
                             marker=dict(symbol="diamond", size=9, color="white", line=dict(width=2, color=reg_col)),
                             hovertemplate="Region median: %{x:.0f}%<extra></extra>"))
    fig.update_layout(
        height=255, margin=dict(l=0, r=30, t=8, b=0), barcornerradius=4,
        xaxis=dict(range=[0, 108], ticksuffix="%", gridcolor="#efeee9", zeroline=False, tickfont=dict(size=10, color=MUTED)),
        yaxis=dict(tickfont=dict(size=11, color=INK2)),
        legend=dict(orientation="h", y=-0.17, x=0, font=dict(size=11)),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"prof_{lgd}")

    c1, c2 = st.columns(2)
    for c, (col, short, _, _, _) in zip((c1, c2), [v for v in VARIABLES if v[3] == "density"]):
        c.metric(f"{short} (km/100 km²)", fmt_value(col, r[col]))
        c.caption(f"State median {analysed_all[col].median():,.1f} · region median {reg_rows[col].median():,.1f}")

    notes = []
    if r["con_city"]:
        notes.append("City mandal: village access and bus service are assumed 100%, and road condition (marked *) "
                     "is the district median of rural mandals.")
    if r["con_flag_markapuram"]:
        notes.append("Markapuram district: road condition ratings look unreliable (nearly all road length rated "
                     "fair or better, against 25–30% in neighbours). Treat the condition measure with caution.")
    if r["con_n_outlier_vars"] and r["con_n_outlier_vars"] > 0 and not r["con_city"]:
        notes.append(f"{int(r['con_n_outlier_vars'])} of the seven measures is an outlier for this mandal. "
                     "It was kept: outliers here are real differences, not errors.")
    st.markdown(f'<div class="card"><h4>What would help most in this region</h4>{helps}'
                f'<div class="muted" style="margin-top:.35rem">Read off the region\'s weakest measure; an indication '
                f'for planning, not a costed recommendation.</div></div>', unsafe_allow_html=True)
    lv = r["con_level"]
    if lv in BUSINESS_BY_LEVEL:
        good, watch = BUSINESS_BY_LEVEL[lv]
        st.markdown(f'<div class="card"><h4>Businesses roads support here</h4>{good}'
                    f'<div class="muted" style="margin-top:.35rem"><b>Watch:</b> {watch}</div></div>',
                    unsafe_allow_html=True)
    for n in notes:
        st.markdown(f'<div class="note">{n}</div>', unsafe_allow_html=True)


with tab_map:
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        if df.empty:
            st.warning("No mandals match the filters. Pick at least one connectivity level.")
        else:
            fig, trace_lgd = build_map(df, colour_by)
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points",
                                    key="map", config=MAP_CONFIG)
            pts = (event or {}).get("selection", {}).get("points", []) if isinstance(event, dict) else \
                getattr(getattr(event, "selection", None), "points", [])
            if pts:
                p = pts[0]
                lgd = p.get("location")
                if lgd is None:
                    try:
                        lgd = trace_lgd[p["curve_number"]][p["point_index"]]
                    except (KeyError, IndexError, TypeError):
                        lgd = None
                if lgd is not None and int(lgd) != st.session_state.mandal_lgd:
                    st.session_state.mandal_lgd = int(lgd)
                    st.rerun()
            st.caption("Hover for details · **click a mandal** to open its profile · click a legend item to hide it.")
    with right:
        options = (df if not df.empty else df_all).sort_values(["district_name", "mandal_name"])
        labels = options["label"].tolist()
        lgds = options["mandal_lgd"].tolist()
        cur = lgds.index(st.session_state.mandal_lgd) if st.session_state.mandal_lgd in lgds else 0
        chosen = st.selectbox("Find a mandal", labels, index=cur, help="Type to search by mandal or district name.")
        if lgds[labels.index(chosen)] != st.session_state.mandal_lgd:
            st.session_state.mandal_lgd = lgds[labels.index(chosen)]
            st.rerun()
        profile_panel(st.session_state.mandal_lgd)


# ════════════════════════════════════════════════════════════════════════════
# 7. COMPARE
# ════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("#### Compare up to five mandals side by side")
    st.caption("Bars show each mandal's **percentile** among the 612 scored mandals (100 = best), so measures with "
               "different units sit on one scale. Actual values are in the table below.")
    pool = analysed_all.sort_values(["district_name", "mandal_name"])
    default = [l for l in [st.session_state.mandal_lgd] if l in pool["mandal_lgd"].values]
    for extra in analysed.sort_values("con_rank")["mandal_lgd"].tolist()[:2] + [int(analysed_all.sort_values("con_rank").iloc[-1]["mandal_lgd"])]:
        if extra not in default and len(default) < 3:
            default.append(extra)
    lab_by_lgd = dict(zip(pool["mandal_lgd"], pool["label"]))
    picked = st.multiselect("Mandals", pool["mandal_lgd"].tolist(), default=default, max_selections=5,
                            format_func=lambda x: lab_by_lgd.get(x, str(x)))
    if picked:
        sub = analysed_all.set_index("mandal_lgd").loc[picked]
        names = [f"{s['mandal_name']} ({s['district_name']})" for _, s in sub.iterrows()]
        cats = [v[1] for v in VARIABLES]
        fig = go.Figure()
        for i, (lgd, s) in enumerate(sub.iterrows()):
            fig.add_trace(go.Bar(
                x=cats, y=[s[v[0] + "_pct"] for v in VARIABLES], name=names[i],
                marker_color=COMPARE_COLOURS[i], marker_line_color="white", marker_line_width=2,
                customdata=[fmt_value(v[0], s[v[0]], s["con_city"]) for v in VARIABLES],
                hovertemplate="<b>" + names[i] + "</b><br>%{x}: %{customdata}<br>Percentile %{y:.0f}<extra></extra>"))
        fig.add_hline(y=50, line_dash="dot", line_color=MUTED, annotation_text="state median",
                      annotation_position="bottom left", annotation_font=dict(size=10, color=MUTED))
        fig.update_layout(
            barmode="group", height=380, margin=dict(l=0, r=0, t=10, b=0), barcornerradius=4, bargap=0.25,
            yaxis=dict(range=[0, 105], title="Percentile (higher = better)", gridcolor="#efeee9",
                       tickfont=dict(size=10, color=MUTED), title_font=dict(size=11, color=INK2)),
            xaxis=dict(tickfont=dict(size=11, color=INK2)),
            legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        table = pd.DataFrame({"Measure": ["Connectivity level", "Region", "Score", f"Rank (of {N_ANALYSED})"] +
                              [f"{v[0][-2:]} {v[2]}" for v in VARIABLES]})
        for name, (lgd, s) in zip(names, sub.iterrows()):
            table[name] = [s["con_level"], s["con_region_name"], fmt_score(s["con_score"]), str(int(s["con_rank"]))] + \
                          [fmt_value(v[0], s[v[0]], s["con_city"]) for v in VARIABLES]
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.caption("* City estimate: condition is the district median of rural mandals.")
    else:
        st.info("Pick one or more mandals to compare.")


# ════════════════════════════════════════════════════════════════════════════
# 8. RANKINGS TABLE
# ════════════════════════════════════════════════════════════════════════════
with tab_rank:
    st.markdown("#### All mandals, ranked")
    st.caption("Follows the district and level filters in the sidebar. Click a column header to sort. "
               "Not-assessed mandals are listed at the bottom with no score.")
    t = df.sort_values(["con_rank", "district_name", "mandal_name"], na_position="last")
    out = pd.DataFrame({
        "Rank": t["con_rank"],
        "Mandal": t["mandal_name"],
        "District": t["district_name"],
        "Level": t["con_level"],
        "Region": t["con_region_name"],
        "Score": t["con_score"].round(2),
        "City": t["con_city"].map({True: "Yes", False: ""}),
    })
    for col, short, full, kind, w in VARIABLES:
        out[f"{col[-2:]} {short}"] = (t[col] * 100).round(1) if kind == "pct" else t[col].round(1)
    out["LGD code"] = t["mandal_lgd"]

    cfg = {
        "Rank": st.column_config.NumberColumn(format="%d", width="small"),
        "Score": st.column_config.NumberColumn(format="%+.2f", help="0 = average analysed mandal"),
        "LGD code": st.column_config.NumberColumn(format="%d"),
    }
    for col, short, full, kind, w in VARIABLES:
        key = f"{col[-2:]} {short}"
        if kind == "pct":
            cfg[key] = st.column_config.ProgressColumn(key, help=full, format="%.0f%%", min_value=0, max_value=100)
        else:
            cfg[key] = st.column_config.NumberColumn(key, help=full, format="%.1f")
    st.dataframe(out, hide_index=True, use_container_width=True, height=560, column_config=cfg)

    d1, d2 = st.columns([1, 3])
    d1.download_button("⬇ Download this table (CSV)", out.to_csv(index=False).encode("utf-8-sig"),
                       file_name="connectivity_mandals_filtered.csv", mime="text/csv", use_container_width=True)
    d2.caption("Percentages are shown as 0–100. Densities are km per 100 km². The LGD code joins this table to the "
               "other pillars.")


# ════════════════════════════════════════════════════════════════════════════
# 9. REGIONS
# ════════════════════════════════════════════════════════════════════════════
with tab_regions:
    st.markdown("#### The eight connectivity regions")
    st.caption("Regions are blocks of neighbouring mandals with similar road profiles (Ward clustering restricted to "
               "neighbours). Borders are approximate: use each mandal's own score for local decisions.")
    rows = []
    for rnum, (name, colour, districts_txt, feature, helps) in REGIONS.items():
        g = analysed_all[analysed_all["con_region"] == rnum]
        rows.append(dict(rnum=rnum, name=name, colour=colour, n=len(g), med=g["con_score"].median(),
                         level=g["con_level"].iloc[0], districts=districts_txt, feature=feature, helps=helps,
                         **{v[0]: g[v[0]].median() for v in VARIABLES}))
    R = pd.DataFrame(rows)

    a, b = st.columns([1, 1.25], gap="large")
    with a:
        Rs = R.sort_values("med")
        fig = go.Figure(go.Bar(
            y=[f"{x.rnum}  {x.name}" for x in Rs.itertuples()], x=Rs["med"], orientation="h",
            marker_color=Rs["colour"], marker_line_width=0, width=0.6,
            text=[f"{v:+.2f}" for v in Rs["med"]], textposition="outside", cliponaxis=False,
            textfont=dict(color=INK, size=11),
            customdata=np.stack([Rs["n"], Rs["level"]], axis=1),
            hovertemplate="<b>%{y}</b><br>Median score %{x:+.2f}<br>%{customdata[0]} mandals · %{customdata[1]}<extra></extra>"))
        fig.add_vline(x=0, line_color=MUTED, line_width=1)
        fig.update_layout(height=360, margin=dict(l=0, r=10, t=26, b=0), barcornerradius=4,
                          title=dict(text="Median connectivity score by region", font=dict(size=13, color=INK), x=0),
                          xaxis=dict(range=[-1.75, 2.75], gridcolor="#efeee9", zeroline=False, tickfont=dict(size=10, color=MUTED)),
                          yaxis=dict(tickfont=dict(size=11, color=INK2)),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with b:
        st.markdown("**What connectivity means for different kinds of business**")
        st.caption("Roads matter most for agriculture, livestock and dairy, and food processing (bulky or perishable "
                   "goods), and somewhat less for textiles, crafts and rural services.")
        for lv, (good, watch) in BUSINESS_BY_LEVEL.items():
            st.markdown(f'<div class="card" style="border-left:4px solid {LEVELS[lv][0]}"><h4>{lv}</h4>'
                        f'<div style="font-size:.88rem">{good}</div>'
                        f'<div class="muted" style="margin-top:.3rem"><b>Watch:</b> {watch}</div></div>',
                        unsafe_allow_html=True)

    st.markdown("##### Typical mandal in each region (medians)")
    prof = pd.DataFrame({
        "#": R["rnum"], "Region": R["name"], "Level": R["level"], "Mandals": R["n"],
        "Median score": [fmt_score(x) for x in R["med"]],
        **{v[0][-2:]: [fmt_value(v[0], x) for x in R[v[0]]] for v in VARIABLES},
    })
    st.dataframe(prof, hide_index=True, use_container_width=True,
                 column_config={v[0][-2:]: st.column_config.TextColumn(help=v[2]) for v in VARIABLES})
    st.caption(" · ".join(f"**{v[0][-2:]}** {v[1].lower()}" for v in VARIABLES) +
               ". C6 and C7 are km per 100 km². City condition values (C5) are estimates.")

    st.markdown("##### Region by region, in plain terms")
    cols = st.columns(4)
    for i, x in enumerate(R.itertuples()):
        with cols[i % 4]:
            st.markdown(
                f'<div class="card" style="border-top:4px solid {x.colour}">'
                f'<div class="eyebrow">Region {x.rnum} · {x.level}</div><h4>{x.name}</h4>'
                f'<div class="muted">{x.n} mandals · median {x.med:+.2f} · {x.districts}</div>'
                f'<div style="margin-top:.4rem;font-size:.88rem">{x.feature}</div>'
                f'<div style="margin-top:.4rem;font-size:.88rem"><b>Would help most:</b> {x.helps}</div></div>',
                unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# 10. ABOUT
# ════════════════════════════════════════════════════════════════════════════
with tab_about:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### What this dashboard shows")
        st.markdown(
            "Problem Statement 2 asks **where** women's self-help groups in Andhra Pradesh have the best conditions "
            "to start and grow enterprises, and **for which businesses**. The Connectivity pillar answers one part: "
            "*can raw materials come in and products go out easily?* It will sit beside the Water, Electricity and "
            "Agricultural market-access pillars, which are combined later into opportunity zones."
        )
        st.markdown("#### How the score was built")
        st.markdown(
            "- **Seven road measures** per mandal (below), screened from 20 candidates.\n"
            "- **PCA** reduces them to four components (77.8% of the variation).\n"
            "- **Score** = 0.423·PC1 + 0.247·PC2 + 0.198·PC3 + 0.132·PC4. Each component is oriented so the score "
            "rises with every measure. Mean 0 = average analysed mandal.\n"
            "- **Regions**: Ward clustering of the four components, allowing only neighbouring mandals to join, "
            "gives eight contiguous regions, grouped into three plain-language levels.\n"
            "- **Checks**: CRITIC weighting ranks mandals almost identically (rank correlation 0.94); the score "
            "agrees with a measure held out of it (people within 500 m of a road, ρ = 0.53)."
        )
        st.markdown("#### The seven measures")
        st.dataframe(pd.DataFrame([{"Code": c[-2:], "Measure": full, "Weight in score": f"{w}%"}
                                   for c, short, full, kind, w in VARIABLES]),
                     hide_index=True, use_container_width=True)
    with b:
        st.markdown("#### Points to keep in mind")
        st.markdown(
            "- **Grey means no data, not poor roads.** 76 of 688 mandals are not assessed, mostly the old "
            "Visakhapatnam district (Anakapalli 24, Alluri Sitharama Raju 11, Visakhapatnam 4) where village and bus "
            "records are blank; 25 miss one measure; 12 cities have too little town-road data.\n"
            "- **City values are partly assumed.** For the 15 city mandals, village access and bus service are set "
            "to 100% and road condition is the district median of rural mandals.\n"
            "- **Markapuram condition ratings look unreliable** (flagged in the profile panel).\n"
            "- **Levels come from regions.** Each mandal takes the level of its region, so a few strong mandals sit "
            "in an \"Average\" region (for example Vizianagaram Urban, rank 3). Check the mandal's own score and rank.\n"
            "- **Region borders are approximate.** Leaving one measure out keeps the broad pattern but moves borders. "
            "Use each mandal's own score for local decisions.\n"
            "- **Not yet measured:** district roads, travel time and bus frequency. APRIS is one snapshot.\n"
            "- **Roads are one of five pillars.** This is a proof of concept; the final opportunity zones combine all "
            "of them."
        )
        st.markdown("#### Data sources")
        st.dataframe(pd.DataFrame([
            ("Mandal boundaries", "APSDMA GIS (AP_Mandals_688), LGD codes", "688 mandals"),
            ("Village roads and sections", "APRIS road master and road surface (APSAC)", "31,853 roads; 44,531 sections"),
            ("Habitations", "APRIS habitation file (APSAC)", "48,869"),
            ("Town roads", "APSDMA municipal roads", "18,635 km, 95 towns"),
            ("National and state highways", "APSDMA transport layers", "3,259 km NH; 13,242 km SH"),
        ], columns=["Data", "Source", "Records"]), hide_index=True, use_container_width=True)
        st.caption("Full method and tables: Connectivity (Roads) Pillar report and notebook, October 2026. "
                   "SERP × ISB capstone.")
