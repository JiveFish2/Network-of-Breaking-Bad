# Network of Breaking Bad

This project analyzes relationships between Breaking Bad characters using web scraping, NLP, and graph analysis. It was adapted from `the_witcher_network-main` for a Breaking Bad dataset/workflow.

## Repository Structure

- `character_scraping.ipynb`: Scrapes/organizes Breaking Bad character data.
- `extracting_relationships.ipynb`: Extracts named entities and builds character networks.
- `characters_bd.csv`: Character list used by the NLP pipeline.
- `data/`: Raw text/script inputs (`.txt`) used for relationship extraction.
- `lib/utils/functions.py`: Reusable NLP/network helper functions.

## Requirements

- Python 3.10+
- Chrome installed (for Selenium runs in the scraping notebook)

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

## Notes

- Relationship extraction expects `.txt` files in `data/`.
- Utility functions are imported from `lib/utils/functions.py`.
