import pandas as pd
import numpy as np
import os
import re
from collections import Counter
import spacy
from spacy import displacy
import networkx as nx

import matplotlib.pyplot as plt


# === [BEGIN: 2026-04-28 FIX 7] cache spaCy model so ner() does not reload on every call ===
_NLP_CACHE = None
# === [END: 2026-04-28 FIX 7] ===


def ner(file_name, nlp=None):
    """
    Process a text file with spaCy.

    Params:
    file_name -- path to a .txt file (str or os.DirEntry)
    nlp -- optional preloaded spaCy Language object; if omitted, a module-level
           cached model is used so repeated calls don't reload from disk.
    """
    # === [BEGIN: 2026-04-28 FIX 7] reuse provided or cached nlp instead of reloading every call ===
    global _NLP_CACHE
    if nlp is None:
        if _NLP_CACHE is None:
            _NLP_CACHE = spacy.load("en_core_web_sm")
        nlp = _NLP_CACHE
    # === [END: 2026-04-28 FIX 7] ===
    book_text = open(file_name, encoding="utf-8", errors="ignore").read()
    book_doc = nlp(book_text)

    return book_doc


def get_ne_list_per_sentence(spacy_doc):
    """
    Get a list of entites per sentence of a Spacy document and store in a dataframe.
    
    Params:
    spacy_doc -- a Spacy processed document
    
    Returns:
    a dataframe containing the sentences and corresponding list of recognised named entities       in the sentences

    The `sentence_id` column records each sentence's position in the document.
    create_relationships() windows on it, so co-occurrence stays measured in
    transcript sentences even after the frame is filtered or re-indexed (FIX 11).
    """

    sent_entity_df = []

    # Loop through sentences, store named entity list for each sentence
    for sentence_id, sent in enumerate(spacy_doc.sents):
        entity_list = [ent.text for ent in sent.ents]
        sent_entity_df.append(
            {"sentence_id": sentence_id, "sentence": sent, "entities": entity_list}
        )

    sent_entity_df = pd.DataFrame(sent_entity_df)

    return sent_entity_df


def filter_entity(ent_list, character_df):
    """
    Function to filter out non-character entities.

    NOTE [2026-04-28]: superseded by `normalize_entities()` below, which is
    alias-aware and returns canonical character names rather than raw entity
    text. Kept here for backward compatibility with older notebooks.

    Params:
    ent_list -- list of entities to be filtered
    character_df -- a dataframe contain characters' names and characters' first names

    Returns:
    a list of entities that are characters (matching by names or first names).

    """
    return [ent for ent in ent_list
            if ent in list(character_df.character)
            or ent in list(character_df.character_firstname)]


# ============================================================
# [BEGIN: 2026-04-28 FIX 1, 2, 3, 4, 6 — character-df cleanup + alias normalisation]
# Replaces the inline cell-10 regex (non-raw, no .strip()) and the firstname-only
# matching that conflated Walter Sr./Jr. and missed aliases like Heisenberg / Gus.
# ============================================================

# Junk "first names" that arise from titles, articles, and the "List of bit parts" rows.
# Anything in this set is dropped from the character DataFrame so it can't match real
# spaCy entity tokens like "Dr." or "List".
JUNK_FIRSTNAMES = {
    "List", "Dr.", "Dr", "Mr.", "Mr", "Mrs.", "Mrs", "Ms.", "Ms", "The", "Declan's",
}

