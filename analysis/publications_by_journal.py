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

OUTPUT_DIR = Path("../output")
FIGURE_DIR = OUTPUT_DIR / "figures"

OUTPUT_DIR.mkdir(exist_ok=True)
FIGURE_DIR.mkdir(exist_ok=True)

START_YEAR = 2000
END_YEAR = 2025

TOP_N_JOURNALS = 10
TOP_N_TRENDS = 10


# ---------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------

pubs = pd.read_csv(
    PUBLICATIONS_FILE
)

print(
    f"Loaded {len(pubs)} publications"
)


# ---------------------------------------------------------------------
# FILTER YEARS
# ---------------------------------------------------------------------

pubs = pubs[
    pubs["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()


# ---------------------------------------------------------------------
# FILTER PUBLICATION TYPE
# ---------------------------------------------------------------------

pubs = pubs[
    pubs["type"] == "article"
].copy()


print(
    f"Publications after filtering: "
    f"{len(pubs)}"
)


# ---------------------------------------------------------------------
# HELPER FUNCTION
# ---------------------------------------------------------------------

def parse_nested_dict(value):
    """
    Convert a CSV representation of a Python dictionary back into
    a dictionary.

    Returns None if the value cannot be parsed.
    """

    if pd.isna(value):
        return None

    if isinstance(value, dict):
        return value

    try:
        parsed = ast.literal_eval(value)
    except (
        ValueError,
        SyntaxError
    ):
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


# ---------------------------------------------------------------------
# EXTRACT JOURNAL
# ---------------------------------------------------------------------

def get_journal(location):

    location = parse_nested_dict(
        location
    )

    if not isinstance(
        location,
        dict
    ):
        return None

    source = location.get(
        "source"
    )

    if not isinstance(
        source,
        dict
    ):
        return None

    return source.get(
        "display_name"
    )


pubs["journal"] = (
    pubs["primary_location"]
    .apply(get_journal)
)


# ---------------------------------------------------------------------
# REPORT MISSING JOURNALS
# ---------------------------------------------------------------------

missing_journals = pubs[
    pubs["journal"].isna()
].copy()


print(
    f"Publications with journal information: "
    f"{len(pubs) - len(missing_journals)}"
)

print(
    f"Publications without journal information: "
    f"{len(missing_journals)}"
)


if len(missing_journals) > 0:

    missing_journals[
        [
            "openalex_id",
            "publication_year",
            "title",
        ]
    ].to_csv(
        OUTPUT_DIR
        / "publications_without_journal.csv",
        index=False
    )


# ---------------------------------------------------------------------
# KEEP ONLY PUBLICATIONS WITH JOURNAL INFORMATION
# ---------------------------------------------------------------------

pubs_with_journal = pubs[
    pubs["journal"].notna()
].copy()


print(
    f"Publications retained for journal analysis: "
    f"{len(pubs_with_journal)}"
)


# ---------------------------------------------------------------------
# SAVE PUBLICATION-LEVEL JOURNAL DATA
# ---------------------------------------------------------------------

pubs_with_journal[
    [
        "openalex_id",
        "publication_year",
        "title",
        "journal",
    ]
].to_csv(
    OUTPUT_DIR
    / "publication_journals.csv",
    index=False
)


# =====================================================================
# JOURNAL STATISTICS
# =====================================================================


total_publications = (
    len(pubs_with_journal)
)


total_journals = (
    pubs_with_journal[
        "journal"
    ].nunique()
)


# ---------------------------------------------------------------------
# 1. PUBLICATIONS BY JOURNAL
# ---------------------------------------------------------------------

journal_summary = (
    pubs_with_journal
    .groupby(
        "journal"
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        ),

        citations=(
            "cited_by_count",
            "sum"
        ),

        mean_citations=(
            "cited_by_count",
            "mean"
        ),
    )
    .reset_index()
    .sort_values(
        "publications",
        ascending=False
    )
)


journal_summary[
    "percentage_of_publications"
] = (
    100
    *
    journal_summary[
        "publications"
    ]
    /
    total_publications
)


journal_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_journal.csv",
    index=False
)


# ---------------------------------------------------------------------
# 2. JOURNALS BY YEAR
# ---------------------------------------------------------------------

