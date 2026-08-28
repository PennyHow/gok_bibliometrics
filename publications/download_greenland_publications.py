# 09_build_greenland_physical_science_corpus.py

from pathlib import Path
import time

import pandas as pd
from pyalex import Works, config


# =====================================================================
# SETTINGS
# =====================================================================

# ---------------------------------------------------------------------
# OpenAlex configuration
# ---------------------------------------------------------------------

with open("../user_key", "r") as f:
    user_key = f.read()
config.email = user_key

with open("../api_key", "r") as f:
    api_key = f.read()
config.api_key = api_key


# ---------------------------------------------------------------------
# Time period
# ---------------------------------------------------------------------

START_YEAR = 2000
END_YEAR = 2025


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------

OUTPUT_DIR = Path("../data")

OUTPUT_DIR.mkdir(
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "greenland_physical_science.csv"
)

OUTPUT_PKL = (
    OUTPUT_DIR
    / "greenland_physical_science.pkl"
)


# ---------------------------------------------------------------------
# Search strategy
# ---------------------------------------------------------------------

# These searches are deliberately broad.
#
# The aim here is to build a candidate Greenland physical-science
# corpus, NOT to perfectly identify cryosphere/geology/etc.
#
# We will classify the resulting corpus in a later script.

SEARCH_TERMS = [

    # ---------------------------------------------------------------
    # General Greenland
    # ---------------------------------------------------------------

    "Greenland",
    "Greenlandic",

    # ---------------------------------------------------------------
    # Ice / cryosphere
    # ---------------------------------------------------------------

    "Greenland Ice Sheet",
    "Greenland ice sheet",
    "Greenland glacier",
    "Greenland glaciers",
    "Greenland ice cap",
    "Greenland ice caps",
    "Greenland glaciology",
    "Greenland ice",
    "Greenland firn",
    "Greenland snow",
    "Greenland melt",
    "Greenland ice dynamics",
    "Greenland mass balance",
    "Greenland ice core",

    # ---------------------------------------------------------------
    # Climate / palaeoclimate
    # ---------------------------------------------------------------

    "Greenland climate",
    "Greenland climate change",
    "Greenland paleoclimate",
    "Greenland palaeoclimate",
    "Greenland paleoenvironment",
    "Greenland palaeoenvironment",
    "Greenland Holocene",
    "Greenland Quaternary",
    "Greenland ice core climate",

    # ---------------------------------------------------------------
    # Geology
    # ---------------------------------------------------------------

    "Greenland geology",
    "Greenland geological",
    "Greenland bedrock",
    "Greenland tectonics",
    "Greenland geochemistry",
    "Greenland sediment",
    "Greenland sedimentology",
    "Greenland geomorphology",
    "Greenland geophysics",
    "Greenland seismic",

    # ---------------------------------------------------------------
    # Ocean / fjords / coastal
    # ---------------------------------------------------------------

    "Greenland ocean",
    "Greenland Sea",
    "Greenland fjord",
    "Greenland fjords",
    "Greenland coastline",
    "Greenland coastal",

    # ---------------------------------------------------------------
    # Hydrology / freshwater
    # ---------------------------------------------------------------

    "Greenland hydrology",
    "Greenland freshwater",
    "Greenland runoff",
    "Greenland meltwater",

    # ---------------------------------------------------------------
    # Atmosphere
    # ---------------------------------------------------------------

    "Greenland atmosphere",
    "Greenland atmospheric",
    "Greenland precipitation",

    # ---------------------------------------------------------------
    # Landscape / environment
    # ---------------------------------------------------------------

    "Greenland permafrost",
    "Greenland landscape",
    "Greenland environmental",
]


# ---------------------------------------------------------------------
# Publication types
# ---------------------------------------------------------------------

# We are interested primarily in research articles.
#
# You can add "review" later if you want reviews included.

INCLUDED_TYPES = {
    "article",
    "review",
}


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def safe_get(dictionary, *keys):
    """
    Safely retrieve nested dictionary values.
    """

    value = dictionary

    for key in keys:

        if not isinstance(
            value,
            dict
        ):
            return None

        value = value.get(key)

    return value


def extract_primary_topic(work):
    """
    Extract the OpenAlex primary topic.
    """

    topic = work.get(
        "primary_topic"
    )

    if not isinstance(
        topic,
        dict
    ):
        return None

    return topic.get(
        "display_name"
    )


def extract_topic_field(
    work,
    field
):

    topic = work.get(
        "primary_topic"
    )

    if not isinstance(
        topic,
        dict
    ):
        return None

    nested = topic.get(
        field
    )

    if not isinstance(
        nested,
        dict
    ):
        return None

    return nested.get(
        "display_name"
    )


