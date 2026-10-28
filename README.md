# AP Opportunity Zones Explorer

An interactive dashboard for exploring the results of **Problem Statement 2: Entrepreneurial Opportunity Zones**
(ISB AMPBA capstone with SERP, Government of Andhra Pradesh). It follows the four pillars and four business areas finalised for the project.

## What's in it

**Opening page: Andhra Pradesh.** When the dashboard loads, no *Section* is selected and the page shows
"Infrastructure & Business Opportunity Overview": two maps side by side. Left: each mandal's strongest
infrastructure pillar. Right: each mandal's strongest business area (opportunity scores). Each map has a short
heading and caption beside its title, its legend top-left and one line underneath; these two maps have no hover
box. This page always shows the whole state (no district filter). Pick
*Infrastructure pillars* or *Business areas* in the sidebar to explore one in depth; "↩ Back to the Andhra Pradesh
overview" in the sidebar returns here. The two sections open on "Andhra Pradesh Infrastructure Overview" and
"Andhra Pradesh Business Opportunity Overview".

**How many are strong.** *Colour the map by → How many pillars are strong* (or *How many business areas are
strong*) shades each mandal from "Strong on all 4 pillars" to "Not strong on any pillar" (strong = top third of
the state). Hovering a mandal shows its name, district and which pillars (or business areas) are strong. Grey
areas read "Data not available".

Built around the professor's review on 24 October 2026:

- **One infrastructure pillar on the map at a time** (Water, Electricity, Connectivity, Market access), in three
  simple levels: High, Medium, Low, plus grey for no data.
- **Each mandal's performance across all four pillars**, side by side in its profile, in the compare view and
  in the "All mandals" table.

**Opening view.** *Pillar on the map* starts blank, and the state map shows the four pillars read together:
each mandal is coloured by its **strongest pillar** (Water blue, Electricity amber, Connectivity teal, Market
access purple), among the pillars where it is in the top third; pale = High on no pillar. Pillars are compared only across the
323 mandals with data on all four, ranked among themselves; other mandals are grey. The figures at the top give
the total number of mandals, then for each pillar the number at High out of those 323.
*Colour the map by* can also show How many pillars are strong or Weakest pillar.

**Pillar on the map.** Pick Connectivity, Electricity, Water or Market access from the drop-down to see one
pillar on its own; clear it to return to the opening view. Colour by Level (High / Medium / Low), Regions (the pillar's spatially
constrained clusters), Level within the district, or A single measure (Electricity's come from
`source/electricity_geo_axis.csv`).

**Districts and Find a mandal (both sections).** Both sit in the right-hand column, in Infrastructure pillars and in Business areas. Pick one or more districts;
*Find a mandal* then appears next to it and lists only those districts' mandals. Both boxes can be cleared with ×.
Clicking a mandal on the map also selects it and adds its district.

**Selecting a mandal (Infrastructure).** The map shows **only that mandal**, outlined in black, with its
neighbours as faint, clickable outlines. The mandal is split into four equal parts, one per pillar, each in its
pillar's level colour (High blue, Medium grey, Low red, No data white); pillars at the same level sit together, so
two Low pillars make half the mandal red. Hover a colour to list its pillars. The split is only a way to show four
values on one shape, not a statement about where in the mandal each value applies. While a mandal is selected the
sidebar hides the map options and the pillar box becomes *Pillar details* (which pillar's measures the profile
lists). **Back to the district map** or clearing *Find a mandal* returns to the district map. The profile cards on
the right give the exact scores and ranks, and **Recommended Business Areas for this Mandal** lists the four
business areas from the strongest level down (★ = High). Neighbours come from `data/mandal_neighbours.csv` and the
four parts from `data/mandal_parts.geojson` (both precomputed from the mandal boundaries).

**Regions tab.** For the pillar (or business area) picked in the sidebar: a map of its regions (or zones) on top,
in the same colours as the *Regions* map option, and the table below with each row in its map colour.

**Compare mandals.** Pick up to five mandals, then *Compare on*: **Infrastructure pillars** (the four pillars only,
in blue), **Business areas** (the four opportunity scores only, in orange) or **Choose my own** (tick any mix of the
eight on one line; pillars stay blue and business areas orange). Each group of bars is one mandal; the table below
shows level · score for the same choice, with blue rows for pillars and orange rows for business areas.
Percentiles and levels here are among the 323 mandals with data on all four pillars.

**Levels.** Each pillar's score is turned into a percentile and split into thirds: High is the top third of the
mandals with data on that pillar (Connectivity included). Views that compare pillars use only the 323 mandals with
data on all four, re-ranked among themselves.

