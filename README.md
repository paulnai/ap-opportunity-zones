# AP Opportunity Zones Explorer (proof of concept)

An interactive dashboard for exploring the results of **Problem Statement 2: Entrepreneurial Opportunity Zones**
(ISB AMPBA capstone with SERP, Government of Andhra Pradesh).

This first version covers the **Connectivity (Roads) pillar**: 688 mandals, of which 612 are scored, with eight
regions and three connectivity levels. The numbers are the same as in the Connectivity report (October 2026).

## What it does

| Tab | What you can do |
|---|---|
| **Map and mandal profile** | Colour the map by connectivity level, region, score, or any of the seven road measures. Hover to see details. Click a mandal, or search for one, to see its profile: score, rank, how it compares with the state and its region, what would help most, and which businesses roads support there. |
| **Compare mandals** | Put up to five mandals side by side. |
| **Rankings table** | All mandals ranked, sortable, and downloadable as a CSV file. |
| **Regions** | The eight regions, their typical mandal, and what connectivity means for different businesses. |
| **About the data** | Method, sources, and the caveats from the report. |

The sidebar filters (districts and connectivity level) apply to every tab.
**Grey on every map means no data, never poor connectivity.**

---

## Option A: Run it on your own laptop

Do this once:

1. **Install Python.** Download it from <https://www.python.org/downloads/> and run the installer.
   On Windows, tick **"Add Python to PATH"** on the first screen of the installer.
2. **Unzip this folder** somewhere easy to find, for example your Desktop.
3. **Open a terminal in the folder:**
   - *Windows:* open the folder in File Explorer, click in the address bar, type `cmd` and press Enter.
   - *Mac:* right-click the folder in Finder, then choose **Services → New Terminal at Folder**.
4. **Install the libraries** by typing this and pressing Enter (it takes a minute or two):
   ```
   pip install -r requirements.txt
   ```
   If `pip` is not recognised, use `python -m pip install -r requirements.txt` instead (on a Mac, `python3 -m pip ...`).

Each time you want to open the dashboard:

5. In the same terminal, type:
   ```
   streamlit run app.py
   ```
   Your browser opens the dashboard at `http://localhost:8501`.
   To stop it, go back to the terminal and press **Ctrl + C**.

## Option B: Publish it as a link for the team (free)

Streamlit Community Cloud hosts the dashboard and gives you a web link that anyone can open in a browser,
with nothing to install.

1. **Create a GitHub account** at <https://github.com> if you don't have one.
2. **Create a new repository:** click **+ → New repository**, name it for example `ap-opportunity-zones`, and choose
   **Private** if the team does not want the data public. Click **Create repository**.
3. **Upload the files:** on the new repository page, click **uploading an existing file**. Drag in **everything inside**
   this folder (`app.py`, `requirements.txt`, `README.md`, `prepare_data.py`, and the folders `data`, `static`,
   `source` and `.streamlit`), then click **Commit changes**.
   - The `.streamlit` folder is hidden on a Mac. In Finder, press **Cmd + Shift + .** (full stop) to show it.
4. **Deploy:** go to <https://share.streamlit.io>, sign in with GitHub, click **Create app**, then
   **Deploy a public app from GitHub**. Choose your repository, set **Main file path** to `app.py`, and click **Deploy**.
5. After a few minutes you get a link like `https://ap-opportunity-zones.streamlit.app`. Share it with the team.
   - For a private repository, invite viewers by email from the app's **Share** button.
   - If nobody opens the app for a few days it goes to sleep. Whoever opens the link next clicks **"Yes, get this app back up"** and it starts again in under a minute.

---

## What's in the folder

| File / folder | What it is |
|---|---|
| `app.py` | The dashboard itself. All labels, colours and text are in **Section 1, Settings**, at the top. |
| `data/` | The prepared data the dashboard reads: one row per mandal, keyed by LGD code, plus simplified map shapes. |
| `prepare_data.py` | Rebuilds `data/` from the raw outputs in `source/`. Needed only when results change or a pillar is added. |
| `source/` | The raw outputs: `connectivity_mandal_results.csv` (from the notebook) and `AP_Mandals_688.geojson`. |
| `static/` | The base map file, so the map loads even on networks that block outside websites. |
| `.streamlit/config.toml` | Colours and server settings. |
| `requirements.txt` | The Python libraries the dashboard needs. |

## Adding the other pillars later

The dashboard is built so Electricity, Water infrastructure, Water availability and Agricultural market access can
be added the same way as Connectivity: each pillar's mandal results file goes into `source/` and is joined on the
**LGD mandal code**. When a pillar is final, share its results file (CSV or Excel, with the LGD code in each row)
together with this folder, and the dashboard can be extended.
