# 08_publication_collaborators.py

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

OUTPUT_DIR.mkdir(exist_ok=True)
FIGURE_DIR.mkdir(exist_ok=True)


START_YEAR = 2000
END_YEAR = 2025

TOP_N_COUNTRIES = 20
TOP_N_INSTITUTIONS = 10


# ---------------------------------------------------------------------
# GEUS IDENTIFICATION
# ---------------------------------------------------------------------

# We exclude GEUS institutions from the collaborator analysis.

GEUS_INSTITUTION_ID = (
    "https://openalex.org/I2801979204"
)


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
# FILTER PUBLICATIONS
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
    f"Publications after filtering: "
    f"{len(pubs)}"
)


# ---------------------------------------------------------------------
# PARSE INSTITUTIONS
# ---------------------------------------------------------------------

def parse_institutions(value):

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


authors["institutions_parsed"] = (
    authors["institutions"]
    .apply(parse_institutions)
)


# ---------------------------------------------------------------------
# MERGE PUBLICATION INFORMATION
# ---------------------------------------------------------------------

authors = authors.merge(
    pubs[
        [
            "openalex_id",
            "publication_year",
            "title",
        ]
    ],
    left_on="openalex_work_id",
    right_on="openalex_id",
    how="inner"
)


print(
    f"Author records belonging to selected publications: "
    f"{len(authors)}"
)


# =====================================================================
# EXTRACT EXTERNAL COLLABORATIONS
# =====================================================================

country_rows = []
institution_rows = []


