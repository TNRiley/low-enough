# src/

The pipeline that builds `index.html`. Run from the project directory, in this order:

```bash
python src/fetch_trees.py   data/dc_prunus_raw.json
python src/fetch_context.py data/
python src/build_payload.py data/ src/payload.json
python src/inject.py
```

| file | what it does |
|---|---|
| `fetch_trees.py` | every `GENUS_NAME='Prunus'` record from DC GIS layer 23, paged by OBJECTID, geometry in WGS84 |
| `fetch_context.py` | the city-wide genus × wires × ward counts (server-side groupBy), plus ward and waterbody polygons |
| `classify.py` | the regex rule list that turns the inventory's free-text species names into cultivars |
| `build_payload.py` | all the arithmetic, and the typed-array packing → `payload.json` |
| `template.html` | the page, with a `__PAYLOAD__` placeholder |
| `inject.py` | splices the two, then runs the catalog's `wrap_for_pages.py` and `add_catalog_link.py` |

The raw downloads land in `data/` and are gitignored — the fetchers refetch them. The one
thing that is *not* reproducible from the scripts is the inventory itself: it is live, so a
later run will differ slightly as trees are planted, removed and re-surveyed.
`REBUILD.md` in the project root carries a verification table of the values as built.

On Windows use `python`, not `python3`.
