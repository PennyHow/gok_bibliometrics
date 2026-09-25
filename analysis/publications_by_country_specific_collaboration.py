from pathlib import Path
import ast
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

PUBLICATIONS_FILE = Path(
    "../data/gok_publications.csv"
)

AUTHORS_FILE = Path(
    "../data/gok_authors.csv"
)

OUTPUT_DIR = Path("../output")

FIGURE_DIR = OUTPUT_DIR / "figures"

OUTPUT_DIR.mkdir(
    exist_ok=True
)

FIGURE_DIR.mkdir(
    exist_ok=True
)

START_YEAR = 2016
END_YEAR = 2025


# ---------------------------------------------------------------------
# DEFINITION OF COUNTRY AFFILIATION
# ---------------------------------------------------------------------
#
# OpenAlex assigns institutions a country code.
#
# Greenland = GL
# Denmark = DK
# America = US
#
# We therefore identify a affiliation when at least one
# institution in an authorship has the defined country_code.


COUNTRY_CODE = "GL"

# ---------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------

pubs = pd.read_csv(
    PUBLICATIONS_FILE
)

authors = pd.read_csv(
    AUTHORS_FILE
)


print(
    f"Loaded {len(pubs)} publications"
)

print(
    f"Loaded {len(authors)} author records"
)

# ---------------------------------------------------------------------
# FILTER YEARS AND PUBLICATION TYPE
# ---------------------------------------------------------------------

