#!/usr/bin/env python3
"""Turn the raw downloads into the single JSON payload the page carries.

    python src/build_payload.py src/data/ src/payload.json

Everything the page draws is computed here; the browser only decodes and plots.
The per-tree table is packed into parallel typed arrays and base64'd, because
12,855 trees x 9 attributes as JSON objects is about 2 MB and as typed arrays it
is 170 KB.

Coordinates are stored as uint16 offsets from the bounding box in units of
1e-5 degrees - about 1.1 m at this latitude, which is finer than the inventory's
own positional accuracy (trees are digitised to the tree box, not surveyed).
"""
import base64, datetime, json, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import classify, LABEL          # noqa: E402

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

# Bloom order, in days relative to the Tidal Basin Yoshino peak bloom date.
# This is published horticultural sequence, not a forecast:
#   NPS, "Types of Trees": Okame is "the earliest flowering cherry"; the weeping
#   Higan cherries "flower about a week before the Yoshino trees"; Kwanzan comes
#   "into bloom two weeks later than the Yoshino".
#   Casey Trees: Okame opens "as early as mid-March" against a Yoshino peak of
#   March 20-25 - hence -14.
#   'Snow Goose' is a Prunus incisa x P. speciosa hybrid flowering "before the
#   leaves" (Oregon State University, Landscape Plants); reliably early, but with
#   no DC-specific published offset, so it is flagged as the uncertain one.
# The second number is the half-width of the open-flower window: NPS describes
# Yoshino bloom as lasting "a period of several days", extended either side of
# peak.
BLOOM = {            # key: (offset days, half-window days, uncertain?)
    "okame":     (-14, 6, False),
    "higan":     (-7,  6, False),
    "snowgoose": (-5,  6, True),
    "yoshino":   (0,   5, False),
    "kwanzan":   (14,  6, False),
}
BLOOM_ORDER = ["okame", "higan", "snowgoose", "yoshino", "kwanzan"]
# Every Prunus key the page knows about, in the order the payload encodes them.
KEYS = BLOOM_ORDER + ["mume", "sargent", "unidentified", "plum", "chokecherry",
                      "blackcherry", "sourcherry", "peach", "apricot", "almond",
                      "unknown"]
ORNAMENTAL = set(BLOOM_ORDER) | {"mume", "sargent", "unidentified"}

WIRE = {"None": 0, "Low Voltage": 1, "High Voltage": 2, "Both": 3}
COND = {None: 0, "Excellent": 1, "Good": 2, "Fair": 3, "Poor": 4, "Dead": 5}

# The inventory carries 26 trees on District-owned land in Laurel, Maryland (the
# Oak Hill / New Beginnings campus). They have no ward, they are 20 miles outside
# the city, and left in they stretch the map's bounding box by a third. Dropped.
DC_BBOX = (-77.13, 38.78, -76.89, 39.01)


def year(ms):
    if ms is None:
        return 0
    try:
        y = (EPOCH + datetime.timedelta(milliseconds=ms)).year
    except (OverflowError, OSError, ValueError):
        return 0
    return y if 1900 <= y <= 2030 else 0


def b64(fmt, values):
    return base64.b64encode(struct.pack("<%d%s" % (len(values), fmt), *values)).decode()


def load(datadir):
    raw = json.load(open(os.path.join(datadir, "dc_prunus_raw.json"), encoding="utf-8"))
    trees = []
    for f in raw:
        a = f["attributes"]
        key, orn = classify(a.get("SCI_NM"), a.get("CMMN_NM"))
        if key is None:               # genus says Prunus, both names say otherwise
            continue
        g = f.get("geometry") or {}
        if g.get("x") is None:
            continue
        if not (DC_BBOX[0] < g["x"] < DC_BBOX[2] and DC_BBOX[1] < g["y"] < DC_BBOX[3]):
            continue
        trees.append({
            "key": key, "orn": orn,
            "lon": g["x"], "lat": g["y"],
            "ward": a.get("WARD") if a.get("WARD") in range(1, 9) else 0,
            "wire": WIRE.get((a.get("WIRES") or "None").strip(), 0),
            "dbh": a.get("DBH") or 0,
            "crown": a.get("CROWN_AREA") or 0,
            "year": year(a.get("DATE_PLANT")),
            "cond": COND.get(a.get("CONDITION"), 0),
        })
    return trees


def pack(trees):
    origin = {"lon": min(t["lon"] for t in trees),
              "lat": min(t["lat"] for t in trees),
              "scale": 1e-5}

    def q(v, base):
        return max(0, min(65535, round((v - base) / origin["scale"])))

    return {
        "n": len(trees),
        "origin": origin,
        "x":     b64("H", [q(t["lon"], origin["lon"]) for t in trees]),
        "y":     b64("H", [q(t["lat"], origin["lat"]) for t in trees]),
        "key":   b64("B", [KEYS.index(t["key"]) for t in trees]),
        "ward":  b64("B", [t["ward"] for t in trees]),
        "wire":  b64("B", [t["wire"] for t in trees]),
        "cond":  b64("B", [t["cond"] for t in trees]),
        # DBH in half-inches; the biggest cherry in the inventory is 56.8 in
        "dbh":   b64("B", [max(0, min(255, round(t["dbh"] * 2))) for t in trees]),
        "crown": b64("H", [max(0, min(65535, round(t["crown"]))) for t in trees]),
        "year":  b64("H", [t["year"] for t in trees]),
    }


