from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

GOK_PUBLICATIONS_FILE = Path(
    "../data/gok_publications.csv"
)

GREENLAND_PHYSICAL_SCIENCE_FILE = Path(
    "../data/greenland_physical_science.csv"
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
# LOAD DATA
# ---------------------------------------------------------------------

gok = pd.read_csv(
    GOK_PUBLICATIONS_FILE
)

greenland = pd.read_csv(
    GREENLAND_PHYSICAL_SCIENCE_FILE
)


print(
    f"Loaded {len(gok):,} GoK publications"
)

print(
    f"Loaded {len(greenland):,} Greenland physical-science publications"
)


# ---------------------------------------------------------------------
# FILTER YEARS
# ---------------------------------------------------------------------

gok = gok[
    gok["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()

greenland = greenland[
    greenland["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()


# ---------------------------------------------------------------------
# OPTIONAL: FILTER PUBLICATION TYPE
# ---------------------------------------------------------------------
#
# Keep this consistent between the two datasets.
#
# If the Greenland physical-science corpus contains only articles
# and reviews, you can leave this section as-is.
#
# If you want ONLY research articles, uncomment the relevant filter.
# ---------------------------------------------------------------------

gok = gok[
    gok["type"] == "article"
].copy()

greenland = greenland[
    greenland["type"] == "article"
].copy()


# ---------------------------------------------------------------------
# REMOVE DUPLICATE OPENALEX WORKS
# ---------------------------------------------------------------------
#
# A work should only count once in each corpus.
# ---------------------------------------------------------------------

gok = gok.drop_duplicates(
    subset="openalex_id"
).copy()

greenland = greenland.drop_duplicates(
    subset="openalex_id"
).copy()


# ---------------------------------------------------------------------
# IDENTIFY GOK CONTRIBUTIONS
# ---------------------------------------------------------------------
#
# A Greenland physical-science publication is considered to have a
# GoK contribution if its OpenAlex work ID occurs in the GoK corpus.
# ---------------------------------------------------------------------

gok_work_ids = set(
    gok["openalex_id"]
)


greenland[
    "gok_contribution"
] = (
    greenland["openalex_id"]
    .isin(gok_work_ids)
)


# ---------------------------------------------------------------------
# OVERLAPPING PUBLICATIONS
# ---------------------------------------------------------------------

gok_greenland = greenland[
    greenland["gok_contribution"]
].copy()


print(
    f"\nGreenland physical-science publications "
    f"with GoK contribution: "
    f"{len(gok_greenland):,}"
)


# ---------------------------------------------------------------------
# OVERALL CONTRIBUTION
# ---------------------------------------------------------------------

total_greenland_physical_science = len(
    greenland
)

total_gok_contributions = len(
    gok_greenland
)


if total_greenland_physical_science > 0:

    gok_percentage = (
        100
        * total_gok_contributions
        / total_greenland_physical_science
    )

else:

    gok_percentage = 0


print(
    "\n"
    + "=" * 70
)

print(
    "GOK CONTRIBUTION TO GREENLAND PHYSICAL SCIENCE"
)

print(
    "=" * 70
)

print(
    f"Total Greenland physical-science publications: "
    f"{total_greenland_physical_science:,}"
)

print(
    f"Publications with GoK contribution: "
    f"{total_gok_contributions:,}"
)

print(
    f"GoK contribution: "
    f"{gok_percentage:.2f}%"
)


# ---------------------------------------------------------------------
# SAVE PUBLICATION-LEVEL MATCH
# ---------------------------------------------------------------------
#
# This is particularly useful for checking the result manually.
# ---------------------------------------------------------------------

greenland.to_pickle(
    OUTPUT_DIR
    / "greenland_physical_science_with_gok_flag.pkl"
)

greenland.to_csv(
    OUTPUT_DIR
    / "greenland_physical_science_with_gok_flag.csv",
    index=False
)


# ---------------------------------------------------------------------
# SAVE ONLY OVERLAPPING PUBLICATIONS
# ---------------------------------------------------------------------

gok_greenland.to_pickle(
    OUTPUT_DIR
    / "gok_contributions_to_greenland_physical_science.pkl"
)

gok_greenland.to_csv(
    OUTPUT_DIR
    / "gok_contributions_to_greenland_physical_science.csv",
    index=False
)


# ---------------------------------------------------------------------
# YEARLY CONTRIBUTION
# ---------------------------------------------------------------------

greenland_by_year = (
    greenland
    .groupby(
        "publication_year"
    )
    .agg(
        greenland_physical_science=(
            "openalex_id",
            "nunique"
        ),

        gok_contributions=(
            "gok_contribution",
            "sum"
        ),
    )
    .reset_index()
)


greenland_by_year[
    "publications_without_gok"
] = (
    greenland_by_year[
        "greenland_physical_science"
    ]
    -
    greenland_by_year[
        "gok_contributions"
    ]
)


greenland_by_year[
    "gok_percentage"
] = (
    100
    *
    greenland_by_year[
        "gok_contributions"
    ]
    /
    greenland_by_year[
        "greenland_physical_science"
    ]
)


greenland_by_year.to_csv(
    OUTPUT_DIR
    / "gok_contribution_to_greenland_physical_science_by_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# PRINT YEARLY RESULTS
# ---------------------------------------------------------------------

print(
    "\nYearly contribution:"
)

print(
    greenland_by_year[
        [
            "publication_year",
            "greenland_physical_science",
            "gok_contributions",
            "gok_percentage",
        ]
    ].to_string(
        index=False,
        formatters={
            "gok_percentage": "{:.2f}%".format
        }
    )
)


# ---------------------------------------------------------------------
# PLOT: GOK SHARE OF GREENLAND PHYSICAL SCIENCE
# ---------------------------------------------------------------------

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    greenland_by_year[
        "publication_year"
    ],
    greenland_by_year[
        "gok_percentage"
    ],
    marker="o"
)

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "GoK contribution (% of Greenland physical-science publications)"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Contribution to Greenland physical-science publications"
)

plt.ylim(
    0,
    max(
        100,
        greenland_by_year[
            "gok_percentage"
        ].max() * 1.1
    )
)

plt.xticks(
    range(
        START_YEAR,
        END_YEAR + 1,
        2
    ),
    rotation=45
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "gok_contribution_to_greenland_physical_science.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# PLOT: ABSOLUTE NUMBERS
# ---------------------------------------------------------------------

plt.figure(
    figsize=(10, 6)
)

plt.bar(
    greenland_by_year[
        "publication_year"
    ],
    greenland_by_year[
        "gok_contributions"
    ],
    label="GoK contribution"
)

plt.bar(
    greenland_by_year[
        "publication_year"
    ],
    greenland_by_year[
        "publications_without_gok"
    ],
    bottom=greenland_by_year[
        "gok_contributions"
    ],
    label="No GoK contribution"
)

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Number of publications"
)

plt.title(
    "Greenland physical-science publications\n"
    "with and without GoK contribution"
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
    / "gok_contribution_to_greenland_physical_science_stacked.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------------

print(
    "\n"
    + "=" * 70
)

print(
    "Analysis complete."
)

print(
    f"Overall GoK contribution: "
    f"{gok_percentage:.2f}%"
)

print(
    f"Output saved to: "
    f"{OUTPUT_DIR}"
)

print(
    "=" * 70
)