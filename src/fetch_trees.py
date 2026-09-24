#!/usr/bin/env python3
"""Download every Prunus record from the DC street-tree inventory.

Source: DC GIS, Urban Tree Canopy map service, layer 23 "UFA Street Trees" -
the District Department of Transportation Urban Forestry Division's inventory of
every tree in public space. ~222,000 records, of which ~12,900 are Prunus.

    python src/fetch_trees.py src/data/dc_prunus_raw.json

The service caps a query at 2,000 records, so this pages by OBJECTID. Geometry is
requested in WGS84 (outSR=4326); the service's own projection is Web Mercator.
"""
import json, os, sys, time, urllib.parse, urllib.request

BASE = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/"
        "Urban_Tree_Canopy/MapServer/23/query")
FIELDS = ("OBJECTID,SCI_NM,CMMN_NM,GENUS_NAME,DATE_PLANT,VICINITY,WARD,DBH,"
          "CONDITION,OWNERSHIP,TBOX_STAT,CROWN_AREA,MAX_CROWN_HEIGHT,MAX_MEAN,"
          "WIRES,CURB,SIDEWALK,TBOX_L,TBOX_W,FACILITYID")
WHERE = "GENUS_NAME='Prunus'"
CHUNK = 400


def get(**kw):
    kw.setdefault("f", "json")
    url = BASE + "?" + urllib.parse.urlencode(kw)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return json.load(r)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))


def main(out):
    ids = sorted(get(where=WHERE, returnIdsOnly="true")["objectIds"])
    print(f"{len(ids)} Prunus records", file=sys.stderr)
    feats = []
    for i in range(0, len(ids), CHUNK):
        d = get(objectIds=",".join(map(str, ids[i:i + CHUNK])), outFields=FIELDS,
                returnGeometry="true", outSR="4326")
        feats.extend(d["features"])
        print(f"  {len(feats)}/{len(ids)}", file=sys.stderr)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(feats, fh)
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "src/data/dc_prunus_raw.json")
