"""
Build docs/index.html: "Heisenberg's Map of Destruction".

An episode-by-episode map of Walter White's world: who he shares scenes with,
which world they belong to (family, law, crime, other), and everyone who dies
because of him.

Inputs (all in heisenberg_map/):
    source/bb.json   The Serial Speakers dataset (Bost, Labatut & Linares,
                     LREC 2020, CC BY 4.0): every line of all 62 episodes,
                     hand-annotated with its speaker and scene. Not committed;
                     downloaded on first run and checked against SHA256.
    characters.csv   Which speakers become nodes, their display label, their
                     world and, for the main and dangerous characters, a
                     signature colour. Hand-curated. Everyone without one is
                     coloured by Louvain community, like the notebook graph.
    deaths.csv       Every death that matters to the map, with Walt's share of
                     the blame (direct / ordered / indirect / none / self).
                     Facts from the Breaking Bad Wiki's "List of Character
                     Deaths" (CC BY-SA); the walt_role column is our call.
    template.html    The page; build injects the data as JSON. It draws the
                     network with vis-network (the library pyvis uses in the
                     notebook), copied from lib/vis-9.1.2 next to the output.

Why scenes and not the transcripts: the transcripts in data/ only carry speaker
names for seasons 1-3, so a text-based network loses Walt almost entirely in
seasons 4-5. Serial Speakers labels every line of every season, so "spoke in the
same scene" is measured the same way from the pilot to the finale. The dataset's
dialogue text is encrypted; this map only needs speakers and scene boundaries.

Usage (from the repo root):
    python heisenberg_map/build_map.py
"""

import bisect
import csv
import hashlib
import json
import os
import shutil
import urllib.request
from collections import Counter, defaultdict

import community as community_louvain
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE = os.path.join(HERE, "source", "bb.json")
SOURCE_URL = "https://ndownloader.figshare.com/files/21635694"
SOURCE_SHA256 = "7e4794f0b2d60a6e764fcf26eea2eeb5b2efa12a2ebd399b39cf874c5b155286"
OUT = os.path.join(ROOT, "docs", "index.html")

WALT = "Walter White"
LOUVAIN_SEED = 42
# Walt first calls himself Heisenberg in 1x06, "Crazy Handful of Nothin'".
HEISENBERG_FROM = "1x06"
FACTIONS = ["family", "law", "crime", "other"]


