# 🌸 Low Enough

**Washington has 10,405 flowering cherries that are nowhere near the Tidal Basin, and two-thirds of them stand under a power line.**

→ **[Open it](https://tnriley.github.io/low-enough/)**

Every Prunus in the District of Columbia's public-space tree inventory, mapped, sized and sorted by when it flowers. The city's blossom map turns out to be its overhead-wire map: 63% of DC's cherries have a utility line above them against 19% of its oaks, because a cherry is what a forester plants where a shade tree would grow into the cable. Across the eight wards the share of street trees that are cherries tracks the share with wires overhead at r = 0.92 - and Ward 2, which contains the Tidal Basin, has the fewest street cherries in the city.

## Running it

One self-contained HTML file. No build step, no server, no network access at runtime — open `index.html` in a browser, or serve the directory with any static host.

```bash
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Rebuilding it from scratch

[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data sources and their quirks, the processing decisions, the page's structure and interactions, and a table of expected values to check the result against.

## Source

The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.

## Data

- **[District of Columbia public-space tree inventory (UFA Street Trees), DC GIS Urban Tree Canopy service layer 23, maintained by the DDOT Urban Forestry Division - species, position, trunk diameter, condition, ward, lidar crown and overhead-wire status for 222,660 trees](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Urban_Tree_Canopy/MapServer/23)** — Public domain (DC Open Data)
- **[Ward boundaries (Ward - 2022) and Waterbodies, DC GIS](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/53)** — Public domain (DC Open Data)
- **[Cherry tree varieties and their bloom order, National Park Service](https://www.nps.gov/subjects/cherryblossom/types-of-trees.htm)** — US Government public domain
- **[Bloom-order corroboration for Okame and Kwanzan, Casey Trees](https://caseytrees.org/2026/03/cherry-blossom-season-is-here-find-blooms-near-you/)** — Cited, not redistributed
- **[Prunus 'Snow Goose' parentage and flowering habit, Landscape Plants, Oregon State University](https://landscapeplants.oregonstate.edu/plants/prunus-snow-goose)** — Cited, not redistributed

Every figure on the page is computed from the data shipped with it. Check the page's own methods panel for how each number is derived and where it should not be pushed.

## Built with

vanilla JS, canvas, inline SVG, typed-array payload.

## Licence

Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.

---

Part of [Quick Projects](https://github.com/TNRiley/quick-projects) — one self-contained thing, built in one session. First published 2026-09-24.
