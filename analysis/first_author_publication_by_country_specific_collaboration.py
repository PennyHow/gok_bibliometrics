from pathlib import Path
import ast

import pandas as pd
import matplotlib.pyplot as plt


# =====================================================================
# SETTINGS
# =====================================================================

PUBLICATIONS_FILE = Path(
    "../data/gok_publications.csv"
)

AUTHORS_FILE = Path(
    "../data/gok_authors.csv"
)

OUTPUT_DIR = Path("../output")
FIGURE_DIR = OUTPUT_DIR / "figures"

OUTPUT_DIR.mkdir(exist_ok=True)
FIGURE_DIR.mkdir(exist_ok=True)


START_YEAR = 2010
END_YEAR = 2025


# ---------------------------------------------------------------------
# IMPORTANT:
# Use the SAME GEUS OpenAlex institution ID that you used in the
# publication-download script and the first-author script.
# ---------------------------------------------------------------------

GEUS_OPENALEX_ID = "https://openalex.org/I2801979204"


# ISO 3166-1 alpha-2 country code
COUNTRY_CODE = "DK"


# =====================================================================
# LOAD DATA
# =====================================================================

pubs = pd.read_csv(PUBLICATIONS_FILE)
authors = pd.read_csv(AUTHORS_FILE)


print(
    f"Loaded {len(pubs):,} publications"
)

print(
    f"Loaded {len(authors):,} author records"
)


# =====================================================================
# FILTER PUBLICATIONS
# =====================================================================