pubs = pubs[
    pubs["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()

pubs = pubs[
    pubs["type"] == "article"
].copy()


print(
    f"Publications after year/type filtering: "
    f"{len(pubs)}"
)

# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------

def parse_institutions(value):
    """
    Convert the 'institutions' column from the CSV back into
    a Python list of dictionaries.

    The CSV contains nested OpenAlex structures that pandas reads
    as strings.
    """
    if pd.isna(value):
        return []

    if isinstance(value, list):
        return value

    try:
        parsed = ast.literal_eval(value)
    except (
        ValueError,
        SyntaxError
    ):
        return []

    if not isinstance(parsed, list):
        return []

    return parsed


def get_country_institutions(value):
    """
    Return structured institution records from country_code
    """
    institutions = parse_institutions(
        value
    )

    country_institutions = []

    for institution in institutions:

        if not isinstance(
            institution,
            dict
        ):
            continue

        country_code = (
            institution.get(
                "country_code"
            )
        )

        if country_code == COUNTRY_CODE:

            country_institutions.append(
                institution
            )

    return country_institutions


def institution_names(institutions):
    """
    Return unique institution names as a sorted list.
    """

    names = set()

    for institution in institutions:
        name = institution.get(
            "display_name"
        )
        if name:
            names.add(name)

    return sorted(names)


def institution_ids(institutions):
    """
    Return unique OpenAlex institution IDs.
    """

    ids = set()

    for institution in institutions:
        institution_id = institution.get(
            "id"
        )
        if institution_id:
            ids.add(institution_id)

    return sorted(ids)


# ---------------------------------------------------------------------
# IDENTIFY COUNTRY AFFILIATIONS
# ---------------------------------------------------------------------

authors[
    "country_institutions"
] = (
    authors["institutions"]
    .apply(
        get_country_institutions
    )
)


authors[
    "has_country_affiliation"
] = (
    authors[
        "country_institutions"
    ]
    .apply(
        lambda x: len(x) > 0
    )
)


authors[
    "country_institution_names"
] = (
    authors[
        "country_institutions"
    ]
    .apply(
        institution_names
    )
)


authors[
    "country_institution_ids"
] = (
    authors[
        "country_institutions"
    ]
    .apply(
        institution_ids
    )
)


# ---------------------------------------------------------------------
# DEFINE CO-AUTHOR FROM SPECIFIED COUNTRY
# ---------------------------------------------------------------------
# A country-specific co-author is an author on a GoK publication who has
# a country-specific institutional affiliation.
#
# We exclude the GoK+GEUS authors from this definition, because the
# purpose here is to measure collaboration between GoK and institutions
# in the specified country.
# ---------------------------------------------------------------------

if "is_gok_geus_author" in authors.columns:

    authors[
        "is_country_coauthor"
    ] = (
        authors[
            "has_country_affiliation"
        ]
        &
        ~authors[
            "is_gok_geus_author"
        ].fillna(False)
    )

else:

    # Fallback if the column does not exist.
    authors[
        "is_country_coauthor"
    ] = authors[
        "has_country_affiliation"
    ]


# ---------------------------------------------------------------------
# SAVE AUTHOR-LEVEL COUNTRY INFORMATION
# ---------------------------------------------------------------------

authors.to_pickle(
    OUTPUT_DIR
    / f"gok_authors_{COUNTRY_CODE}.pkl"
)

authors.to_csv(
    OUTPUT_DIR
    / f"gok_authors_{COUNTRY_CODE}.csv",
    index=False
)


# ---------------------------------------------------------------------
# PUBLICATION-LEVEL COUNTRY INFORMATION
# ---------------------------------------------------------------------

country_author_records = (
    authors[
        authors[
            "is_country_coauthor"
        ]
    ]
    .copy()
)


# Unique publications with at least one country co-author
country_work_ids = set(
    country_author_records[
        "openalex_work_id"
    ]
)


pubs[
    "has_country_coauthor"
] = (
    pubs["openalex_id"]
    .isin(country_work_ids)
)


# ---------------------------------------------------------------------
# COUNT COUNTRY AUTHORS PER PUBLICATION
# ---------------------------------------------------------------------

country_counts = (
    country_author_records
    .groupby(
        "openalex_work_id"
    )
    .agg(
        country_coauthors=(
            "author_id",
            "nunique"
        )
    )
    .reset_index()
)


pubs = pubs.merge(
    country_counts,
    left_on="openalex_id",
    right_on="openalex_work_id",
    how="left"
)


pubs[
    "country_coauthors"
] = (
    pubs[
        "country_coauthors"
    ]
    .fillna(0)
    .astype(int)
)


# ---------------------------------------------------------------------
# COUNTRY INSTITUTIONS PER PUBLICATION
# ---------------------------------------------------------------------

country_institution_rows = []

for _, row in country_author_records.iterrows():

    work_id = row[
        "openalex_work_id"
    ]

    institutions = row[
        "country_institutions"
    ]

    for institution in institutions:

        country_institution_rows.append({

            "openalex_work_id":
                work_id,

            "author_id":
                row.get("author_id"),

            "author_name":
                row.get("author_name"),

            "institution_id":
                institution.get("id"),

            "institution_name":
                institution.get(
                    "display_name"
                ),

            "country_code":
                institution.get(
                    "country_code"
                ),

        })

country_institution_authors = (
    pd.DataFrame(
        country_institution_rows
    )
)


# ---------------------------------------------------------------------
# UNIQUE COUNTRY INSTITUTIONS PER PAPER
# ---------------------------------------------------------------------

if len(
    country_institution_authors
) > 0:

    institution_per_work = (
        country_institution_authors
        .groupby(
            "openalex_work_id"
        )
        .agg(
            country_institutions=(
                "institution_name",
                lambda x:
                    "; ".join(
                        sorted(
                            set(x)
                        )
                    )
            ),
            country_institution_count=(
                "institution_id",
                "nunique"
            ),
        )
        .reset_index()
    )

else:

    institution_per_work = pd.DataFrame(
        columns=[
            "openalex_work_id",
            "country_institutions",
            "country_institution_count",
        ]
    )


pubs = pubs.merge(
    institution_per_work,
    left_on="openalex_id",
    right_on="openalex_work_id",
    how="left"
)


pubs[
    "country_institution_count"
] = (
    pubs[
        "country_institution_count"
    ]
    .fillna(0)
    .astype(int)
)


pubs[
    "country_institutions"
] = (
    pubs[
        "country_institutions"
    ]
    .fillna("")
)


# ---------------------------------------------------------------------
# SAVE PUBLICATION-LEVEL DATA
# ---------------------------------------------------------------------

pubs.to_pickle(
    OUTPUT_DIR
    / f"gok_publications_{COUNTRY_CODE}.pkl"
)

pubs.to_csv(
    OUTPUT_DIR
    / f"gok_publications_{COUNTRY_CODE}.csv",
    index=False
)

# ---------------------------------------------------------------------
# STATISTICS: PUBLICATIONS WITH COUNTRY COLLABORATION
# ---------------------------------------------------------------------

country_by_year = (
    pubs
    .groupby(
        "publication_year"
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        ),

        publications_with_country=(
            "has_country_coauthor",
            "sum"
        ),
    )
    .reset_index()
)

country_by_year[
    "percentage_with_country"
] = (
    100
    *
    country_by_year[
        "publications_with_country"
    ]
    /
    country_by_year[
        "publications"
    ]
)

country_by_year.to_csv(
    OUTPUT_DIR
    / f"{COUNTRY_CODE}_collaboration_by_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# STATISTICS: COUNTRY INSTITUTIONS
# ---------------------------------------------------------------------

if len(
    country_institution_authors
) > 0:

    institution_summary = (
        country_institution_authors
        .groupby(
            [
                "institution_id",
                "institution_name",
            ]
        )
        .agg(
            publications=(
                "openalex_work_id",
                "nunique"
            ),

            authors=(
                "author_id",
                "nunique"
            ),
        )
        .reset_index()
        .sort_values(
            "publications",
            ascending=False
        )
    )

else:

    institution_summary = pd.DataFrame(
        columns=[
            "institution_id",
            "institution_name",
            "publications",
            "authors",
        ]
    )


institution_summary.to_csv(
    OUTPUT_DIR
    / f"{COUNTRY_CODE}_institutions.csv",
    index=False
)


# ---------------------------------------------------------------------
# INSTITUTION × YEAR
# ---------------------------------------------------------------------

if len(
    country_institution_authors
) > 0:

    # Add publication year
    institution_year = (
        country_institution_authors
        .merge(
            pubs[
                [
                    "openalex_id",
                    "publication_year",
                ]
            ],
            left_on="openalex_work_id",
            right_on="openalex_id",
            how="left"
        )
    )

    institution_by_year = (
        institution_year
        .groupby(
            [
                "publication_year",
                "institution_id",
                "institution_name",
            ]
        )
        .agg(
            publications=(
                "openalex_work_id",
                "nunique"
            )
        )
        .reset_index()
    )

else:

    institution_by_year = pd.DataFrame(
        columns=[
            "publication_year",
            "institution_id",
            "institution_name",
            "publications",
        ]
    )


institution_by_year.to_csv(
    OUTPUT_DIR
    / f"{COUNTRY_CODE}_institutions_by_year.csv",
    index=False
)

# ---------------------------------------------------------------------
# COUNTRY-SPECIFIC AUTHORS
# ---------------------------------------------------------------------
#
# Save one row per country-specific co-author + institution.
#
# This preserves which institution(s) each co-author was affiliated
# with on the publication.
# ---------------------------------------------------------------------

if len(
    country_institution_authors
) > 0:

    country_authors_summary = (
        country_institution_authors
        .groupby(
            [
                "author_id",
                "author_name",
                "institution_id",
                "institution_name",
            ]
        )
        .agg(
            publications=(
                "openalex_work_id",
                "nunique"
            )
        )
        .reset_index()
        .sort_values(
            "publications",
            ascending=False
        )
    )

else:

    country_authors_summary = pd.DataFrame(
        columns=[
            "author_id",
            "author_name",
            "institution_id",
            "institution_name",
            "publications",
        ]
    )


country_authors_summary.to_csv(
    OUTPUT_DIR
    / f"{COUNTRY_CODE}_coauthors.csv",
    index=False
)

# ---------------------------------------------------------------------
# SUMMARY STATISTICS
# ---------------------------------------------------------------------

total_publications = len(pubs)

country_publications = int(
    pubs[
        "has_country_coauthor"
    ].sum()
)


if total_publications > 0:

    country_percentage = (
        100
        *
        country_publications
        /
        total_publications
    )

else:

    country_percentage = 0


print("\n")
print("=" * 70)
print(f"{COUNTRY_CODE} COLLABORATION ANALYSIS")
print("=" * 70)

print(
    f"Total GoK publications: "
    f"{total_publications}"
)

print(
    f"Publications with {COUNTRY_CODE} "
    f"co-author: "
    f"{country_publications}"
)

print(
    f"Percentage with {COUNTRY_CODE} "
    f"collaboration: "
    f"{country_percentage:.1f}%"
)

print(
    f"Unique {COUNTRY_CODE} institutions: "
    f"{len(institution_summary)}"
)

print(
    f"Unique {COUNTRY_CODE} co-authors: "
    f"{len(country_authors_summary)}"
)


if len(
    institution_summary
) > 0:

    print(f"\nTop {COUNTRY_CODE} institutions:")

    print(
        institution_summary
        .head(10)
        .to_string(
            index=False
        )
    )


# ---------------------------------------------------------------------
# PLOT: PUBLICATIONS PER YEAR — COUNTRY VS NO COUNTRY
# ---------------------------------------------------------------------

country_by_year["publications_without_country"] = (
    country_by_year["publications"]
    - country_by_year["publications_with_country"]
)


plt.figure(figsize=(10, 6))

plt.bar(
    country_by_year["publication_year"],
    country_by_year["publications_with_country"],
    label=f"With {COUNTRY_CODE} institution"
)

plt.bar(
    country_by_year["publication_year"],
    country_by_year["publications_without_country"],
    bottom=country_by_year["publications_with_country"],
    label=f"Without {COUNTRY_CODE} institution"
)

plt.xlabel("Publication year")
plt.ylabel("Number of publications")

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Publications with and without {COUNTRY_CODE} collaboration"
)

plt.legend()

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / f"{COUNTRY_CODE}_collaboration_stacked_bar.png",
    dpi=300
)

plt.close()

# ---------------------------------------------------------------------
# PLOT: PERCENTAGE OF OUTPUT WITH COUNTRY COLLABORATION
# ---------------------------------------------------------------------

country_by_year[
    "percentage_without_country"
] = (
    100
    - country_by_year[
        "percentage_with_country"
    ]
)


plt.figure(figsize=(10, 6))

plt.bar(
    country_by_year["publication_year"],
    country_by_year["percentage_with_country"],
    label=f"With {COUNTRY_CODE} institution"
)

plt.bar(
    country_by_year["publication_year"],
    country_by_year["percentage_without_country"],
    bottom=country_by_year["percentage_with_country"],
    label=f"Without {COUNTRY_CODE} institution"
)

plt.xlabel("Publication year")
plt.ylabel("Percentage of publications")

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Share of publications involving {COUNTRY_CODE} institutions"
)

plt.ylim(0, 100)

plt.legend()

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / f"{COUNTRY_CODE}_collaboration_percentage_stacked_bar.png",
    dpi=300
)

plt.close()


print("\nAnalysis complete.")