def load_source():
    if not os.path.exists(SOURCE):
        os.makedirs(os.path.dirname(SOURCE), exist_ok=True)
        print(f"downloading Serial Speakers bb.json from {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, SOURCE)
    with open(SOURCE, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"{SOURCE}: unexpected SHA256 {digest}; delete it to re-download.")
    with open(SOURCE, encoding="utf-8") as fh:
        return json.load(fh)


def read_csv(name):
    with open(os.path.join(HERE, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def scenes_by_episode(dataset):
    """[(code, title, [set of speakers per scene])] in broadcast order."""
    episodes = []
    for season in dataset["seasons"]:
        for ep in season["episodes"]:
            starts = [sc["start"] for sc in ep["data"]["scenes"]]
            scenes = defaultdict(set)
            for seg in ep["data"]["speech_segments"]:
                i = max(bisect.bisect_right(starts, seg["start"]) - 1, 0)
                scenes[i].add(seg["speaker"])
            code = f"{season['id']}x{ep['id']:02d}"
            episodes.append((code, ep["title"], [scenes[i] for i in sorted(scenes)]))
    return episodes


def main():
    dataset = load_source()
    characters = read_csv("characters.csv")
    deaths = read_csv("deaths.csv")
    episodes = scenes_by_episode(dataset)
    codes = [code for code, _, _ in episodes]
    index = {code: i for i, code in enumerate(codes)}

    meta = {c["speaker"]: c for c in characters}
    walt_role = {d["character"]: d for d in deaths if d["character"]}

    # Per-episode scene counts and pairwise shared scenes, restricted to nodes.
    presence = defaultdict(Counter)  # speaker -> {episode index: scenes}
    pairs = Counter()                # (episode index, a, b) -> shared scenes
    for i, (_, _, scenes) in enumerate(episodes):
        for speakers in scenes:
            members = sorted(s for s in speakers if s in meta)
            for s in members:
                presence[s][i] += 1
            for x in range(len(members)):
                for y in range(x + 1, len(members)):
                    pairs[(i, members[x], members[y])] += 1

    nodes = []
    for c in characters:
        name = c["speaker"]
        death = walt_role.get(name)
        if presence[name]:
            first = min(presence[name])
        elif death:
            first = index[death["episode"]]  # known only through their death
        else:
            raise SystemExit(f"characters.csv: {name!r} never speaks and has no death row")
        nodes.append({
            "id": name,
            "label": c["label"],
            "faction": c["faction"],
            "first": first,
            "presence": {str(k): v for k, v in sorted(presence[name].items())},
            "death": index[death["episode"]] if death else None,
            "role": death["walt_role"] if death else None,
            "note": c["note"],
            "color": c["color"] or None,
            "border": c["border"] or None,
        })

    # Unnamed victims Walt is responsible for become one collective node per row.
    for d in deaths:
        if d["character"] or d["walt_role"] == "none":
            continue
        nid = f"victims-{d['episode']}"
        label = {"2x13": "167 passengers of Wayfarer 515", "3x12": "Two rival dealers",
                 "4x13": "Two superlab guards", "5x16": "Two more of Jack's gang"}.get(d["episode"], "Unnamed victims")
        nodes.append({
            "id": nid, "label": label, "faction": "crime" if d["episode"] != "2x13" else "other",
            "first": index[d["episode"]], "presence": {}, "death": index[d["episode"]],
            "role": d["walt_role"], "note": "", "collective": int(d["victims"]),
        })
        d["character"] = nid

    node_ids = {n["id"] for n in nodes}
    edges = [[i, a, b, w] for (i, a, b), w in sorted(pairs.items())]

    # Communities over the whole series, seeded so the colours hold still between builds.
    G = nx.Graph()
    for (_, a, b), w in pairs.items():
        G.add_edge(a, b, weight=G.get_edge_data(a, b, {"weight": 0})["weight"] + w)
    groups = community_louvain.best_partition(G, weight="weight", random_state=LOUVAIN_SEED)
    # Renumber by size, largest first, so the page can hand out colours in a fixed order.
    by_size = [g for g, _ in Counter(groups.values()).most_common()]
    groups = {name: by_size.index(g) for name, g in groups.items()}
    for n in nodes:
        n["group"] = groups.get(n["id"])

    death_rows = []
    for d in deaths:
        death_rows.append({
            "ep": index[d["episode"]],
            "id": d["character"] if d["character"] in node_ids else None,
            "name": d["character"] if not d["character"].startswith("victims-") else None,
            "victims": int(d["victims"]),
            "role": d["walt_role"],
            "cause": d["cause"],
            "responsible": d["responsible"],
            "rationale": d["rationale"],
        })

    data = {
        "episodes": [{"code": c, "title": t} for c, t, _ in episodes],
        "nodes": nodes,
        "edges": edges,
        "deaths": death_rows,
        "walt": WALT,
        "heisenbergFrom": index[HEISENBERG_FROM],
    }

    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as fh:
        page = fh.read()
    page = page.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    # The page loads vis-network from next to itself, so it works offline and on GitHub Pages.
    for name in ("vis-network.min.js", "vis-network.css"):
        shutil.copy(os.path.join(ROOT, "lib", "vis-9.1.2", name), os.path.join(os.path.dirname(OUT), name))

    counted = Counter()
    for d in death_rows:
        counted[d["role"]] += d["victims"]
    print(f"{len(episodes)} episodes, {len(nodes)} nodes, {len(edges)} episode-edges, "
          f"{len(set(groups.values()))} communities")
    print("deaths by Walt's role:", dict(counted))
    print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