**Business areas** (second section): Agriculture, Livestock, Rural Services and Aquaculture.

- **Opening view.** *Business area* starts blank. The map colours each mandal by its **strongest business area**
  (top third of the opportunity score); the figures at the top give the total number of mandals and, for
  each business, the number at High. *Colour the map by* can also show Number of business areas at High (0–4).
- **One business area.** The map shows the **opportunity score** (0–100), or its five **opportunity zones**, from the Integrated clustering
  reports: the business's own data combined with the infrastructure pillars, weighted equally. ★ marks the
  top 15 pilot mandals. *A single measure* includes the **business activity score** (the earlier score from
  business data only, 679 mandals) and its inputs.
- **Districts and Find a mandal** work as in Infrastructure pillars: Districts in the right-hand column, and *Find a mandal* appears once a district is picked, listing only its mandals.
- **Selecting a mandal.** "↩ Back to the state map" sits above the map. Under the map, side by side:
  ① **Infrastructure check** — what the business needs from each pillar against what the mandal has (Meets /
  Partly / Gap / Unknown) and a verdict (Suitable, Partly suitable, Not suitable); ② **Opportunity score** — score,
  rank, level, zone, possible SHG enterprises and support range. With no business picked, one line per business.
- **Regions tab.** The five opportunity zones per business, with possible SHG enterprises and support ranges,
  and the top 15 pilot mandals.
- What each business needs (High / Medium / Low per pillar) is a set of assumed requirements, used only for the
  infrastructure check. They can be made more accurate with expert weights.

| Layer | Mandals with data |
|---|---|
| Connectivity · Electricity · Water · Market access | 612 · 397 · 661 · 688 |
| Agriculture · Livestock · Rural Services · Aquaculture: opportunity score | 323 each |
| Livestock · Rural Services · Aquaculture: business activity score | 679 each |

**Grey on every map means no data, never a low score.**

---

## Run it on your laptop

Once: install Python from <https://www.python.org/downloads/> (on Windows tick **"Add Python to PATH"**), unzip
this folder, open a terminal in it (Windows: click the folder's address bar, type `cmd`, press Enter) and run:
```
pip install -r requirements.txt
```
Each time:
```
streamlit run app.py
```
Your browser opens the dashboard. Press **Ctrl + C** in the terminal to stop it.

## Publish it as a link (free)

1. On <https://github.com>, create a repository (choose **Private** if the data should not be public).
2. Click **uploading an existing file** and drag in **everything inside** this folder, including the folders
   `data`, `static`, `source` and `.streamlit` (on a Mac, press Cmd + Shift + . to see `.streamlit`). Commit.
3. On <https://share.streamlit.io>, sign in with GitHub, click **Create app**, choose the repository, set the main
   file to `app.py`, and click **Deploy**. The link appears in your browser's address bar after a few minutes.

If you already published an earlier version, upload these files over the old ones in the same repository.
The link stays the same and the app updates itself.

---

## Folder contents

| File / folder | What it is |
|---|---|
| `app.py` | The dashboard. Labels, colours, caveats, business needs and zone texts are in **Section 1, Settings**. |
| `data/` | Prepared data: one row per mandal with every layer, keyed by LGD code; map shapes; `name_matching.csv`. |
| `prepare_data.py`, `crosswalk.py` | Rebuild `data/` from `source/`. Needed only when a result file changes. |
| `source/` | Each analysis result file as received. `source/integrated/` holds the four opportunity-score files from the Integrated clustering folder; the app reads them directly. |
| `static/`, `.streamlit/` | Base map file and app settings. |

## Notes on the data

- **Electricity** covers 397 mandals (APEPDCL and APCPDCL territory). Its score is PC1, as the Electricity report
  recommends. The opportunity scores need all four pillars, so they cover 323 mandals; the south is grey on the
  business maps.
- **Livestock, Rural Services and Aquaculture** files have no LGD code. They were matched by mandal and district
  name: 611 exact, 68 spelling variants checked by hand. Towns later split into urban and rural parts take the
  original LGD code. See `data/name_matching.csv`.
- **Aquaculture:** Shareen's final notebook re-run unchanged. The output matches her 679-mandal report (six
  regions: Delta Core 72, Inland Baseline 567, Brackish Frontier 12, North Marine Landing 11, Estuarine Creek 10,
  Southern Saline 7).
- **Opportunity scores (Integrated clustering):** four files, 323 mandals each, with LGD codes; zone counts match
  the reports. The Agriculture file is identical to the earlier one. Rural Services and Aquaculture do not use the
  Market access pillar. The Agriculture CSV's mean (45.62) differs slightly from its report (45.96).
- **Cold storage** is not part of the final framework and has been removed.