for work_id, work_authors in authors.groupby(
    "openalex_work_id"
):

    publication_year = (
        work_authors[
            "publication_year"
        ].iloc[0]
    )


    # ---------------------------------------------------------------
    # Sets ensure that each country/institution is counted only once
    # per publication.
    # ---------------------------------------------------------------

    publication_countries = set()
    publication_institutions = set()


    # ---------------------------------------------------------------
    # LOOP THROUGH AUTHORS
    # ---------------------------------------------------------------

    for _, author_row in work_authors.iterrows():

        institutions = (
            author_row[
                "institutions_parsed"
            ]
        )


        for institution in institutions:

            if not isinstance(
                institution,
                dict
            ):
                continue


            institution_id = (
                institution.get("id")
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


            # -------------------------------------------------------
            # EXCLUDE GEUS
            # -------------------------------------------------------

            if institution_id == GEUS_INSTITUTION_ID:

                continue


            # -------------------------------------------------------
            # INSTITUTION
            # -------------------------------------------------------

            if institution_id:

                publication_institutions.add(
                    (
                        institution_id,
                        institution_name,
                        country_code
                    )
                )


            # -------------------------------------------------------
            # COUNTRY
            # -------------------------------------------------------

            if country_code:

                publication_countries.add(
                    country_code
                )


    # ---------------------------------------------------------------
    # SAVE COUNTRY RECORDS
    # ---------------------------------------------------------------

    for country in publication_countries:

        country_rows.append({

            "openalex_work_id":
                work_id,

            "publication_year":
                publication_year,

            "country_code":
                country,

        })


    # ---------------------------------------------------------------
    # SAVE INSTITUTION RECORDS
    # ---------------------------------------------------------------

    for (
        institution_id,
        institution_name,
        country_code
    ) in publication_institutions:

        institution_rows.append({

            "openalex_work_id":
                work_id,

            "publication_year":
                publication_year,

            "institution_id":
                institution_id,

            "institution":
                institution_name,

            "country_code":
                country_code,

        })


countries = pd.DataFrame(
    country_rows
)

institutions = pd.DataFrame(
    institution_rows
)


# ---------------------------------------------------------------------
# SAVE COLLABORATION DATA
# ---------------------------------------------------------------------

countries.to_csv(
    OUTPUT_DIR
    / "publication_collaborator_countries.csv",
    index=False
)

institutions.to_csv(
    OUTPUT_DIR
    / "publication_collaborator_institutions.csv",
    index=False
)


print(
    f"External country-publication records: "
    f"{len(countries)}"
)

print(
    f"External institution-publication records: "
    f"{len(institutions)}"
)


# =====================================================================
# COUNTRY ANALYSIS
# =====================================================================

# ---------------------------------------------------------------------
# TOTAL PUBLICATIONS BY COUNTRY
# ---------------------------------------------------------------------

country_summary = (
    countries
    .groupby(
        "country_code"
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


total_publications = (
    pubs["openalex_id"]
    .nunique()
)


country_summary[
    "percentage_of_publications"
] = (
    100
    *
    country_summary[
        "publications"
    ]
    /
    total_publications
)


country_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_collaborator_country.csv",
    index=False
)


# ---------------------------------------------------------------------
# COUNTRIES BY YEAR
# ---------------------------------------------------------------------

countries_by_year = (
    countries
    .groupby(
        [
            "publication_year",
            "country_code",
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


countries_by_year.to_csv(
    OUTPUT_DIR
    / "publications_by_collaborator_country_year.csv",
    index=False
)


# =====================================================================
# INSTITUTION ANALYSIS
# =====================================================================

# ---------------------------------------------------------------------
# TOTAL PUBLICATIONS BY INSTITUTION
# ---------------------------------------------------------------------

institution_summary = (
    institutions
    .groupby(
        [
            "institution_id",
            "institution",
            "country_code",
        ],
        dropna=False
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


institution_summary[
    "percentage_of_publications"
] = (
    100
    *
    institution_summary[
        "publications"
    ]
    /
    total_publications
)


institution_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_collaborator_institution.csv",
    index=False
)


# ---------------------------------------------------------------------
# INSTITUTIONS BY YEAR
# ---------------------------------------------------------------------

institutions_by_year = (
    institutions
    .groupby(
        [
            "publication_year",
            "institution_id",
            "institution",
            "country_code",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_work_id",
            "nunique"
        )
    )
    .reset_index()
)


institutions_by_year.to_csv(
    OUTPUT_DIR
    / "publications_by_collaborator_institution_year.csv",
    index=False
)


# =====================================================================
# COLLABORATION INTENSITY
# =====================================================================

# Number of external collaborator countries per publication

countries_per_publication = (
    countries
    .groupby(
        "openalex_work_id"
    )[
        "country_code"
    ]
    .nunique()
)


# Number of external collaborator institutions per publication

institutions_per_publication = (
    institutions
    .groupby(
        "openalex_work_id"
    )[
        "institution_id"
    ]
    .nunique()
)


collaboration_summary = pd.DataFrame({

    "external_countries":
        countries_per_publication,

    "external_institutions":
        institutions_per_publication,

})


collaboration_summary = (
    collaboration_summary
    .reset_index()
)


collaboration_summary.to_csv(
    OUTPUT_DIR
    / "publication_collaboration_intensity.csv",
    index=False
)


# =====================================================================
# FIGURES
# =====================================================================

# ---------------------------------------------------------------------
# FIGURE 1: TOP COLLABORATOR COUNTRIES
# ---------------------------------------------------------------------

top_countries = (
    country_summary
    .head(TOP_N_COUNTRIES)
    .sort_values(
        "publications"
    )
)


plt.figure(
    figsize=(10, 8)
)

plt.barh(
    top_countries["country_code"],
    top_countries["publications"]
)

plt.xlabel(
    "Number of publications"
)

plt.ylabel(
    "Country"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Top {TOP_N_COUNTRIES} external collaborator countries"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "top_collaborator_countries.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 2: TOP COLLABORATING INSTITUTIONS
# ---------------------------------------------------------------------

top_institutions = (
    institution_summary
    .head(TOP_N_INSTITUTIONS)
    .sort_values(
        "publications"
    )
)


plt.figure(
    figsize=(11, 8)
)

plt.barh(
    top_institutions["institution"],
    top_institutions["publications"]
)

plt.xlabel(
    "Number of publications"
)

plt.ylabel(
    "Institution"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Top {TOP_N_INSTITUTIONS} external collaborating institutions"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "top_collaborating_institutions.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 3: COLLABORATOR COUNTRIES THROUGH TIME
# ---------------------------------------------------------------------

top_country_names = (
    country_summary
    .head(TOP_N_COUNTRIES)[
        "country_code"
    ]
    .tolist()
)


country_trends = (
    countries_by_year[
        countries_by_year[
            "country_code"
        ].isin(
            top_country_names
        )
    ]
    .pivot_table(
        index="publication_year",
        columns="country_code",
        values="publications",
        aggfunc="sum",
        fill_value=0
    )
    .reindex(
        range(
            START_YEAR,
            END_YEAR + 1
        ),
        fill_value=0
    )
)


plt.figure(
    figsize=(12, 8)
)

for country in country_trends.columns:

    plt.plot(
        country_trends.index,
        country_trends[country],
        marker="o",
        label=country
    )


plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Number of publications"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "External collaborator countries through time"
)

plt.legend(
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "collaborator_countries_through_time.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 4: TOP 2 COLLABORATING INSTITUTIONS + OTHER
# ---------------------------------------------------------------------

TOP_N_INSTITUTION_TRENDS = 2


top_institution_names = (
    institution_summary
    .head(
        TOP_N_INSTITUTION_TRENDS
    )[
        "institution"
    ]
    .tolist()
)


institution_trends = (
    institutions_by_year[
        institutions_by_year[
            "institution"
        ].isin(
            top_institution_names
        )
    ]
    .pivot_table(
        index="publication_year",
        columns="institution",
        values="publications",
        aggfunc="sum",
        fill_value=0
    )
    .reindex(
        range(
            START_YEAR,
            END_YEAR + 1
        ),
        fill_value=0
    )
)


institution_trends = (
    institution_trends
    .reindex(
        columns=top_institution_names,
        fill_value=0
    )
)


# Total publications involving at least one
# external institution

total_collaborative_by_year = (
    institutions
    .groupby(
        "publication_year"
    )[
        "openalex_work_id"
    ]
    .nunique()
    .reindex(
        range(
            START_YEAR,
            END_YEAR + 1
        ),
        fill_value=0
    )
)


top_two_by_year = (
    institution_trends
    .sum(
        axis=1
    )
)


institution_trends[
    "Other institutions"
] = (
    total_collaborative_by_year
    - top_two_by_year
)


# ---------------------------------------------------------------------
# STACKED BAR CHART
# ---------------------------------------------------------------------

ax = institution_trends.plot(
    kind="bar",
    stacked=True,
    figsize=(12, 7)
)


ax.set_xlabel(
    "Publication year"
)

ax.set_ylabel(
    "Number of publications"
)

ax.set_title(
    "GEUS Department of Glaciology and Climate\n"
    "External collaborating institutions through time"
)


ax.legend(
    bbox_to_anchor=(1.02, 1),
    loc="upper left",
    title="Institution"
)


plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "collaborating_institutions_top2.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =====================================================================
# SUMMARY
# =====================================================================

print("\n")
print("=" * 70)
print("COLLABORATION ANALYSIS")
print("=" * 70)

print(
    f"Total publications: "
    f"{total_publications}"
)

print(
    f"External collaborator countries: "
    f"{country_summary['country_code'].nunique()}"
)

print(
    f"External collaborating institutions: "
    f"{institution_summary['institution_id'].nunique()}"
)


print("\nTop collaborator countries:")

print(
    country_summary
    .head(TOP_N_COUNTRIES)
    .to_string(
        index=False
    )
)


print("\nTop collaborating institutions:")

print(
    institution_summary[
        [
            "institution",
            "country_code",
            "publications",
            "percentage_of_publications",
        ]
    ]
    .head(TOP_N_INSTITUTIONS)
    .to_string(
        index=False
    )
)


print("\nAnalysis complete.")