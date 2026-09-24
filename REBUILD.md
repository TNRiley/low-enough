# Rebuilding *Low Enough*

Enough instruction to reproduce this project from scratch with a shell, Python 3 and
nothing else. Read it all before starting; §6 is the one that will save you.

---

## 1. What is being built, and why

A single standalone HTML page about the flowering cherry trees of Washington DC — not the
famous ones. The Tidal Basin grove belongs to the National Park Service and is about 3,800
trees. The *District's own* public-space tree inventory holds roughly 12,800 more trees of
the genus *Prunus*, about 10,400 of them ornamental flowering cherries, scattered along
streets and through parks all over the city.

**The finding the page exists to show:** 63% of those cherries stand under an overhead
utility wire, against 28% for the city's street trees as a whole and 19% for its oaks. That
is not about cherries being special — it is a *height* ladder. Sort every genus in the
inventory by its under-wire share and you get a clean descent from tree lilac (80%) to pine
(2%), i.e. from small trees to large ones. What makes it worth a page is the second step:
because Washington's small-tree slot is filled with cherries in particular, **the city's
blossom map and its overhead-wire map are the same map**. Across the eight wards, the share
of street trees that are cherries tracks the share with wires overhead at r = 0.92. Wards 1,
2 and 6 put their utilities underground and have almost no street cherries — and Ward 2 is
the ward that contains the Tidal Basin.

The secondary finding: the street trees are five cultivars whose published bloom order
spreads over about six weeks in two waves, with a lull of several days between the Yoshinos
finishing and the Kwanzans starting. The most common flowering cherry on a DC street is the
Kwanzan, which opens about two weeks after the Tidal Basin peaks.

---

## 2. Data sources, with exact URLs

### 2.1 The backbone: DC's public-space tree inventory

ArcGIS REST, no key, no rate limit encountered:

```
https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Urban_Tree_Canopy/MapServer/23
```

Layer 23 is `UFA Street Trees`, the DDOT Urban Forestry Division inventory. 222,660 records
at the time of the build. Fields used: `SCI_NM`, `CMMN_NM`, `GENUS_NAME`, `DATE_PLANT`,
`WARD`, `DBH`, `CONDITION`, `CROWN_AREA`, `WIRES`, `VICINITY`, plus point geometry.

Quirks that will bite:

* **The service caps a query at 2,000 records.** `returnCountOnly` and
  `groupByFieldsForStatistics` are not capped, so do every aggregate server-side and only
  page the rows you actually need. `src/fetch_trees.py` pulls the OBJECTID list first and
  then fetches in blocks of 400.
* **`outStatisticFieldName` comes back upper-cased.** Ask for `n`, read `N`. Normalise the
  attribute keys or you will get a `KeyError` on every groupBy.
* **`WIRES` has two spellings of "no wire":** `"None"` and `"None "` (trailing space). Strip
  before counting or you will split the biggest bucket in two. Values are `None`,
  `Low Voltage`, `High Voltage`, `Both`. This page counts the last three together.
* **`GENUS_NAME` is not trustworthy on its own.** 62 rows have `GENUS_NAME = 'Prunus'` with
  an oak, a crape myrtle or a London plane in the name fields. Drop them.
* **`GENUS_NAME` contains a typo in DC's own data:** `Aescululs` for *Aesculus*. Leave the
  value alone; map it to a display name.
* **`DATE_PLANT` is epoch milliseconds and occasionally garbage** — a handful of 1899/1900
  values, and some out of range for `datetime.utcfromtimestamp` on Windows, which raises
  `OSError: [Errno 22]` rather than something you would guess. Clamp to 1900–2030 and
  catch `OSError`.
* **Geometry defaults to Web Mercator.** Pass `outSR=4326`.
* **26 records sit in Laurel, Maryland** (the District-owned Oak Hill / New Beginnings
  campus, `VICINITY` like "Oak Hill Drive"). They have no ward and they stretch the map's
  bounding box by a third. `src/build_payload.py` drops anything outside
  `(-77.13, 38.78, -76.89, 39.01)`.

### 2.2 Boundaries

```
.../Administrative_Other_Boundaries_WebMercator/MapServer/53   Ward - 2022
.../Environment_Water_WebMercator/MapServer/24                 Waterbodies (polygons)
```

Note **24, not 13** — layer 13 is `Hydrography`, which is polylines, and a polyline query
returns no `rings`, so the fetch fails with `KeyError: 'features'` in a confusing way.
Request with `maxAllowableOffset` (0.0002 deg is plenty) and `geometryPrecision=5`; the raw
ward rings are about a megabyte. Waterbodies returns ~1,293 polygons, nearly all stormwater
cells and ponds; keep only rings with a shoelace area above 2e-6 deg², which leaves 9 —
the two rivers and the basins.

### 2.3 Bloom order (reference, not measurement)