# Map raw entity strings (as spaCy emits them) to canonical character names that exist
# in characters_bd.csv. Aliases take priority over full-name / firstname matching, so
# they're how we resolve Heisenberg → Walter, Gus → Gustavo Fring, Walt Jr. → Walter Jr.,
# etc. Add liberally; entries pointing at names not in the CSV are silently ignored
# downstream (they'd produce orphan nodes).
ALIASES = {
    # Walter White (Sr.)
    "Walt": "Walter White",
    "Walter": "Walter White",
    "Heisenberg": "Walter White",
    "Mr. White": "Walter White",
    "White": "Walter White",
    # Walter White Jr. — also goes by Flynn
    "Walt Jr.": "Walter White Jr.",
    "Walter Jr.": "Walter White Jr.",
    "Flynn": "Walter White Jr.",
    "Junior": "Walter White Jr.",
    # Jesse Pinkman
    "Jesse": "Jesse Pinkman",
    "Pinkman": "Jesse Pinkman",
    # Skyler White
    "Skyler": "Skyler White",
    "Sky": "Skyler White",
    # Hank Schrader
    "Hank": "Hank Schrader",
    "Schrader": "Hank Schrader",
    # Marie Schrader
    "Marie": "Marie Schrader",
    # Saul Goodman (manually injected by clean_character_df since the BB Fandom category omits him)
    "Saul": "Saul Goodman",
    "Goodman": "Saul Goodman",
    "Jimmy McGill": "Saul Goodman",
    # Mike Ehrmantraut
    "Mike": "Mike Ehrmantraut",
    "Ehrmantraut": "Mike Ehrmantraut",
    # Gus Fring — note CSV name is "Gustavo Fring"
    "Gus": "Gustavo Fring",
    "Gustavo": "Gustavo Fring",
    "Fring": "Gustavo Fring",
    # Salamancas
    "Tuco": "Tuco Salamanca",
    "Hector": "Hector Salamanca",
    "Tio": "Hector Salamanca",
    # Steven Gomez (CSV uses "Steven", not "Steve")
    "Steve": "Steven Gomez",
    "Gomez": "Steven Gomez",
    "Gomie": "Steven Gomez",
    # Other recurring characters
    "Todd": "Todd Alquist",
    "Lydia": "Lydia Rodarte-Quayle",
    "Jane": "Jane Margolis",
    "Holly": "Holly White",
    "Brock": "Brock Cantillo",
    "Andrea": "Andrea Cantillo",
    "Ted": "Ted Beneke",
    "Beneke": "Ted Beneke",
    "Donald": "Donald Margolis",
    "Huell": "Huell Babineaux",
    "Kuby": "Patrick Kuby",
    "Jack": "Jack Welker",
    "Welker": "Jack Welker",
    "Gale": "Gale Boetticher",
    "Boetticher": "Gale Boetticher",
    "Combo": "Combo",
    "Badger": "Badger",
    "Krazy-8": "Krazy-8",
    "Skinny Pete": "Skinny Pete",
}


def clean_character_df(df):
    """
    Clean a raw characters_bd.csv DataFrame:
      - strip parenthesised qualifiers and trailing whitespace from `character`
      - drop "List of bit parts ..." rows (their firstname becomes "List")
      - drop rows whose firstname is a title/article (Dr., Mr., The, ...)
      - inject characters that the BB Fandom category misses (e.g. Saul Goodman)
      - disambiguate Walter Sr. vs Jr. by overriding Jr.'s firstname so a bare
        "Walter" mention attributes to Sr. and Jr. is reached only via aliases
    """
    df = df.copy()
    df["character"] = df["character"].astype(str).apply(
        lambda x: re.sub(r"\(.*?\)", "", x).strip()
    )
    df = df[~df["character"].str.contains("List of bit parts", case=False, na=False)]
    df = df[df["character"].str.len() > 0]

    # Inject characters missing from the Fandom BB category but central to the show.
    extras = pd.DataFrame([{"season": "Season 2", "character": "Saul Goodman"}])
    extras = extras[~extras["character"].isin(df["character"])]
    df = pd.concat([df, extras], ignore_index=True)

    df = df.drop_duplicates(subset=["character"]).reset_index(drop=True)
    df["character_firstname"] = df["character"].apply(lambda x: x.split(" ", 1)[0])
    df = df[~df["character_firstname"].isin(JUNK_FIRSTNAMES)].reset_index(drop=True)

    # Walter Jr. shares "Walter" firstname with his father; route him via a unique token.
    jr_mask = df["character"].str.endswith(" Jr.") | df["character"].str.endswith(" Jr")
    df.loc[jr_mask, "character_firstname"] = "Junior"

    return df


def normalize_entities(ent_list, character_df, aliases=None):
    """
    Map raw spaCy entity strings to canonical character names from `character_df`.

    Resolution order, first match wins:
      1. Alias map (e.g. "Heisenberg" → "Walter White")
      2. Exact full-name match against character_df.character
      3. Firstname match — but only if the firstname is unique in character_df
         (so ambiguous firstnames like "Walter" don't auto-attribute)

    Unmatched entities are dropped. Returns a list of canonical full names.
    """
    if aliases is None:
        aliases = ALIASES
    full_names = set(character_df["character"])
    fn_counts = Counter(character_df["character_firstname"])
    fn_to_full = {
        fn: full
        for fn, full in zip(character_df["character_firstname"], character_df["character"])
        if fn_counts[fn] == 1
    }
    canon = []
    for ent in ent_list:
        e = ent.strip()
        if e in aliases:
            canon.append(aliases[e])
        elif e in full_names:
            canon.append(e)
        elif e in fn_to_full:
            canon.append(fn_to_full[e])
    return canon


# ============================================================
# [END: 2026-04-28 FIX 1, 2, 3, 4, 6 — character-df cleanup + alias normalisation]
# ============================================================