pubs = pubs[
    pubs["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()


# Only include articles
pubs = pubs[
    pubs["type"] == "article"
].copy()


print()
print(
    f"Qualifying article publications: "
    f"{len(pubs):,}"
)


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def parse_list(value):
    """
    Convert a string representation of a Python list/dictionary
    back into Python objects.
    """

    if pd.isna(value):
        return []

    if isinstance(value, list):
        return value

    try:
        return ast.literal_eval(value)

    except (ValueError, SyntaxError):
        return []


def has_geus_affiliation(value):
    """
    Check whether an author's institutions include GEUS.
    """

    institutions = parse_list(value)

    if not isinstance(institutions, list):
        return False

    for institution in institutions:

        if not isinstance(institution, dict):
            continue

        institution_id = institution.get("id")

        if institution_id == GEUS_OPENALEX_ID:
            return True

    return False


def has_country_affiliation(value):
    """
    Check whether an author has at least one institution
    located in specified country.
    """

    institutions = parse_list(value)

    if not isinstance(institutions, list):
        return False

    for institution in institutions:

        if not isinstance(institution, dict):
            continue

        country_code = institution.get(
            "country_code"
        )

        if country_code == COUNTRY_CODE:
            return True

    return False


# =====================================================================
# IDENTIFY FIRST AUTHORS
# =====================================================================

first_authors = authors[
    authors["author_position"] == 1
].copy()


print()
print(
    f"First-author records: "
    f"{len(first_authors):,}"
)


# =====================================================================
# IDENTIFY GEUS FIRST AUTHORS
# =====================================================================

first_authors["is_geus_first_author"] = (
    first_authors["institutions"]
    .apply(has_geus_affiliation)
)


geus_first_authors = first_authors[
    first_authors["is_geus_first_author"]
].copy()


print(
    f"GEUS first-author records: "
    f"{len(geus_first_authors):,}"
)


# =====================================================================
# IDENTIFY COUNTRY-AFFILIATED AUTHORS
# =====================================================================

authors["has_country_affiliation"] = (
    authors["institutions"]
    .apply(has_country_affiliation)
)


country_authors = authors[
    authors["has_country_affiliation"]
].copy()


print(
    f"Authors with Country affiliations: "
    f"{len(country_authors):,}"
)


# =====================================================================
# GEUS FIRST-AUTHOR PUBLICATIONS
# =====================================================================

geus_first_author_work_ids = set(
    geus_first_authors[
        "openalex_work_id"
    ]
)


# =====================================================================
# FIND COUNTRY CO-AUTHORS
# =====================================================================

country_authors_on_geus_pubs = (
    country_authors[
        country_authors[
            "openalex_work_id"
        ].isin(
            geus_first_author_work_ids
        )
    ]
    .copy()
)


# ---------------------------------------------------------------------
# Exclude the first author.
#
# We want country-specific CO-AUTHORS, not merely a first author who also
# happens to have a country-specific affiliation.
# ---------------------------------------------------------------------

country_coauthors = (
    country_authors_on_geus_pubs[
        country_authors_on_geus_pubs[
            "author_position"
        ] != 1
    ]
    .copy()
)


# =====================================================================
# IDENTIFY PUBLICATIONS WITH COUNTRY CO-AUTHORS
# =====================================================================

country_collaboration_work_ids = set(
    country_coauthors[
        "openalex_work_id"
    ]
)


# =====================================================================
# BUILD COMPLETE GEUS FIRST-AUTHOR PUBLICATION DATASET
# =====================================================================

geus_first_author_pubs = pubs[
    pubs["openalex_id"].isin(
        geus_first_author_work_ids
    )
].copy()


# ---------------------------------------------------------------------
# Mark whether each publication has a country-specific co-author
# ---------------------------------------------------------------------

geus_first_author_pubs[
    "country_collaboration"
] = (
    geus_first_author_pubs[
        "openalex_id"
    ].isin(
        country_collaboration_work_ids
    )
)


print()
print(
    f"Total GEUS first-author publications: "
    f"{len(geus_first_author_pubs):,}"
)

print(
    f"With {COUNTRY_CODE} co-author: "
    f"{geus_first_author_pubs['country_collaboration'].sum():,}"
)

print(
    f"Without {COUNTRY_CODE} co-author: "
    f"{(~geus_first_author_pubs['country_collaboration']).sum():,}"
)


# =====================================================================
# PUBLICATIONS BY YEAR
# =====================================================================

summary = (

    geus_first_author_pubs

    .groupby(
        [
            "publication_year",
            "country_collaboration"
        ]
    )

    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )

    .reset_index()
)


# =====================================================================
# RESHAPE INTO WITH / WITHOUT COUNTRY
# =====================================================================

summary_pivot = (

    summary

    .pivot(
        index="publication_year",
        columns="country_collaboration",
        values="publications"
    )

    .fillna(0)

    .reset_index()
)


# Rename the boolean columns

summary_pivot = summary_pivot.rename(
    columns={
        True:
            "with_country",
        False:
            "without_country"
    }
)


# Make sure both columns exist
# even if one category happens to have no publications.

if "with_country" not in summary_pivot.columns:
    summary_pivot["with_country"] = 0

if "without_country" not in summary_pivot.columns:
    summary_pivot["without_country"] = 0


summary_pivot["with_country"] = (
    summary_pivot["with_country"]
    .astype(int)
)

summary_pivot["without_country"] = (
    summary_pivot["without_country"]
    .astype(int)
)


# =====================================================================
# INCLUDE ALL YEARS
# =====================================================================

all_years = pd.DataFrame({
    "publication_year": range(
        START_YEAR,
        END_YEAR + 1
    )
})


summary_pivot = (

    all_years

    .merge(
        summary_pivot,
        on="publication_year",
        how="left"
    )

    .fillna(0)
)


summary_pivot["with_country"] = (
    summary_pivot["with_country"]
    .astype(int)
)

summary_pivot["without_country"] = (
    summary_pivot["without_country"]
    .astype(int)
)


# =====================================================================
# TOTALS
# =====================================================================

summary_pivot["total_first_author_publications"] = (

    summary_pivot["with_country"]

    + summary_pivot["without_country"]
)


# =====================================================================
# PERCENTAGES
# =====================================================================

summary_pivot["country_percentage"] = (

    100
    * summary_pivot["with_country"]
    / summary_pivot[
        "total_first_author_publications"
    ]

).fillna(0)


summary_pivot["non_country_percentage"] = (

    100
    * summary_pivot["without_country"]
    / summary_pivot[
        "total_first_author_publications"
    ]

).fillna(0)


# =====================================================================
# SAVE DATA
# =====================================================================

summary_pivot.to_csv(

    OUTPUT_DIR
    / f"geus_first_author_{COUNTRY_CODE}_collaboration_by_year.csv",

    index=False
)


# =====================================================================
# SAVE PUBLICATION LIST
# =====================================================================

publication_list = geus_first_author_pubs[
    [
        "openalex_id",
        "publication_year",
        "title",
        "doi",
        "country_collaboration"
    ]
].copy()


publication_list = publication_list.sort_values(
    [
        "publication_year",
        "country_collaboration",
        "title"
    ]
)


publication_list.to_csv(

    OUTPUT_DIR
    / f"geus_first_author_{COUNTRY_CODE}_collaboration.csv",

    index=False
)


# =====================================================================
# PRINT SUMMARY
# =====================================================================

print()
print("=" * 75)
print(
    f"GEUS FIRST-AUTHOR PUBLICATIONS AND {COUNTRY_CODE} COLLABORATION"
)
print("=" * 75)

print()

print(
    summary_pivot.to_string(
        index=False
    )
)

print()

print(
    f"Total GEUS first-author publications: "
    f"{len(geus_first_author_pubs):,}"
)

print(
    f"Total with {COUNTRY_CODE} co-authors: "
    f"{geus_first_author_pubs['country_collaboration'].sum():,}"
)

print(
    f"Overall percentage with {COUNTRY_CODE} co-authors: "
    f"{100 * geus_first_author_pubs['country_collaboration'].mean():.1f}%"
)


# =====================================================================
# 100% STACKED BAR CHART
# =====================================================================

plt.figure(
    figsize=(10, 6)
)


plt.bar(

    summary_pivot["publication_year"],

    summary_pivot["with_country"],

    label=f"With {COUNTRY_CODE} co-author"
)


plt.bar(

    summary_pivot["publication_year"],

    summary_pivot["without_country"],

    bottom=summary_pivot["with_country"],

    label=f"Without {COUNTRY_CODE} co-author"
)

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Number of first-author publications"
)