journals_by_year = (
    pubs_with_journal
    .groupby(
        [
            "publication_year",
            "journal",
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


journals_by_year.to_csv(
    OUTPUT_DIR
    / "publications_by_journal_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# 3. JOURNAL SUMMARY BY YEAR
# ---------------------------------------------------------------------

journal_year_matrix = (
    journals_by_year
    .pivot_table(
        index="publication_year",
        columns="journal",
        values="publications",
        aggfunc="sum",
        fill_value=0
    )
)


all_years = pd.Index(
    range(
        START_YEAR,
        END_YEAR + 1
    ),
    name="publication_year"
)


journal_year_matrix = (
    journal_year_matrix
    .reindex(
        all_years,
        fill_value=0
    )
)


journal_year_matrix.to_csv(
    OUTPUT_DIR
    / "journal_publication_matrix.csv"
)


# =====================================================================
# FIGURES
# =====================================================================


# ---------------------------------------------------------------------
# FIGURE 1: TOP JOURNALS
# ---------------------------------------------------------------------

top_journals = (
    journal_summary
    .head(TOP_N_JOURNALS)
    .sort_values(
        "publications"
    )
)


plt.figure(
    figsize=(10, 8)
)

plt.barh(
    top_journals["journal"],
    top_journals["publications"]
)

plt.xlabel(
    "Number of publications"
)

plt.ylabel(
    "Journal"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Top {TOP_N_JOURNALS} publication journals"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "top_journals.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 2: TOP 2 JOURNALS + OTHER THROUGH TIME
# ---------------------------------------------------------------------

top_journal_names = (
    journal_summary
    .head(TOP_N_TRENDS)[
        "journal"
    ]
    .tolist()
)


top_journals_year = (
    journals_by_year[
        journals_by_year[
            "journal"
        ].isin(
            top_journal_names
        )
    ]
    .pivot_table(
        index="publication_year",
        columns="journal",
        values="publications",
        aggfunc="sum",
        fill_value=0
    )
)


top_journals_year = (
    top_journals_year
    .reindex(
        all_years,
        fill_value=0
    )
)


# Make sure journals appear in overall ranking order

top_journals_year = (
    top_journals_year
    .reindex(
        columns=top_journal_names,
        fill_value=0
    )
)


# ---------------------------------------------------------------------
# CALCULATE OTHER JOURNALS
# ---------------------------------------------------------------------

total_by_year = (
    pubs_with_journal
    .groupby(
        "publication_year"
    )[
        "openalex_id"
    ]
    .nunique()
    .reindex(
        all_years,
        fill_value=0
    )
)


top_two_by_year = (
    top_journals_year
    .sum(
        axis=1
    )
)


top_journals_year["Other journals"] = (
    total_by_year
    - top_two_by_year
)


# ---------------------------------------------------------------------
# STACKED BAR CHART
# ---------------------------------------------------------------------

ax = top_journals_year.plot(
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
    "Publication journals through time"
)


ax.legend(
    bbox_to_anchor=(1.02, 1),
    loc="upper left",
    title="Journal"
)


plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "journal_trends_top2.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 3: JOURNAL DIVERSITY THROUGH TIME
# ---------------------------------------------------------------------

journals_per_year = (
    pubs_with_journal
    .groupby(
        "publication_year"
    )[
        "journal"
    ]
    .nunique()
    .reindex(
        all_years,
        fill_value=0
    )
)


plt.figure(
    figsize=(12, 6)
)

plt.bar(
    journals_per_year.index,
    journals_per_year.values
)

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Number of unique journals"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Number of publication journals per year"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "journals_per_year.png",
    dpi=300
)

plt.close()


# =====================================================================
# SUMMARY
# =====================================================================

print("\n")
print("=" * 70)
print("PUBLICATION JOURNAL ANALYSIS")
print("=" * 70)

print(
    f"Total publications: "
    f"{total_publications}"
)

print(
    f"Unique journals: "
    f"{total_journals}"
)

print(
    f"Publications without journal: "
    f"{len(missing_journals)}"
)


print("\nTop journals:")

print(
    journal_summary[
        [
            "journal",
            "publications",
            "percentage_of_publications",
            "citations",
            "mean_citations",
        ]
    ]
    .head(TOP_N_JOURNALS)
    .to_string(
        index=False
    )
)


print("\nAnalysis complete.")