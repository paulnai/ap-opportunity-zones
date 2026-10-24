"""Matches files that have no LGD code (Livestock, Aquaculture, Rural services) to the 688 official mandals by name."""
import re, difflib
import pandas as pd

n = lambda s: re.sub(r"[^a-z]", "", str(s).lower())
DISTRICT_ALIAS = {"konaseema": "drbrambedkarkonaseema", "vishakapatnam": "visakhapatnam",
                  "anantapuramu": "ananthapuramu", "anantapur": "ananthapuramu",
                  "nellore": "sripottisriramulunellore", "kadapa": "ysrkadapa"}
# Hand-checked spellings that string similarity cannot resolve (file key -> official mandal key)
MANDAL_ALIAS = {
    "rajamahendravaramurban": "rajahmundryfullyurban",
    "rajamahendravaramrural": "rajahmundryrural", "visakhapatnamrural": "visakhapatnamr",
    "ukothapalli": "kothapalle", "kganagavaram": "kgangavaram",
    # renamed / abbreviated mandals
    "gaddamanugukonduru": "gkonduru", "atlapragadakonduru": "akonduru", "beerongikothakota": "bkothakota",
    "kumaravenkatabhupalapuram": "kvbpuram", "valmikipuram": "vayalpadu",
    "bksamudram": "bukkarayasamudram", "odcheruvu": "obuladevaracheruvu",
    # towns the official map splits into urban + rural parts: the single record goes to the original LGD code
    "eluru": "elururural", "ongole": "ongolerural", "nandyal": "nandyalrural",
    "machilipatnam": "machilipatnamsouth", "chittoor": "chittoorrural", "anantapur": "anantapurrural",
    "vizianagaram": "vizianagaramrural",
}

def build(mandals: pd.DataFrame, df: pd.DataFrame, dcol: str, mcol: str):
    m = mandals.assign(dk=mandals.district_name.map(n), mk=mandals.mandal_name.map(n))
    d = df.assign(dk=df[dcol].map(n).map(lambda x: DISTRICT_ALIAS.get(x, x)),
                  mk=df[mcol].map(n).map(lambda x: MANDAL_ALIAS.get(x, x)))
    out, how = [], []
    for _, r in d.iterrows():
        cand = m[m.dk == r.dk]
        hit = cand[cand.mk == r.mk]
        h = "exact"
        if hit.empty:
            close = difflib.get_close_matches(r.mk, cand.mk.tolist(), 1, 0.75)
            hit, h = (cand[cand.mk == close[0]], "close spelling") if close else (hit, "")
        if hit.empty:  # same name in another district (district boundaries redrawn)
            hit = m[m.mk == r.mk]; h = "other district" if len(hit) == 1 else ""
            if len(hit) != 1: hit = hit.iloc[0:0]
        out.append(int(hit.mandal_lgd.iloc[0]) if len(hit) else None); how.append(h or "unmatched")
    return pd.Series(out, index=df.index, dtype="Int64"), pd.Series(how, index=df.index)
