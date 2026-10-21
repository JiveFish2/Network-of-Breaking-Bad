"""
Print-screen the Louvain-coloured character graph into character-graph.png.

Rewritten 2026-10-21 to match the look of the README image in the project this
one was adapted from, thu-vu92/the_witcher_network (its notebook cell 44:
`Network(width="1000px", height="700px", bgcolor='#222222',
font_color='white')`). The 2026-08-11 version imitated the older Breaking Bad
PNG from commit e1fd32f instead -- white background, invisible labels, canvas
trimmed to the drawing -- which is why it looked nothing like the Witcher graph.

What the render is:

    engine   pyvis / vis.js, print-screened
    canvas   1000x700 -- the notebook's Network(width=, height=), untrimmed,
             the way the Witcher screenshot shows the whole canvas
    options  vis.js DEFAULTS. smooth: dynamic (the curvy, looping edges),
             edges.color.inherit, default barnesHut, default value->width
             scaling. This script therefore calls no set_options() at all.
    nodes    sized by raw degree, coloured by Louvain community via the `group`
             attribute, so vis.js picks the colours from its own group palette
    labels   visible -- white on the #222222 background, exactly as the
             notebook and the Witcher repo write them.
    framing  fit() to the largest connected component only. Fernando--Sandor is
             a 2-node island that, if fitted, shrinks the main graph into a
             corner of the canvas; it stays in the HTML, just off-frame here.

pyvis 0.3.2's template leaves a white strip under the canvas, so the page body
is painted #222222 before the screenshot.

Graph source: `breaking_communities.html`, which the notebook writes and which
embeds the full node/edge list. Reading it back avoids re-running spaCy NER
over all 62 transcripts just to redraw. Community groups are taken from that
file when present; otherwise they're recomputed with Louvain (--seed). A copy
saved before the notebook's `set_node_attributes(G, communities, 'group')` cell
ran carries no groups, so this script recomputes them.

vis.js physics is force-directed and unseeded, so every run produces a
*different layout* of the same graph. Louvain is seeded so at least the
community-to-colour assignment holds still. Judge the output by node count, hub
sizes and community colours -- never by geometry.

Requires Google Chrome; Selenium Manager fetches the matching chromedriver on
first run.

Usage:
    python make_character_graph.py
    python make_character_graph.py --out /tmp/preview.png --seed 7
"""

import argparse
import json
import os
import re
import time

import networkx as nx
from pyvis.network import Network
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

HERE = os.path.dirname(os.path.abspath(__file__))

# The notebook's and the Witcher repo's pyvis background.
BGCOLOR = "#222222"

# pyvis writes the node and edge datasets with this exact constructor call.
_DATASET_RE = re.compile(r"new vis\.DataSet\((\[.*?\])\);", re.S)

# The line we hook so the page can tell us when physics has settled.
_NETWORK_CTOR = "new vis.Network(container, data, options);"


def load_graph(html_path):
    """Rebuild the NetworkX graph from a pyvis-generated HTML file."""
    with open(html_path, encoding="utf-8") as fh:
        html = fh.read()

    datasets = _DATASET_RE.findall(html)
    if len(datasets) != 2:
        raise SystemExit(
            f"{html_path}: expected 2 vis.DataSet blocks (nodes, edges), found "
            f"{len(datasets)}. Regenerate it from extracting_relationships.ipynb."
        )

    nodes, edges = (json.loads(block) for block in datasets)

    G = nx.Graph()
    for node in nodes:
        # `size` is the raw degree, set by the notebook before from_nx().
        G.add_node(node["id"], size=node["size"])
        if node.get("group") is not None:
            G.nodes[node["id"]]["group"] = node["group"]
    for edge in edges:
        # The attribute MUST be called `value`, not `weight`. pyvis's from_nx
        # runs with edge_scaling=False by default, which writes any `weight`
        # straight into vis.js `width` -- a weight of 2205 becomes a 2205px-wide
        # edge, i.e. a solid wedge across the canvas. Naming it `value` instead
        # leaves width at 1 and lets vis.js apply its default value->width
        # scaling (1..15px), which is what the reference render does; the
        # notebook gets this for free because create_relationships() already
        # calls the column `value`.
        G.add_edge(edge["from"], edge["to"], value=edge["value"])

    return G


