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
# TARGET TOPIC
# ---------------------------------------------------------------------
#
# Change ONLY this value to analyse another topic.
#
# Examples:
#
# "Cryospheric studies and observations"
# "Geology and Paleoclimatology Research"
#
# Matching below is case-insensitive.
# ---------------------------------------------------------------------

TARGET_TOPIC = "Geology and Paleoclimatology Research"


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
# REMOVE DUPLICATE WORKS
# ---------------------------------------------------------------------

gok = gok.drop_duplicates(
    subset="openalex_id"
).copy()

greenland = greenland.drop_duplicates(
    subset="openalex_id"
).copy()


# ---------------------------------------------------------------------
# CHECK AVAILABLE PRIMARY TOPICS
# ---------------------------------------------------------------------
#
# primary_topic is already a plain text column in your CSV.
# No parsing is required.
# ---------------------------------------------------------------------

available_topics = (
    greenland[
        "primary_topic"
    ]
    .dropna()
    .astype(str)
    .value_counts()
)


print(
    "\nTop primary topics in the Greenland "
    "physical-science corpus:"
)

print(
    available_topics.head(20).to_string()
)


# ---------------------------------------------------------------------
# FILTER TO TARGET TOPIC
# ---------------------------------------------------------------------
#
# Case-insensitive matching.
# ---------------------------------------------------------------------

greenland_topic = greenland[
    greenland[
        "primary_topic"
    ]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
    ==
    TARGET_TOPIC.strip().casefold()
].copy()


print(
    "\n"
    + "=" * 70
)

print(
    f"TARGET TOPIC: {TARGET_TOPIC}"
)

print(
    "=" * 70
)

print(
    f"Publications in target topic: "
    f"{len(greenland_topic):,}"
)


# ---------------------------------------------------------------------
# STOP IF NO PUBLICATIONS WERE FOUND
# ---------------------------------------------------------------------

if len(greenland_topic) == 0:

    print(
        "\nNo publications were found for this topic."
    )

    print(
        "\nPlease check the spelling against the "
        "list of available primary topics printed above."
    )

    raise SystemExit


# ---------------------------------------------------------------------
# IDENTIFY GOK CONTRIBUTIONS
# ---------------------------------------------------------------------
#
# A publication is considered to have a GoK contribution if its
# OpenAlex work ID occurs in the GoK publication corpus.
# ---------------------------------------------------------------------

gok_work_ids = set(
    gok["openalex_id"]
)


greenland_topic[
    "gok_contribution"
] = (
    greenland_topic[
        "openalex_id"
    ]
    .isin(gok_work_ids)
)


# ---------------------------------------------------------------------
# COUNT OVERALL CONTRIBUTION
# ---------------------------------------------------------------------

total_topic_publications = len(
    greenland_topic
)

topic_gok_contributions = int(
    greenland_topic[
        "gok_contribution"
    ].sum()
)


if total_topic_publications > 0:

    topic_gok_percentage = (
        100
        * topic_gok_contributions
        / total_topic_publications
    )

else:

    topic_gok_percentage = 0


print(
    f"\nPublications with GoK contribution: "
    f"{topic_gok_contributions:,}"
)

print(
    f"GoK contribution: "
    f"{topic_gok_percentage:.2f}%"
)


# ---------------------------------------------------------------------
# SAFE TOPIC NAME FOR OUTPUT FILES
# ---------------------------------------------------------------------

safe_topic_name = (
    TARGET_TOPIC
    .lower()
    .replace(" ", "_")
    .replace("/", "_")
    .replace("\\", "_")
)


# ---------------------------------------------------------------------
# SAVE ALL PUBLICATIONS IN THIS TOPIC
# ---------------------------------------------------------------------

greenland_topic.to_pickle(
    OUTPUT_DIR
    / f"{safe_topic_name}_with_gok_flag.pkl"
)

greenland_topic.to_csv(
    OUTPUT_DIR
    / f"{safe_topic_name}_with_gok_flag.csv",
    index=False
)


# ---------------------------------------------------------------------
# SAVE ONLY GOK CONTRIBUTIONS
# ---------------------------------------------------------------------

gok_topic = greenland_topic[
    greenland_topic[
        "gok_contribution"
    ]
].copy()


gok_topic.to_pickle(
    OUTPUT_DIR
    / f"gok_contributions_{safe_topic_name}.pkl"
)

gok_topic.to_csv(
    OUTPUT_DIR
    / f"gok_contributions_{safe_topic_name}.csv",
    index=False
)


# ---------------------------------------------------------------------
# YEARLY STATISTICS
# ---------------------------------------------------------------------

topic_by_year = (
    greenland_topic
    .groupby(
        "publication_year"
    )
    .agg(
        topic_publications=(
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


topic_by_year[
    "publications_without_gok"
] = (
    topic_by_year[
        "topic_publications"
    ]
    -
    topic_by_year[
        "gok_contributions"
    ]
)


topic_by_year[
    "gok_percentage"
] = (
    100
    *
    topic_by_year[
        "gok_contributions"
    ]
    /
    topic_by_year[
        "topic_publications"
    ]
)


# ---------------------------------------------------------------------
# SAVE YEARLY STATISTICS
# ---------------------------------------------------------------------

topic_by_year.to_csv(
    OUTPUT_DIR
    / f"gok_contribution_{safe_topic_name}_by_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# PRINT YEARLY RESULTS
# ---------------------------------------------------------------------

print(
    "\nYearly contribution:"
)

print(
    topic_by_year[
        [
            "publication_year",
            "topic_publications",
            "gok_contributions",
            "gok_percentage",
        ]
    ].to_string(
        index=False,
        formatters={
            "gok_percentage":
                "{:.2f}%".format
        }
    )
)


# ---------------------------------------------------------------------
# PLOT: GOK PERCENTAGE BY YEAR
# ---------------------------------------------------------------------

plt.figure(
    figsize=(10, 6)
)

plt.plot(
    topic_by_year[
        "publication_year"
    ],
    topic_by_year[
        "gok_percentage"
    ],
    marker="o"
)

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "GoK contribution (% of topic publications)"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Contribution to {TARGET_TOPIC}"
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

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / f"gok_contribution_{safe_topic_name}_percentage.png",
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
    topic_by_year[
        "publication_year"
    ],
    topic_by_year[
        "gok_contributions"
    ],
    label="GoK contribution"
)

plt.bar(
    topic_by_year[
        "publication_year"
    ],
    topic_by_year[
        "publications_without_gok"
    ],
    bottom=topic_by_year[
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
    f"{TARGET_TOPIC}\n"
    "Publications with and without GoK contribution"
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
    / f"gok_contribution_{safe_topic_name}_stacked.png",
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
    f"Topic: {TARGET_TOPIC}"
)

print(
    f"Total topic publications: "
    f"{total_topic_publications:,}"
)

print(
    f"GoK contributions: "
    f"{topic_gok_contributions:,}"
)

print(
    f"GoK contribution: "
    f"{topic_gok_percentage:.2f}%"
)

print(
    "=" * 70
)