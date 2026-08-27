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

START_YEAR = 2000
END_YEAR = 2025


# ---------------------------------------------------------------------
# DEFINITION OF GREENLANDIC AFFILIATION
# ---------------------------------------------------------------------
#
# OpenAlex assigns institutions a country code.
#
# Greenland = GL
#
# We therefore identify a Greenlandic affiliation when at least one
# institution in an authorship has country_code == "GL".
#
# ---------------------------------------------------------------------

GREENLAND_COUNTRY_CODE = "GL"

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


def get_greenland_institutions(value):
    """
    Return structured institution records whose country_code
    is Greenland (GL).
    """
    institutions = parse_institutions(
        value
    )

    greenland_institutions = []

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

        if country_code == GREENLAND_COUNTRY_CODE:

            greenland_institutions.append(
                institution
            )

    return greenland_institutions


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
# IDENTIFY GREENLANDIC AFFILIATIONS
# ---------------------------------------------------------------------

authors[
    "greenland_institutions"
] = (
    authors["institutions"]
    .apply(
        get_greenland_institutions
    )
)


authors[
    "has_greenland_affiliation"
] = (
    authors[
        "greenland_institutions"
    ]
    .apply(
        lambda x: len(x) > 0
    )
)


authors[
    "greenland_institution_names"
] = (
    authors[
        "greenland_institutions"
    ]
    .apply(
        institution_names
    )
)


authors[
    "greenland_institution_ids"
] = (
    authors[
        "greenland_institutions"
    ]
    .apply(
        institution_ids
    )
)


# ---------------------------------------------------------------------
# DEFINE GREENLANDIC CO-AUTHOR
# ---------------------------------------------------------------------
# A Greenlandic co-author is an author on a GoK publication who has
# a Greenlandic institutional affiliation.
#
# We exclude the GoK+GEUS authors from this definition, because the
# purpose here is to measure collaboration between GoK and institutions
# in Greenland.
# ---------------------------------------------------------------------

if "is_gok_geus_author" in authors.columns:

    authors[
        "is_greenland_coauthor"
    ] = (
        authors[
            "has_greenland_affiliation"
        ]
        &
        ~authors[
            "is_gok_geus_author"
        ].fillna(False)
    )

else:

    # Fallback if the column does not exist.
    authors[
        "is_greenland_coauthor"
    ] = authors[
        "has_greenland_affiliation"
    ]


# ---------------------------------------------------------------------
# SAVE AUTHOR-LEVEL GREENLAND INFORMATION
# ---------------------------------------------------------------------

authors.to_pickle(
    OUTPUT_DIR
    / "gok_authors_greenland.pkl"
)

authors.to_csv(
    OUTPUT_DIR
    / "gok_authors_greenland.csv",
    index=False
)


# ---------------------------------------------------------------------
# PUBLICATION-LEVEL GREENLAND INFORMATION
# ---------------------------------------------------------------------

greenland_author_records = (
    authors[
        authors[
            "is_greenland_coauthor"
        ]
    ]
    .copy()
)


# Unique publications with at least one Greenlandic co-author
greenland_work_ids = set(
    greenland_author_records[
        "openalex_work_id"
    ]
)


pubs[
    "has_greenland_coauthor"
] = (
    pubs["openalex_id"]
    .isin(greenland_work_ids)
)


# ---------------------------------------------------------------------
# COUNT GREENLANDIC AUTHORS PER PUBLICATION
# ---------------------------------------------------------------------

greenland_counts = (
    greenland_author_records
    .groupby(
        "openalex_work_id"
    )
    .agg(
        greenland_coauthors=(
            "author_id",
            "nunique"
        )
    )
    .reset_index()
)


pubs = pubs.merge(
    greenland_counts,
    left_on="openalex_id",
    right_on="openalex_work_id",
    how="left"
)


pubs[
    "greenland_coauthors"
] = (
    pubs[
        "greenland_coauthors"
    ]
    .fillna(0)
    .astype(int)
)


# ---------------------------------------------------------------------
# GREENLANDIC INSTITUTIONS PER PUBLICATION
# ---------------------------------------------------------------------

greenland_institution_rows = []