* NPS, *Types of Trees*, <https://www.nps.gov/subjects/cherryblossom/types-of-trees.htm> —
  Okame is "the earliest flowering cherry"; the weeping Higan cherries "flower about a week
  before the Yoshino trees"; Kwanzan comes "into bloom two weeks later than the Yoshino";
  the grove is about 70% Yoshino of roughly 3,800 trees.
* NPS, *Bloom Watch* — peak bloom is "the day when 70% of the Yoshino Cherry blossoms are
  open"; Yoshinos "bloom for a period of several days"; peak is most likely "between the
  last week of March and the first week of April".
* Casey Trees — Okame "as early as mid-March" against a Yoshino peak of March 20–25, which
  is where the −14 comes from.
* Oregon State University, *Landscape Plants*,
  <https://landscapeplants.oregonstate.edu/plants/prunus-snow-goose> — 'Snow Goose' is a
  *P. speciosa* × *P. incisa* hybrid flowering before the leaves.

**A dead end worth knowing about:** the USA National Phenology Network has an open
observations API and does carry *Prunus yedoensis* (species 228) and *P. serrulata* (227),
so deriving bloom windows empirically looks attractive. It is not viable. A
`getSummarizedData` query for both species across DC, MD and VA, 2010–2026, open-flower
phenophase (501), returns **76 rows**, and NPN has no record at all for Okame, Snow Goose or
the *subhirtella* Higans, which are 3,300 of DC's trees. Do not build on it.

---

## 3. Processing decisions

**Cultivar normalisation** (`src/classify.py`). The two name fields are free text and
disagree with each other constantly: the same tree appears as `Prunus Okame`,
`Prunus 'Okame'`, `Okame cherry` and combinations. A regex rule list over the joined
lower-cased `SCI_NM + CMMN_NM` string resolves them, in order — `kwanzan` before
`serrulata`, `snow ?goose` before everything, `yedoensis|yodoensis|yoshino|akebono`
together (the inventory misspells *yedoensis* as *yodoensis*). Anything still containing
`prunus` and nothing else falls through to `unidentified`.

The ornamental flowering cherries are the five named cultivars plus Japanese apricot,
Sargent and the `unidentified` bucket. Chokecherry, black cherry, purple-leaf plum, peach,
apricot and almond are *Prunus* but not blossom trees; they appear in the wire charts (which
are about genera) and not in the bloom charts.

**344 rows have `GENUS_NAME = 'Prunus'` and both name fields blank.** They are counted as
*Prunus* but not as flowering cherries. Do not fold them in to make the headline number
bigger.

**Bloom windows.** Each cultivar gets an offset from Tidal Basin Yoshino peak and a
half-width: Okame −14 ±6, Higan −7 ±6, Snow Goose −5 ±6 (flagged uncertain), Yoshino 0 ±5,
Kwanzan +14 ±6. The narrower Yoshino window is NPS's "several days". The arithmetic leaves a
three-day gap between Yoshino ending and Kwanzan starting; that gap is real and the page says
so rather than smoothing it away.

**Crown height is not used.** `MAX_CROWN_HEIGHT` for cherries runs to 127 feet, which is a
neighbouring oak leaning into the lidar crown polygon. `CROWN_AREA` is sound and is where
the 106 acres comes from.

