# AP Opportunity Zones Explorer

An interactive dashboard for exploring the results of **Problem Statement 2: Entrepreneurial Opportunity Zones**
(ISB AMPBA capstone with SERP, Government of Andhra Pradesh). It follows the four pillars and four business areas finalised by the team.

## What's in it

Built around the professor's review on 24 October 2026:

- **One infrastructure pillar on the map at a time** (Water, Electricity, Connectivity, Market access), in three
  simple levels: High, Medium, Low, plus grey for no data.
- **Each mandal's performance across all four pillars**, side by side in its profile, in the compare view and
  in the "All mandals" table.

**Pillar on the map.** Connectivity, Electricity, Water or Market access.

**Colour the map by.**
- For the chosen pillar: Level (High / Medium / Low), Score (shading), Level within the district, or A single
  measure (not for Electricity, whose file has no raw measures).
- All four pillars: number at High (0–4), or data coverage (0–4). These read all four pillars together, so the
  pillar picked above does not change the map. Every pillar, Connectivity included, is split into thirds here.

**Weakest pillar.** Each mandal's weakest pillar (lowest percentile among its pillars in the bottom third) is shown
in its profile, in the hover of the all-pillar views, and as a column and filter in the All mandals table. It is not
a map colour, to keep every map to three colours or one shaded colour.

**Levels.** Connectivity keeps the levels from its report (Well connected, Average, Poorly connected). The other
pillars split their scored mandals into thirds: High is the top third of mandals with data.

**Business areas** (second section): Agriculture, Livestock, Rural Services and Aquaculture. Each has the team's
own analysis and a **draft opportunity score** that combines the four pillars with draft weights (Low 1, Medium 2,
High 3). Agriculture, Livestock and Rural Services use slide 14 of the mid-review deck. Aquaculture uses Claude's
suggested ratings, approved by Nairita and pending team review (Water High, Electricity High, Connectivity
Medium/High, Market access Medium).

| Layer | Mandals with data |
|---|---|
| Connectivity · Electricity · Water · Market access | 612 · 397 · 661 · 688 |
| Agriculture · Livestock · Rural Services · Aquaculture | 323 · 679 · 679 · 679 |

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
| `app.py` | The dashboard. Labels, colours, caveats and draft weights are in **Section 1, Settings**. |
| `data/` | Prepared data: one row per mandal with every layer, keyed by LGD code; map shapes; `name_matching.csv`. |
| `prepare_data.py`, `crosswalk.py` | Rebuild `data/` from `source/`. Needed only when a team's results change. |
| `source/` | Each team's result file as received (Aquaculture: Shareen's final notebook re-run unchanged). |
| `static/`, `.streamlit/` | Base map file and app settings. |

## Notes on the data

- **Electricity** covers 397 mandals (APEPDCL and APCPDCL territory). Its score is PC1, as the Electricity report
  recommends. The Agriculture composite and the draft scores therefore need the "without Electricity" switch to
  cover the south.
- **Livestock, Rural Services and Aquaculture** files have no LGD code. They were matched by mandal and district
  name: 611 exact, 68 spelling variants checked by hand. Towns later split into urban and rural parts take the
  original LGD code. See `data/name_matching.csv`.
- **Aquaculture:** Shareen's final notebook re-run unchanged. The output matches her 679-mandal report (six
  regions: Delta Core 72, Inland Baseline 567, Brackish Frontier 12, North Marine Landing 11, Estuarine Creek 10,
  Southern Saline 7).
- **Cold storage** is not part of the final framework and has been removed.