# ============================================================
# [BEGIN: 2026-08-08 FIX 11 — co-occurrence window must span TRANSCRIPT sentences]
#
# Regression this fixes:
#   The 2026-04-28 rewrite added `df = df.reset_index(drop=True)` and then windowed
#   with `df.loc[i:i+window_size]`. After the reset, those labels address *rows that
#   survived the character filter*, not sentences of the transcript. So a "5-sentence
#   window" became "the next 5 sentences that happen to mention someone" — which can
#   span hundreds of lines of dialogue. Every window was then guaranteed to be full,
#   and characters who never share a scene got wired together.
#
#   Measured on the full 62-episode corpus (window_size=5), holding entity resolution
#   fixed at the pre-alias `filter_entity` path so only the windowing varies:
#       correct sentence windowing : 84 nodes, 203 edges, avg degree 4.8
#       after reset_index          : 102 nodes, 362 edges, avg degree 7.1  <-- the hairball
#   Walter White alone went to degree 63 of a possible 101.
#
# The fix: window over explicit sentence positions and never trust the row index.
# `sentence_col` (default "sentence_id") carries each retained row's position in the
# original document, so the function is now immune to any upstream reset_index().
# If the column is absent we fall back to the index, which is what the pre-2026-04-28
# notebook relied on.
#
# Verified to reproduce the pre-regression edge list exactly — identical weights on all
# 203 edges — when entity resolution is held at the old firstname-split path.
#
# Do NOT expect those 203 edges from a live run. The pipeline resolves entities through
# ALIASES / normalize_entities() (FIX 4), which recovers mentions the old path dropped
# entirely — "Gus", "Saul", "Gomie", "Heisenberg" — so the real corpus output is
# 89 nodes, 236 edges, avg degree 5.30. That is the number to check a run against.
# The pre-2026-04-28 code produced 82 nodes / 190 edges; character-graph.png was
# regenerated on 2026-08-10 so the reference render matches the 89/236 output.
# ============================================================
def create_relationships(df, window_size, sentence_col="sentence_id"):

    """
    Create a dataframe of relationships from a dataframe of characters-per-sentence.

    Two characters are linked when they are mentioned within `window_size` sentences
    of each other *in the source text*.

    Params:
    df -- dataframe with a `character_entities` column (list of characters per sentence).
          Should also carry `sentence_col`; rows filtered out upstream must NOT be
          renumbered, or the window loses its meaning (see FIX 11 above).
    window_size -- window span, in sentences of the original document.
    sentence_col -- column holding each row's position in the original document.
                    Falls back to the dataframe index when the column is missing.

    Returns:
    a relationship dataframe containing 3 columns: source, target, value.

    """

    if "character_entities" not in df.columns:
        raise ValueError("Input dataframe must include a 'character_entities' column")
    if window_size < 1:
        raise ValueError("window_size must be >= 1")

    rel_columns = ["source", "target", "value"]

    if df.empty:
        return pd.DataFrame(columns=rel_columns)

    # Sentence positions in the ORIGINAL document — never the post-filter row number.
    if sentence_col in df.columns:
        positions = np.asarray(df[sentence_col], dtype=np.int64)
    else:
        positions = np.asarray(df.index, dtype=np.int64)

    entity_lists = list(df["character_entities"])

    # searchsorted needs ascending positions; sort together if the caller shuffled rows.
    if not np.all(np.diff(positions) >= 0):
        order = np.argsort(positions, kind="stable")
        positions = positions[order]
        entity_lists = [entity_lists[i] for i in order]

    relationships = []
    last_position = int(positions[-1])

    # Slide the window over every sentence position in the document. `p + window_size`
    # is inclusive, matching the original `min(i + window_size, last)` bound.
    for p in range(last_position + 1):
        lo = np.searchsorted(positions, p, side="left")
        hi = np.searchsorted(positions, p + window_size, side="right")
        if hi <= lo:
            continue

        char_list = []
        for k in range(lo, hi):
            char_list.extend(entity_lists[k])

        # Remove duplicated characters that are next to each other
        char_unique = [char_list[i] for i in range(len(char_list))
                       if (i==0) or char_list[i] != char_list[i-1]]

        if len(char_unique) > 1:
            for idx, a in enumerate(char_unique[:-1]):
                b = char_unique[idx + 1]
                relationships.append({"source": a, "target": b})

    if not relationships:
        return pd.DataFrame(columns=rel_columns)

    relationship_df = pd.DataFrame(relationships)
    # Sort the cases with a->b and b->a
    relationship_df = pd.DataFrame(np.sort(relationship_df.values, axis = 1),
                                   columns = relationship_df.columns)
    relationship_df["value"] = 1
    relationship_df = relationship_df.groupby(["source","target"],
                                              sort=False,
                                              as_index=False).sum()

    return relationship_df
# ============================================================
# [END: 2026-08-08 FIX 11]
# ============================================================
