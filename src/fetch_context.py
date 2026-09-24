#!/usr/bin/env python3
"""Fetch the city-wide context the page compares the cherries against.

Three things, all from DC GIS:

  1. every genus x wire-status x ward count over the whole 222k-tree inventory
     (server-side groupBy - no need to download 222,000 rows to get the ladder
     chart and the ward correlation);
  2. ward boundaries (Ward - 2022);
  3. hydrography polygons, so the river is visible on the map.

    python src/fetch_context.py src/data/

Both boundary layers are simplified here rather than in the browser: the raw ward
polygons are ~1 MB and the page only needs a recognisable outline.
"""
import json, os, sys, time, urllib.parse, urllib.request

TREES = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/"
         "Urban_Tree_Canopy/MapServer/23/query")
WARDS = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/"
         "Administrative_Other_Boundaries_WebMercator/MapServer/53/query")
WATER = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/"
         "Environment_Water_WebMercator/MapServer/24/query")


def get(base, **kw):
    kw.setdefault("f", "json")
    url = base + "?" + urllib.parse.urlencode(kw)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return json.load(r)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))


def genus_wire_ward():
    d = get(TREES, where="1=1", groupByFieldsForStatistics="GENUS_NAME,WIRES,WARD",
            outStatistics=json.dumps([{"statisticType": "count",
                                       "onStatisticField": "OBJECTID",
                                       "outStatisticFieldName": "n"}]),
            returnGeometry="false")
    out = []
    for f in d["features"]:
        a = {k.upper(): v for k, v in f["attributes"].items()}
        out.append({"genus": a.get("GENUS_NAME"),
                    # the inventory has both "None" and "None " for no wire
                    "wires": (a.get("WIRES") or "None").strip(),
                    "ward": a.get("WARD"), "n": a["N"]})
    return out


def rings(base, where="1=1", tol=0.00012, out_fields="*"):
    d = get(base, where=where, outFields=out_fields, returnGeometry="true",
            outSR="4326", geometryPrecision="5",
            maxAllowableOffset=str(tol))
    feats = []
    for f in d["features"]:
        g = f.get("geometry") or {}
        if g.get("rings"):
            feats.append({"attributes": f["attributes"], "rings": g["rings"]})
    return feats


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name, payload in (
        ("city_counts.json", genus_wire_ward()),
        ("wards.json",  rings(WARDS, out_fields="WARD,NAME")),
        # only the big water bodies; the creeks are noise at this scale
        ("water.json",  rings(WATER, where="1=1", tol=0.0002,
                      out_fields="DESCRIPTION")),
    ):
        p = os.path.join(outdir, name)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh)
        print(f"wrote {p} ({len(payload)} records)", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "src/data")
