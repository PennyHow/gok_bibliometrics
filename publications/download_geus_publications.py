# 02_download_gok_publications.py

from pathlib import Path
import pandas as pd
from pyalex import Institutions, Works, config

# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

with open("../user_key", "r") as f:
    user_key = f.read()
config.email = user_key

with open("../api_key", "r") as f:
    api_key = f.read()
config.api_key = api_key

OUTPUT_FILE = Path("../data/geus_publications.csv")

START_YEAR = 2000
END_YEAR = 2026

# OpenAlex institution ID for:
# Geological Survey of Denmark and Greenland (GEUS)
institute_id = "https://openalex.org/I2801979204"

# ---------------------------------------------------------------------
# DOWNLOAD WORKS
# ---------------------------------------------------------------------

all_works = []

print(f"Downloading works for {institute_id}")

works = (
    Works()
    .filter(
        institutions={"id": institute_id},
        publication_year=f"{START_YEAR}-{END_YEAR}"
    )
)

for page in works.paginate(per_page=200):
    all_works.extend(page)


# ---------------------------------------------------------------------
# REMOVE DUPLICATES
# ---------------------------------------------------------------------

unique_works = {}

for work in all_works:
    unique_works[work["id"]] = work

print(
    f"Downloaded {len(all_works)} institute-work records"
)

print(
    f"Unique publications: {len(unique_works)}"
)


# ---------------------------------------------------------------------
# FLATTEN OPENALEX RECORDS
# ---------------------------------------------------------------------

publication_rows = []
author_rows = []

for work_id, work in unique_works.items():

    publication_rows.append({
        "openalex_id": work["id"],
        "doi": work.get("doi"),
        "title": work.get("title"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "type": work.get("type"),

        "cited_by_count": work.get("cited_by_count"),

        "is_oa": (
            work.get("open_access", {})
            .get("is_oa")
        ),

        "oa_status": (
            work.get("open_access", {})
            .get("oa_status")
        ),

        "primary_location": (
            work.get("primary_location")
        ),

        "primary_topic": (
            work.get("primary_topic")
        ),

        "topics": work.get("topics"),

        "keywords": work.get("keywords"),

        "concepts": work.get("concepts"),

    })

    # ---------------------------------------------------------------
    # AUTHORS
    # ---------------------------------------------------------------

    for position, authorship in enumerate(
        work.get("authorships", [])
    ):

        author = authorship.get("author", {})

        author_rows.append({
            "openalex_work_id": work["id"],

            "author_position": position + 1,

            "author_id": author.get("id"),

            "author_name": author.get("display_name"),

            "orcid": author.get("orcid"),

            "is_corresponding": (
                authorship.get("is_corresponding")
            ),

            "institutions": (
                authorship.get("institutions")
            ),

            "raw_affiliation_strings": (
                authorship.get(
                    "raw_affiliation_strings"
                )
            )
        })


# ---------------------------------------------------------------------
# SAVE
# ---------------------------------------------------------------------

publications = pd.DataFrame(publication_rows)
authors = pd.DataFrame(author_rows)

publications.to_pickle(
    "data/geus_publications.pkl"
)

authors.to_pickle(
    "data/geus_authors.pkl"
)

publications.to_csv(
    OUTPUT_FILE,
    index=False
)

authors.to_csv(
    "data/geus_authors.csv",
    index=False
)

print("\nDone.")
print(f"Publications: {len(publications)}")
print(f"Author records: {len(authors)}")