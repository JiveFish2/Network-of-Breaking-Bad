# Network of Breaking Bad

This project analyzes relationships between Breaking Bad characters using web scraping, NLP, and graph analysis. It was adapted from `the_witcher_network-main` for a Breaking Bad dataset/workflow.

## References

- Breaking Bad repo: [JiveFish2/Network-of-Breaking-Bad](https://github.com/JiveFish2/Network-of-Breaking-Bad)
- Original Witcher repo: [thu-vu92/the_witcher_network](https://github.com/thu-vu92/the_witcher_network)

## Repository Structure

- `character_scraping.ipynb`: Scrapes/organizes Breaking Bad character data.
- `extracting_relationships.ipynb`: Extracts named entities and builds character networks.
- `characters_bd.csv`: Character list used by the NLP pipeline.
- `data/`: Raw text/script inputs (`.txt`) used for relationship extraction.
- `lib/utils/functions.py`: Reusable NLP/network helper functions.

## Status

Implemented:
- Character scraping notebook (now uses the MediaWiki API directly; no Selenium / browser needed).
- Relationship extraction notebook using spaCy + NetworkX, with alias-aware entity resolution.
- Utility functions for NER, alias normalization, character-list cleanup, and relationship graph edges.

Planned:
- Expand the alias map in `lib/utils/functions.py` (currently covers the show's main cast).
- Expand and clean episode/script coverage in `data/`.
- Improve visualization outputs and centrality/community analysis reporting.

## Requirements

- Python 3.10+

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Running

1. Start Jupyter:
```bash
jupyter notebook
```
2. Run `character_scraping.ipynb` to generate/update character data.
3. Run `extracting_relationships.ipynb` to build and visualize relationship graphs.

## Character Graph

![Breaking Bad character graph](character-graph.png)

Built from all 62 episode transcripts with a 5-sentence co-occurrence window: **89 characters, 236 relationships** (average degree 5.3). Node size is degree, colour is the Louvain community, edge thickness is how often the pair co-occurs. The render follows the look of the original Witcher network image (pyvis, dark `#222222` background, white labels); it frames the 87-character main component, so the isolated Fernando–Sandor pair sits off-frame. Regenerate it with `python make_character_graph.py`. A run that lands far from those counts means something upstream changed — see `CLAUDE.md`.

## Notes

- Relationship extraction expects `.txt` files in `data/`.
- Utility functions are imported from `lib/utils/functions.py`.

## Expected Input Formats

- `characters_bd.csv`:
  - Required column: `character`
  - Optional/used in notebook: `season`
  - The relationship notebook derives `character_firstname` internally.
- `data/*.txt`:
  - Plain UTF-8 text files.
  - Typically one file per episode/script chunk.
  - Dialogue/scenes in readable transcript form (speaker names in text are helpful for NER quality).

## Known Limitations

- NER is based on `en_core_web_sm`, which can miss entities or merge/split names incorrectly.
- Character matching uses an alias map plus full-name / unique-firstname matching; ambiguous shared firstnames (e.g. multiple "Lucy" entries) are intentionally not auto-attributed.
- Relationship strength is proximity-based (windowed co-occurrence), not semantic interaction detection.
- Results depend heavily on transcript quality and consistency.

## Change History

Notable in-place changes are tagged with `# === [YYYY-MM-DD FIX <n>] ===` markers in source files. Grep for the date to find each block. The 2026-04-28 pass covered: MediaWiki API rewrite of the scraper (Cloudflare workaround), character-list cleanup, alias normalization, and notebook hygiene fixes.