def extract_author_ids(work):
    """
    Extract all OpenAlex author IDs.
    """

    author_ids = []

    for authorship in work.get(
        "authorships",
        []
    ):

        author = authorship.get(
            "author",
            {}
        )

        author_id = author.get(
            "id"
        )

        if author_id:
            author_ids.append(
                author_id
            )

    return author_ids


def extract_author_names(work):
    """
    Extract all author names.
    """

    names = []

    for authorship in work.get(
        "authorships",
        []
    ):

        author = authorship.get(
            "author",
            {}
        )

        name = author.get(
            "display_name"
        )

        if name:
            names.append(
                name
            )

    return names


# =====================================================================
# DOWNLOAD
# =====================================================================

print("=" * 70)
print("GREENLAND PHYSICAL SCIENCE CORPUS")
print("=" * 70)

print(
    f"Years: {START_YEAR}-{END_YEAR}"
)

print(
    f"Search terms: {len(SEARCH_TERMS)}"
)

print()


# ---------------------------------------------------------------------
# Download records
# ---------------------------------------------------------------------

all_works = []


for i, search_term in enumerate(
    SEARCH_TERMS,
    start=1
):

    print(
        f"[{i}/{len(SEARCH_TERMS)}] "
        f"Searching: {search_term}"
    )

    try:

        works = (
            Works()
            .search(
                search_term
            )
            .filter(
                publication_year=(
                    f"{START_YEAR}-{END_YEAR}"
                )
            )
        )


        result_count = 0


        # -------------------------------------------------------------
        # Cursor pagination
        # -------------------------------------------------------------

        for page in works.paginate(
            per_page=100
        ):

            all_works.extend(
                page
            )

            result_count += len(
                page
            )


        print(
            f"    Retrieved {result_count:,} records"
        )


    except Exception as e:

        print(
            f"    ERROR: {e}"
        )

        print(
            "    Continuing with next search..."
        )

        continue


    # Small delay between searches.
    #
    # Your API key gives you much better access than anonymous requests,
    # but there is still no reason to hammer the API unnecessarily.

    time.sleep(
        0.2
    )


print()
print(
    f"Total search-result records: "
    f"{len(all_works):,}"
)


# =====================================================================
# DEDUPLICATION
# =====================================================================

unique_works = {}


for work in all_works:

    work_id = work.get(
        "id"
    )

    if work_id:

        unique_works[
            work_id
        ] = work


print(
    f"Unique OpenAlex works: "
    f"{len(unique_works):,}"
)


# =====================================================================
# FILTER PUBLICATION TYPES
# =====================================================================

filtered_works = []


for work in unique_works.values():

    work_type = work.get(
        "type"
    )

    if work_type not in INCLUDED_TYPES:
        continue

    filtered_works.append(
        work
    )


print(
    f"After publication-type filtering: "
    f"{len(filtered_works):,}"
)


# =====================================================================
# FLATTEN RECORDS
# =====================================================================

publication_rows = []


for work in filtered_works:

    primary_topic = (
        work.get(
            "primary_topic"
        )
    )


    # ---------------------------------------------------------------
    # Topic information
    # ---------------------------------------------------------------

    primary_topic_name = (
        extract_primary_topic(
            work
        )
    )

    primary_subfield = (
        extract_topic_field(
            work,
            "subfield"
        )
    )

    primary_field = (
        extract_topic_field(
            work,
            "field"
        )
    )

    primary_domain = (
        extract_topic_field(
            work,
            "domain"
        )
    )


    # ---------------------------------------------------------------
    # Primary location
    # ---------------------------------------------------------------

    primary_location = (
        work.get(
            "primary_location"
        )
    )

    journal = None

    if isinstance(
        primary_location,
        dict
    ):

        source = (
            primary_location.get(
                "source"
            )
        )

        if isinstance(
            source,
            dict
        ):

            journal = (
                source.get(
                    "display_name"
                )
            )


    # ---------------------------------------------------------------
    # Authors
    # ---------------------------------------------------------------

    author_ids = (
        extract_author_ids(
            work
        )
    )

    author_names = (
        extract_author_names(
            work
        )
    )


    # ---------------------------------------------------------------
    # Institutions
    # ---------------------------------------------------------------

    institution_ids = []

    institution_names = []

    institution_countries = []


    for authorship in work.get(
        "authorships",
        []
    ):

        for institution in authorship.get(
            "institutions",
            []
        ):

            institution_id = (
                institution.get(
                    "id"
                )
            )

            institution_name = (
                institution.get(
                    "display_name"
                )
            )

            country_code = (
                institution.get(
                    "country_code"
                )
            )


            if institution_id:
                institution_ids.append(
                    institution_id
                )

            if institution_name:
                institution_names.append(
                    institution_name
                )

            if country_code:
                institution_countries.append(
                    country_code
                )


    # ---------------------------------------------------------------
    # Save row
    # ---------------------------------------------------------------

    publication_rows.append({

        # -----------------------------------------------------------
        # Basic bibliographic information
        # -----------------------------------------------------------

        "openalex_id":
            work.get("id"),

        "doi":
            work.get("doi"),

        "title":
            work.get("title"),

        "publication_year":
            work.get(
                "publication_year"
            ),

        "publication_date":
            work.get(
                "publication_date"
            ),

        "type":
            work.get(
                "type"
            ),

        "cited_by_count":
            work.get(
                "cited_by_count"
            ),


        # -----------------------------------------------------------
        # Open access
        # -----------------------------------------------------------

        "is_oa":
            safe_get(
                work,
                "open_access",
                "is_oa"
            ),

        "oa_status":
            safe_get(
                work,
                "open_access",
                "oa_status"
            ),


        # -----------------------------------------------------------
        # Journal
        # -----------------------------------------------------------

        "journal":
            journal,


        # -----------------------------------------------------------
        # Research topics
        # -----------------------------------------------------------

        "primary_topic":
            primary_topic_name,

        "primary_subfield":
            primary_subfield,

        "primary_field":
            primary_field,

        "primary_domain":
            primary_domain,

        "topics":
            work.get(
                "topics"
            ),

        "keywords":
            work.get(
                "keywords"
            ),

        "concepts":
            work.get(
                "concepts"
            ),


        # -----------------------------------------------------------
        # Authors
        # -----------------------------------------------------------

        "author_ids":
            author_ids,

        "author_names":
            author_names,

        "author_count":
            len(
                author_ids
            ),


        # -----------------------------------------------------------
        # Institutions
        # -----------------------------------------------------------

        "institution_ids":
            institution_ids,

        "institution_names":
            institution_names,

        "institution_countries":
            institution_countries,


        # -----------------------------------------------------------
        # Locations
        # -----------------------------------------------------------

        "primary_location":
            primary_location,

    })


