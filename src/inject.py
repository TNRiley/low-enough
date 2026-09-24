#!/usr/bin/env python3
"""Splice payload.json into template.html and produce the finished page.

    python src/inject.py

Last two steps are the catalog's own tools, per catalog/PUBLISHING.md - without
them a regenerated page silently loses its doctype and its breadcrumb.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = PROJ
while ROOT != os.path.dirname(ROOT) and not os.path.isdir(os.path.join(ROOT, "catalog")):
    ROOT = os.path.dirname(ROOT)
TOOLS = os.path.join(ROOT, "catalog", "tools")
OUT = os.path.join(PROJ, "index.html")


def main():
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    payload = open(os.path.join(HERE, "payload.json"), encoding="utf-8").read().strip()
    json.loads(payload)                       # fail loudly on a broken payload
    # </script> inside a <script> block would close it early; nothing else in
    # JSON needs escaping here.
    payload = payload.replace("</", "<\\/")
    if "__PAYLOAD__" not in tpl:
        sys.exit("template.html has no __PAYLOAD__ placeholder")
    page = tpl.replace("__PAYLOAD__", payload)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print("wrote %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024), file=sys.stderr)

    for tool in ("wrap_for_pages.py", "add_catalog_link.py"):
        p = os.path.join(TOOLS, tool)
        if os.path.exists(p):
            subprocess.run([sys.executable, p, OUT], check=True)
        else:
            print("! missing " + p, file=sys.stderr)


if __name__ == "__main__":
    main()