plt.title(
    "GEUS first-author publications\n"
    f"with and without {COUNTRY_CODE} co-authors"
)


plt.xticks(
    range(
        START_YEAR,
        END_YEAR + 1,
        2
    ),
    rotation=45
)


plt.legend()

plt.tight_layout()


plt.savefig(

    FIGURE_DIR
    / f"geus_first_author_{COUNTRY_CODE}_collaboration_by_year.png",

    dpi=300
)

plt.close()


# =====================================================================
# 100% STACKED PERCENTAGE BAR CHART
# =====================================================================

plt.figure(
    figsize=(10, 6)
)


plt.bar(

    summary_pivot["publication_year"],

    summary_pivot["country_percentage"],

    label=f"With {COUNTRY_CODE} co-author"
)


plt.bar(

    summary_pivot["publication_year"],

    summary_pivot["non_country_percentage"],

    bottom=summary_pivot["country_percentage"],

    label=f"Without {COUNTRY_CODE} co-author"
)


plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Percentage of GEUS first-author publications"
)

plt.title(
    "GEUS first-author publications\n"
    f"{COUNTRY_CODE} collaboration"
)


plt.ylim(
    0,
    100
)


plt.xticks(
    range(
        START_YEAR,
        END_YEAR + 1,
        2
    ),
    rotation=45
)


plt.legend()

plt.tight_layout()


plt.savefig(

    FIGURE_DIR
    / f"geus_first_author_{COUNTRY_CODE}_collaboration_percentage_by_year.png",

    dpi=300
)

plt.close()


# =====================================================================
# DONE
# =====================================================================

print()
print("Analysis complete.")

print(
    f"Saved: "
    f"{OUTPUT_DIR / f'geus_first_author_{COUNTRY_CODE}_collaboration_by_year.csv'}"
)

print(
    f"Saved publication list: "
    f"{OUTPUT_DIR / f'geus_first_author_{COUNTRY_CODE}.csv'}"
)

print(
    f"Saved figure: "
    f"{FIGURE_DIR / f'geus_first_author_{COUNTRY_CODE}.png'}"
)

print(
    f"Saved percentage figure: "
    f"{FIGURE_DIR / f'geus_first_author_{COUNTRY_CODE}_collaboration_percentage_by_year.png'}"
)