**Payload encoding.** Per-tree attributes go into parallel typed arrays, base64'd: positions
as `uint16` offsets from the bounding box in units of 1e-5 degrees (≈1.1 m, finer than the
inventory's own accuracy — trees are digitised to the tree box), DBH in half-inches as
`uint8`, crown area in square feet as `uint16`, year as `uint16` with 0 for unknown. 12,829
trees come to about 170 KB packed against roughly 2 MB as JSON objects.

---

## 4. The page

One standalone HTML document, no build step beyond `src/inject.py`, no runtime dependencies
except Google Fonts. Six sections: the map; the under-wire ladder; the ward scatter; the
bloom season; the planting history; how it was counted.

**Identity.** Warm blush paper, charcoal ink, and a catenary-wire motif strung between two
poles as the section rule — the tension between the postcard subject and the utility-pole
finding is the whole point of the design. Fraunces for headings, IBM Plex Sans for body, IBM
Plex Mono for figures.

**Colour.** Two palettes, both validated with the `dataviz` skill's
`scripts/validate_palette.js`, against both the page surface and the map's own land colour:

* an **ordinal** five-step rose ramp for bloom order, earliest to latest —
  light `#E693AD #D57193 #BF4E77 #9C355F #702244`,
  dark `#FBC3D3 #F09EB9 #DE7A9C #C4587E #A03E62` (`--ordinal`, all checks pass);
* a **categorical** pair for under-wire / no-wire —
  light `#BF4E77 #1F6FB2`, dark `#D4658C #3E93D6` (`--pairs all`, all checks pass).

Do not eyeball replacements. Re-run the validator.

**Two things that were got wrong first time and are worth not repeating:**

1. *A stacked step area for the bloom season.* Five near-identical pinks stacked on top of
   each other, no legend, unreadable. It is now five direct-labelled ranges on one time axis
   with the running total as a separate strip underneath — the labels are the legend.
2. *`getComputedStyle` inside the render loop.* `colourFor(i)` resolved a CSS custom property
   per tree, i.e. 12,829 style resolutions per frame, and locked the renderer hard enough
   that screenshots timed out. Colours are now resolved once per frame into a lookup keyed by
   cultivar index, and every tree's screen position is precomputed once per canvas size into
   `Float32Array`s.

**Map contrast.** The first version filled the District with `--card` over `--sunk`, which in
dark mode is a two-value difference — the city was invisible and the map read as an empty
box. The map now has its own four tokens (`--mapbg`, `--mapland`, `--mapline`, `--mapwater`)
so the silhouette is a real silhouette in both themes.

---

## 5. Verification table

Rebuild and check these. They are the numbers that catch a parse error immediately.

| Quantity | Expected |
|---|---|
| Trees in the whole inventory | 222,660 |
| Of those, under an overhead wire | 62,179 → **28%** |
| *Prunus* records returned by `GENUS_NAME='Prunus'` | 12,917 |
| After dropping mislabels and the Maryland campus | **12,829** |
| Ornamental flowering cherries | **10,405** |
| Of those, under a wire | 6,517 → **63%** |
| Kwanzan / Yoshino / unidentified / Snow Goose / Okame / Higan / mume | 2,460 / 2,315 / 2,243 / 1,955 / 1,297 / 94 / 41 |
| Cherry crown area, total | **106.4 acres** |
| Under-wire share, tree lilac (*Syringa*) | 80% — top of the ladder |
| Under-wire share, oak (*Quercus*, n = 42,382) | 19% |
| Under-wire share, pine (*Pinus*) | 2% — bottom of the ladder |
| Flowering cherries in Ward 2 | **270** — fewest of any ward |
| Flowering cherries in Ward 3 | 2,970 — most |
| Ward overhead-wire share, Wards 1 / 2 / 6 | 0.2% / 1.0% / 1.1% |
| Ward overhead-wire share, Wards 3 / 4 / 7 / 8 | 37% / 38% / 42% / 40% |
| Pearson r, ward wire share vs ward cherry share, n = 8 | **0.92** |
| Flowering cherries with a planting date | 6,635 |
| Mean planted per year, 2004–2026 | 288 |
| Under-wire share of cherries planted 1995–2004 | 94% |
| Under-wire share of cherries planted 2020–2026 | 61% |
| Trees in flower on peak day (day 0) | 4,270 |
| Peak of the season (days −5 to −1) | 4,364 |
| Trees in flower at day +7 | 0 — the lull between the waves |

A recognisable spot check: hovering the dense line of dots along Puerto Rico Ave NE, or the
cluster at Oxon Run Park in Ward 8, should return cherries; the middle of the map — the
National Mall and the federal core — should be empty, because those trees are the Park
Service's and are not in this inventory at all.

---

## 6. What the page must say about itself

Non-negotiable, and all of it is in section 06 of the page:

1. **The Tidal Basin trees are not in this data.** Every comparison to "3,800 trees" is
   against the Park Service's own published figure, and the blank middle of the map is the
   federal land, not an absence of trees.
2. **The wire finding is about planters, not trees.** Nothing here shows cherries seeking out
   wires. It shows foresters choosing a small tree where a wire is in the way, and the ladder
   in section 02 is the proof — every small genus is up there, not just the cherry.
3. **The bloom order is published sequence, not a forecast**, applied to trees the Park
   Service does not own, and the whole season slides with whatever date the Tidal Basin peaks
   in a given year. Snow Goose is the least certain of the five.
4. **2,243 cherries have no recorded cultivar** and cannot be placed in the season at all.
5. **Unrecorded `WIRES` rows are counted as no wire**, so 63% is a floor.
6. **Crown height is unusable** and is not used.

---

## 7. Running it

```bash
python src/fetch_trees.py   src/data/dc_prunus_raw.json   # ~13k rows, a couple of minutes
python src/fetch_context.py src/data/           # counts + ward and water geometry
python src/build_payload.py src/data/ src/payload.json    # ~257 KB
python src/inject.py                                  # → index.html, wrapped and linked
```

`inject.py` runs `catalog/tools/wrap_for_pages.py` and `catalog/tools/add_catalog_link.py`
as its last two steps. Do not skip them: without the first the page lands in quirks mode on
GitHub Pages and every en dash turns to mojibake, and without the second it loses its way
back to the catalog.

On Windows, the interpreter is `python`, not `python3` — see `catalog/PUBLISHING.md`.