def stats(trees, city):
    orn = [t for t in trees if t["orn"]]

    def wired(rs):
        return sum(1 for r in rs if r["wire"])

    # --- the ladder: under-wire share by genus, across the whole inventory ---
    gen = {}
    for r in city:
        g = gen.setdefault(r["genus"] or "(unrecorded)", {"n": 0, "u": 0})
        g["n"] += r["n"]
        if r["wires"] in ("Both", "Low Voltage", "High Voltage"):
            g["u"] += r["n"]
    ladder = sorted(({"genus": k, "n": v["n"], "under": v["u"]}
                     for k, v in gen.items()
                     if v["n"] >= 800 and k not in ("(unrecorded)", "Other")),
                    key=lambda d: -d["under"] / d["n"])

    # --- wards: wire share of all street trees vs cherry share --------------
    wards = {}
    for r in city:
        if r["ward"] not in range(1, 9):
            continue
        w = wards.setdefault(r["ward"], {"trees": 0, "under": 0, "cherry": 0})
        w["trees"] += r["n"]
        if r["wires"] in ("Both", "Low Voltage", "High Voltage"):
            w["under"] += r["n"]
        if r["genus"] == "Prunus":
            w["cherry"] += r["n"]
    for wd, v in wards.items():
        sub = [t for t in orn if t["ward"] == wd]
        v["orn"] = len(sub)
        v["ornUnder"] = wired(sub)
        v["mix"] = {k: sum(1 for t in sub if t["key"] == k) for k in BLOOM_ORDER}

    # --- per cultivar -------------------------------------------------------
    cult = {}
    for k in KEYS:
        sub = [t for t in trees if t["key"] == k]
        if not sub:
            continue
        crowns = [t["crown"] for t in sub if t["crown"]]
        dbhs = sorted(t["dbh"] for t in sub if t["dbh"])
        cult[k] = {
            "label": LABEL.get(k, (k, ""))[0], "sci": LABEL.get(k, ("", ""))[1],
            "n": len(sub), "under": wired(sub),
            "crownSqFt": round(sum(crowns)), "crownN": len(crowns),
            "dbhMedian": dbhs[len(dbhs) // 2] if dbhs else None,
            "dead": sum(1 for t in sub if t["cond"] == 5),
            "ornamental": k in ORNAMENTAL,
            "bloom": BLOOM.get(k),
        }

    # --- planting history ---------------------------------------------------
    years = {}
    for t in orn:
        if not t["year"]:
            continue
        y = years.setdefault(t["year"], dict({"n": 0, "under": 0},
                                             **{k: 0 for k in BLOOM_ORDER}))
        y["n"] += 1
        y["under"] += 1 if t["wire"] else 0
        if t["key"] in BLOOM_ORDER:
            y[t["key"]] += 1

    return {
        "ladder": ladder,
        "wards": dict((str(k), v) for k, v in sorted(wards.items())),
        "cultivars": cult,
        "plantings": dict((str(y), v) for y, v in sorted(years.items()) if y >= 1995),
        "totals": {
            "prunus": len(trees),
            "ornamental": len(orn),
            "ornamentalUnder": wired(orn),
            "cityTrees": sum(r["n"] for r in city),
            "cityUnder": sum(r["n"] for r in city
                             if r["wires"] in ("Both", "Low Voltage", "High Voltage")),
            "crownAcres": round(sum(t["crown"] for t in orn) / 43560, 1),
            "dated": sum(1 for t in orn if t["year"]),
        },
    }


def geo(datadir):
    wards = json.load(open(os.path.join(datadir, "wards.json"), encoding="utf-8"))
    water = json.load(open(os.path.join(datadir, "water.json"), encoding="utf-8"))

    def area(ring):
        s = 0.0
        for i in range(len(ring) - 1):
            s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
        return abs(s) / 2

    big = []
    for f in water:
        r = max(f["rings"], key=area)
        # drop ponds and stormwater cells: only the rivers and the basins read
        # at city scale
        if area(r) > 2e-6:
            big.append([[round(p[0], 5), round(p[1], 5)] for p in r])

    return {
        "wards": [{"ward": f["attributes"].get("WARD"),
                   "rings": [[[round(p[0], 5), round(p[1], 5)] for p in r]
                             for r in f["rings"]]} for f in wards],
        "water": big,
    }


def main(datadir, out):
    trees = load(datadir)
    city = json.load(open(os.path.join(datadir, "city_counts.json"), encoding="utf-8"))
    payload = dict({
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "keys": KEYS, "bloomOrder": BLOOM_ORDER,
        "trees": pack(trees),
        "geo": geo(datadir),
    }, **stats(trees, city))
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print("wrote %s  %.0f KB  %d flowering cherries"
          % (out, os.path.getsize(out) / 1024, payload["totals"]["ornamental"]),
          file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "src/data",
         sys.argv[2] if len(sys.argv) > 2 else "src/payload.json")