# =====================================================================
# CREATE DATAFRAME
# =====================================================================

corpus = pd.DataFrame(
    publication_rows
)


# =====================================================================
# REMOVE ANY REMAINING DUPLICATES
# =====================================================================

corpus = (
    corpus
    .drop_duplicates(
        subset="openalex_id"
    )
    .reset_index(
        drop=True
    )
)


print()
print(
    f"Final corpus: "
    f"{len(corpus):,} publications"
)


# =====================================================================
# SAVE
# =====================================================================

corpus.to_pickle(
    OUTPUT_PKL
)

corpus.to_csv(
    OUTPUT_FILE,
    index=False
)


print()
print(
    f"Saved:"
)

print(
    f"  {OUTPUT_FILE}"
)

print(
    f"  {OUTPUT_PKL}"
)


# =====================================================================
# BASIC DIAGNOSTICS
# =====================================================================

print()
print("=" * 70)
print("CORPUS DIAGNOSTICS")
print("=" * 70)


# ---------------------------------------------------------------------
# Publications by year
# ---------------------------------------------------------------------

print()
print("Publications by year:")

year_counts = (
    corpus
    .groupby(
        "publication_year"
    )
    .size()
)

print(
    year_counts.to_string()
)


# ---------------------------------------------------------------------
# Publication types
# ---------------------------------------------------------------------

print()
print("Publication types:")

print(
    corpus[
        "type"
    ]
    .value_counts()
    .to_string()
)


# ---------------------------------------------------------------------
# Primary research domains
# ---------------------------------------------------------------------

print()
print("Top primary research domains:")

print(
    corpus[
        "primary_domain"
    ]
    .value_counts(
        dropna=False
    )
    .head(20)
    .to_string()
)


# ---------------------------------------------------------------------
# Primary research fields
# ---------------------------------------------------------------------

print()
print("Top primary research fields:")

print(
    corpus[
        "primary_field"
    ]
    .value_counts(
        dropna=False
    )
    .head(30)
    .to_string()
)


# ---------------------------------------------------------------------
# Primary research topics
# ---------------------------------------------------------------------

print()
print("Top primary research topics:")

print(
    corpus[
        "primary_topic"
    ]
    .value_counts(
        dropna=False
    )
    .head(30)
    .to_string()
)


# ---------------------------------------------------------------------
# Topic coverage
# ---------------------------------------------------------------------

with_topic = (
    corpus[
        "primary_topic"
    ]
    .notna()
    .sum()
)

without_topic = (
    len(corpus)
    - with_topic
)

print()
print(
    f"Publications with primary topic: "
    f"{with_topic:,}"
)

print(
    f"Publications without primary topic: "
    f"{without_topic:,}"
)


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------

print()
print("=" * 70)
print("DONE")
print("=" * 70)

print(
    f"Greenland physical-science corpus: "
    f"{len(corpus):,} publications"
)

print(
    f"Period: {START_YEAR}-{END_YEAR}"
)

print(
    "The corpus is now ready for classification."
)