for _, row in greenland_author_records.iterrows():

    work_id = row[
        "openalex_work_id"
    ]

    institutions = row[
        "greenland_institutions"
    ]

    for institution in institutions:

        greenland_institution_rows.append({

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

greenland_institution_authors = (
    pd.DataFrame(
        greenland_institution_rows
    )
)


# ---------------------------------------------------------------------
# UNIQUE GREENLANDIC INSTITUTIONS PER PAPER
# ---------------------------------------------------------------------

if len(
    greenland_institution_authors
) > 0:

    institution_per_work = (
        greenland_institution_authors
        .groupby(
            "openalex_work_id"
        )
        .agg(
            greenland_institutions=(
                "institution_name",
                lambda x:
                    "; ".join(
                        sorted(
                            set(x)
                        )
                    )
            ),
            greenland_institution_count=(
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
            "greenland_institutions",
            "greenland_institution_count",
        ]
    )


pubs = pubs.merge(
    institution_per_work,
    left_on="openalex_id",
    right_on="openalex_work_id",
    how="left"
)


pubs[
    "greenland_institution_count"
] = (
    pubs[
        "greenland_institution_count"
    ]
    .fillna(0)
    .astype(int)
)


pubs[
    "greenland_institutions"
] = (
    pubs[
        "greenland_institutions"
    ]
    .fillna("")
)


# ---------------------------------------------------------------------
# SAVE PUBLICATION-LEVEL DATA
# ---------------------------------------------------------------------

pubs.to_pickle(
    OUTPUT_DIR
    / "gok_publications_greenland.pkl"
)

pubs.to_csv(
    OUTPUT_DIR
    / "gok_publications_greenland.csv",
    index=False
)

# ---------------------------------------------------------------------
# STATISTICS: PUBLICATIONS WITH GREENLAND COLLABORATION
# ---------------------------------------------------------------------

greenland_by_year = (
    pubs
    .groupby(
        "publication_year"
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        ),

        publications_with_greenland=(
            "has_greenland_coauthor",
            "sum"
        ),
    )
    .reset_index()
)

greenland_by_year[
    "percentage_with_greenland"
] = (
    100
    *
    greenland_by_year[
        "publications_with_greenland"
    ]
    /
    greenland_by_year[
        "publications"
    ]
)

greenland_by_year.to_csv(
    OUTPUT_DIR
    / "greenland_collaboration_by_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# STATISTICS: GREENLANDIC INSTITUTIONS
# ---------------------------------------------------------------------

if len(
    greenland_institution_authors
) > 0:

    institution_summary = (
        greenland_institution_authors
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
    / "greenland_institutions.csv",
    index=False
)


# ---------------------------------------------------------------------
# INSTITUTION × YEAR
# ---------------------------------------------------------------------

if len(
    greenland_institution_authors
) > 0:

    # Add publication year
    institution_year = (
        greenland_institution_authors
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
    / "greenland_institutions_by_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# GREENLANDIC AUTHORS
# ---------------------------------------------------------------------

if len(
    greenland_author_records
) > 0:

    greenland_authors_summary = (
        greenland_author_records
        .groupby(
            [
                "author_id",
                "author_name",
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

    greenland_authors_summary = pd.DataFrame(
        columns=[
            "author_id",
            "author_name",
            "publications",
        ]
    )


greenland_authors_summary.to_csv(
    OUTPUT_DIR
    / "greenland_coauthors.csv",
    index=False
)


# ---------------------------------------------------------------------
# SUMMARY STATISTICS
# ---------------------------------------------------------------------

total_publications = len(pubs)

greenland_publications = int(
    pubs[
        "has_greenland_coauthor"
    ].sum()
)


if total_publications > 0:

    greenland_percentage = (
        100
        *
        greenland_publications
        /
        total_publications
    )

else:

    greenland_percentage = 0


print("\n")
print("=" * 70)
print("GREENLAND COLLABORATION ANALYSIS")
print("=" * 70)

print(
    f"Total GoK publications: "
    f"{total_publications}"
)

print(
    f"Publications with Greenlandic "
    f"co-author: "
    f"{greenland_publications}"
)

print(
    f"Percentage with Greenlandic "
    f"collaboration: "
    f"{greenland_percentage:.1f}%"
)

print(
    f"Unique Greenlandic institutions: "
    f"{len(institution_summary)}"
)

print(
    f"Unique Greenlandic co-authors: "
    f"{len(greenland_authors_summary)}"
)


if len(
    institution_summary
) > 0:

    print("\nTop Greenlandic institutions:")

    print(
        institution_summary
        .head(10)
        .to_string(
            index=False
        )
    )


# ---------------------------------------------------------------------
# PLOT: PUBLICATIONS PER YEAR — GREENLAND VS NO GREENLAND
# ---------------------------------------------------------------------

greenland_by_year["publications_without_greenland"] = (
    greenland_by_year["publications"]
    - greenland_by_year["publications_with_greenland"]
)


plt.figure(figsize=(10, 6))

plt.bar(
    greenland_by_year["publication_year"],
    greenland_by_year["publications_with_greenland"],
    label="With Greenlandic institution"
)

plt.bar(
    greenland_by_year["publication_year"],
    greenland_by_year["publications_without_greenland"],
    bottom=greenland_by_year["publications_with_greenland"],
    label="Without Greenlandic institution"
)

plt.xlabel("Publication year")
plt.ylabel("Number of publications")

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Publications with and without Greenlandic collaboration"
)

plt.legend()

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "greenland_collaboration_stacked_bar.png",
    dpi=300
)

plt.close()

# ---------------------------------------------------------------------
# PLOT: PERCENTAGE OF OUTPUT WITH GREENLAND COLLABORATION
# ---------------------------------------------------------------------

greenland_by_year[
    "percentage_without_greenland"
] = (
    100
    - greenland_by_year[
        "percentage_with_greenland"
    ]
)


plt.figure(figsize=(10, 6))

plt.bar(
    greenland_by_year["publication_year"],
    greenland_by_year["percentage_with_greenland"],
    label="With Greenlandic institution"
)

plt.bar(
    greenland_by_year["publication_year"],
    greenland_by_year["percentage_without_greenland"],
    bottom=greenland_by_year["percentage_with_greenland"],
    label="Without Greenlandic institution"
)

plt.xlabel("Publication year")
plt.ylabel("Percentage of publications")

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Share of publications involving Greenlandic institutions"
)

plt.ylim(0, 100)

plt.legend()

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "greenland_collaboration_percentage_stacked_bar.png",
    dpi=300
)

plt.close()


print("\nAnalysis complete.")