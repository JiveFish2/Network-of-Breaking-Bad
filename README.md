# ⚗️ Network of Breaking Bad

This project maps the connections and the evolution of relationships between characters in the **Breaking Bad** universe using **Web Scraping**, **Natural Language Processing (NLP)**, and **Network Analysis**.

The project is inspired by the data portfolio series by [Thu Vu](https://www.youtube.com/@thuvu592), adapted to explore the dynamics of the Breaking Bad lore.

## Project Roadmap

### **Phase 1: Data Extraction (V1 - Current)**
In this initial phase, I developed a scraper to collect the official character list for each season of the show.
* **Data Source**: [Breaking Bad Fandom Wiki](https://breakingbad.fandom.com/wiki/Category:Breaking_Bad_Characters).
* **Tools**: Python, Selenium, Pandas, and Matplotlib.
* **Key Features**:
    * Automated navigation through character categories (Seasons 1 to 5B).
    * Handling of cookie consent pop-ups and dynamic page rendering.
    * Initial data analysis showing character distribution across seasons.

### **Phase 2: Relationship Extraction (V2 - Upcoming)**
The next version will transform raw text/scripts into an interactive relationship graph.
* **Objective**: Identify character importance using network metrics and community detection.
* **Planned Tech Stack**:
    * `spaCy` for Named Entity Recognition (NER).
    * `NetworkX` for calculating Degree, Betweenness, and Closeness Centrality.
    * `Pyvis` for interactive graph visualization.

---

## Tech Stack (V1)

* **Selenium**: Used for browser automation to interact with dynamic web elements.
* **WebDriver Manager**: Handles ChromeDriver binaries automatically for a smoother setup.
* **Pandas**: Used for data structuring, cleaning, and CSV export.
* **Matplotlib**: Generates visual summaries of the scraped data.

## Repository Structure

* `notebooks/character_scraping.ipynb`: The primary notebook containing the scraper logic and initial exploratory data analysis.
* `data/`: Directory for stored CSVs and raw text files for Phase 2.
* `src/`: Utility functions for NLP processing and graph generation.

---

## Installation & Usage

1. **Clone the repo**:
   ```bash
   git clone [https://github.com/JiveFish2/Network-of-Breaking-Bad.git](https://github.com/JiveFish2/Network-of-Breaking-Bad.git)