def assign_communities(G, seed):
    """Ensure every node carries a `group`; recompute with Louvain if needed."""
    if all("group" in data for _, data in G.nodes(data=True)):
        groups = {n: d["group"] for n, d in G.nodes(data=True)}
        source = "from source HTML"
    else:
        import community as community_louvain

        groups = community_louvain.best_partition(G, random_state=seed)
        nx.set_node_attributes(G, groups, "group")
        source = f"recomputed, Louvain seed {seed}"

    return len(set(groups.values())), source


def render_html(G, out_path, width, height):
    """Write the pyvis page with stock vis.js options -- see module docstring."""
    # Same colours as the notebook and the Witcher repo: white labels on #222222.
    net = Network(width=f"{width}px", height=f"{height}px", bgcolor=BGCOLOR,
                  font_color="white")
    net.from_nx(G)
    # Deliberately no set_options() -- vis.js defaults are the reference look.
    net.write_html(out_path, notebook=False, open_browser=False)

    with open(out_path, encoding="utf-8") as fh:
        html = fh.read()
    if _NETWORK_CTOR not in html:
        raise SystemExit(
            "pyvis template changed: could not find the vis.Network constructor "
            "to hook for stabilization. Check pyvis version (tested on 0.3.2)."
        )
    html = html.replace(
        _NETWORK_CTOR,
        _NETWORK_CTOR
        + """
      window.__net = network;
      window.__stab = false;
      network.once("stabilizationIterationsDone", function () { window.__stab = true; });
""",
        1,
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)


def screenshot(html_path, png_path, width, height, scale, timeout, fit_nodes):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument(f"--window-size={width + 120},{height + 120}")
    opts.add_argument(f"--force-device-scale-factor={scale}")
    opts.add_argument("--hide-scrollbars")

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get("file://" + html_path)

        deadline = time.time() + timeout
        while time.time() < deadline:
            if driver.execute_script("return window.__stab === true;"):
                break
            time.sleep(0.25)
        else:
            print(f"  ! physics did not report stabilized within {timeout:.0f}s; "
                  "screenshotting anyway")

        # Freeze the layout, fit the main component to the canvas, drop the
        # loading overlay and paint over the template's white strip.
        driver.execute_script(
            """
            document.body.style.background = arguments[1];
            var n = window.__net;
            n.setOptions({physics: {enabled: false}});
            n.fit({nodes: arguments[0], animation: false});
            var bar = document.getElementById('loadingBar');
            if (bar) { bar.style.display = 'none'; }
            """,
            fit_nodes, BGCOLOR,
        )
        time.sleep(1.5)  # let the canvas repaint after fit()

        driver.find_element(By.CSS_SELECTOR, "#mynetwork canvas").screenshot(png_path)
    finally:
        driver.quit()


def main():
    ap = argparse.ArgumentParser(
        description="Print-screen the Louvain-coloured character graph.")
    ap.add_argument("--source", default=os.path.join(HERE, "breaking_communities.html"),
                    help="pyvis HTML to read the graph from")
    ap.add_argument("--out", default=os.path.join(HERE, "character-graph.png"))
    ap.add_argument("--render", default=os.path.join(HERE, "_graph_render.html"),
                    help="intermediate page that gets screenshotted (git-ignored)")
    ap.add_argument("--seed", type=int, default=42,
                    help="Louvain random_state, used only if --source has no groups")
    # 1000x700 is the notebook's canvas; the PNG is that whole canvas.
    ap.add_argument("--width", type=int, default=1000)
    ap.add_argument("--height", type=int, default=700)
    ap.add_argument("--scale", type=float, default=2.0,
                    help="Chrome device scale factor; >1 for a crisper, larger PNG")
    ap.add_argument("--timeout", type=float, default=120.0,
                    help="seconds to wait for physics to stabilise")
    args = ap.parse_args()

    G = load_graph(args.source)
    print(f"graph:  {G.number_of_nodes()} nodes / {G.number_of_edges()} edges / "
          f"avg degree {2 * G.number_of_edges() / G.number_of_nodes():.2f}")

    n_com, how = assign_communities(G, args.seed)
    print(f"groups: {n_com} communities ({how})")

    main_component = max(nx.connected_components(G), key=len)
    off_frame = G.number_of_nodes() - len(main_component)
    print(f"frame:  largest component, {len(main_component)} nodes "
          f"({off_frame} in smaller components left off-frame)")

    render_html(G, args.render, args.width, args.height)
    screenshot(os.path.abspath(args.render), os.path.abspath(args.out),
               args.width, args.height, args.scale, args.timeout,
               sorted(main_component))
    print(f"wrote:  {args.out}")


if __name__ == "__main__":
    main()
