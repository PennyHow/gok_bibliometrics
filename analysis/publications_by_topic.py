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

START_YEAR = 2010
END_YEAR = 2025

TOP_N_TOPICS = 20


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

def parse_topics(value):
    """
    Convert the topics column from a CSV string back into
    a Python list of dictionaries.
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


# ---------------------------------------------------------------------
# IDENTIFY PRIMARY TOPIC FOR EACH PUBLICATION
# ---------------------------------------------------------------------
#
# Each OpenAlex publication can have multiple topics.
# We therefore select the topic with the highest OpenAlex score.
# So: ONE publication -> ONE primary topic
#
# ---------------------------------------------------------------------

primary_topic_rows = []

no_topic_count = 0


for _, row in pubs.iterrows():

    topics = parse_topics(
        row["topics"]
    )

    valid_topics = []

    for topic in topics:

        if not isinstance(
            topic,
            dict
        ):
            continue

        topic_name = topic.get(
            "display_name"
        )

        if not topic_name:
            continue

        score = topic.get(
            "score"
        )

        # Make sure score is numeric
        try:
            score = float(score)
        except (
            TypeError,
            ValueError
        ):
            continue

        valid_topics.append(
            (
                score,
                topic
            )
        )

    if not valid_topics:

        no_topic_count += 1

        continue

    # Highest-scoring topic = primary topic
    primary_score, primary = max(
        valid_topics,
        key=lambda x: x[0]
    )

    primary_topic_rows.append({

        "openalex_id":
            row["openalex_id"],

        "publication_year":
            row["publication_year"],

        "primary_topic_id":
            primary.get("id"),

        "primary_topic":
            primary.get(
                "display_name"
            ),

        "primary_topic_score":
            primary_score,

        "primary_subfield":
            (
                primary
                .get("subfield", {})
                .get("display_name")
            ),

        "primary_subfield_id":
            (
                primary
                .get("subfield", {})
                .get("id")
            ),

        "primary_field":
            (
                primary
                .get("field", {})
                .get("display_name")
            ),

        "primary_field_id":
            (
                primary
                .get("field", {})
                .get("id")
            ),

        "primary_domain":
            (
                primary
                .get("domain", {})
                .get("display_name")
            ),

        "primary_domain_id":
            (
                primary
                .get("domain", {})
                .get("id")
            ),
    })


primary_topics = pd.DataFrame(
    primary_topic_rows
)


print(
    f"Publications with topic information: "
    f"{len(primary_topics)}"
)

print(
    f"Publications without topic information: "
    f"{no_topic_count}"
)


# ---------------------------------------------------------------------
# SAVE PUBLICATION-LEVEL PRIMARY TOPICS
# ---------------------------------------------------------------------

primary_topics.to_csv(
    OUTPUT_DIR
    / "publication_primary_topics.csv",
    index=False
)

primary_topics.to_pickle(
    OUTPUT_DIR
    / "publication_primary_topics.pkl"
)


# ---------------------------------------------------------------------
# MERGE PRIMARY TOPIC BACK INTO PUBLICATION DATA
# ---------------------------------------------------------------------

pubs_with_topics = pubs[
    pubs["openalex_id"].isin(
        primary_topics["openalex_id"]
    )
].copy()


print(
    f"Publications retained for topic analysis: "
    f"{len(pubs_with_topics)}"
)


pubs_with_topics.to_csv(
    OUTPUT_DIR
    / "gok_publications_with_primary_topic.csv",
    index=False
)

# =====================================================================
# TOPIC STATISTICS
# =====================================================================

total_publications = (
    len(pubs_with_topics)
)


publications_with_topics = (
    len(primary_topics)
)


# ---------------------------------------------------------------------
# REPORT PUBLICATIONS WITHOUT A PRIMARY TOPIC
# ---------------------------------------------------------------------

topic_ids = set(
    primary_topics["openalex_id"]
)

missing_topics = pubs[
    ~pubs["openalex_id"].isin(topic_ids)
].copy()


if len(missing_topics) > 0:

    print("\nPublications without an OpenAlex topic:")

    print(
        missing_topics[
            [
                "openalex_id",
                "publication_year",
                "title",
            ]
        ]
        .to_string(
            index=False
        )
    )

    missing_topics.to_csv(
        OUTPUT_DIR
        / "publications_without_topic.csv",
        index=False
    )

# ---------------------------------------------------------------------
# 1. PRIMARY TOPIC COUNTS
# ---------------------------------------------------------------------

topic_summary = (
    primary_topics
    .groupby(
        [
            "primary_topic_id",
            "primary_topic",
            "primary_subfield",
            "primary_field",
            "primary_domain",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        ),

        mean_topic_score=(
            "primary_topic_score",
            "mean"
        ),
    )
    .reset_index()
    .sort_values(
        "publications",
        ascending=False
    )
)


topic_summary[
    "percentage_of_publications"
] = (
    100
    *
    topic_summary[
        "publications"
    ]
    /
    publications_with_topics
)


topic_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_topic.csv",
    index=False
)


# ---------------------------------------------------------------------
# 2. PRIMARY TOPIC BY YEAR
# ---------------------------------------------------------------------

topics_by_year = (
    primary_topics
    .groupby(
        [
            "publication_year",
            "primary_topic_id",
            "primary_topic",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )
    .reset_index()
)


topics_by_year.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_topic_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# 3. PRIMARY FIELD COUNTS
# ---------------------------------------------------------------------

field_summary = (
    primary_topics
    .groupby(
        [
            "primary_field_id",
            "primary_field",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )
    .reset_index()
    .sort_values(
        "publications",
        ascending=False
    )
)


field_summary[
    "percentage_of_publications"
] = (
    100
    *
    field_summary[
        "publications"
    ]
    /
    publications_with_topics
)


field_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_field.csv",
    index=False
)


# ---------------------------------------------------------------------
# 4. PRIMARY FIELD BY YEAR
# ---------------------------------------------------------------------

fields_by_year = (
    primary_topics
    .groupby(
        [
            "publication_year",
            "primary_field_id",
            "primary_field",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )
    .reset_index()
)


fields_by_year.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_field_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# 5. PRIMARY SUBFIELD COUNTS
# ---------------------------------------------------------------------

subfield_summary = (
    primary_topics
    .groupby(
        [
            "primary_subfield_id",
            "primary_subfield",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )
    .reset_index()
    .sort_values(
        "publications",
        ascending=False
    )
)


subfield_summary[
    "percentage_of_publications"
] = (
    100
    *
    subfield_summary[
        "publications"
    ]
    /
    publications_with_topics
)


subfield_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_subfield.csv",
    index=False
)


# ---------------------------------------------------------------------
# 6. PRIMARY DOMAIN COUNTS
# ---------------------------------------------------------------------

domain_summary = (
    primary_topics
    .groupby(
        [
            "primary_domain_id",
            "primary_domain",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )
    .reset_index()
    .sort_values(
        "publications",
        ascending=False
    )
)


domain_summary[
    "percentage_of_publications"
] = (
    100
    *
    domain_summary[
        "publications"
    ]
    /
    publications_with_topics
)


domain_summary.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_domain.csv",
    index=False
)


# ---------------------------------------------------------------------
# 7. PRIMARY DOMAIN BY YEAR
# ---------------------------------------------------------------------

domains_by_year = (
    primary_topics
    .groupby(
        [
            "publication_year",
            "primary_domain_id",
            "primary_domain",
        ],
        dropna=False
    )
    .agg(
        publications=(
            "openalex_id",
            "nunique"
        )
    )
    .reset_index()
)


domains_by_year.to_csv(
    OUTPUT_DIR
    / "publications_by_primary_domain_year.csv",
    index=False
)


# =====================================================================
# FIGURES
# =====================================================================


# ---------------------------------------------------------------------
# FIGURE 1: TOP PRIMARY TOPICS
# ---------------------------------------------------------------------

top_topics = (
    topic_summary
    .head(TOP_N_TOPICS)
    .sort_values(
        "publications"
    )
)


plt.figure(
    figsize=(10, 8)
)

plt.barh(
    top_topics["primary_topic"],
    top_topics["publications"]
)

plt.xlabel(
    "Number of publications"
)

plt.ylabel(
    "Primary research topic"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Top {TOP_N_TOPICS} primary research topics"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "top_primary_topics.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 2: PRIMARY FIELDS
# ---------------------------------------------------------------------

fields_plot = (
    field_summary
    .sort_values(
        "publications"
    )
)


plt.figure(
    figsize=(10, 8)
)

plt.barh(
    fields_plot["primary_field"],
    fields_plot["publications"]
)

plt.xlabel(
    "Number of publications"
)

plt.ylabel(
    "Primary scientific field"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Publications by primary scientific field"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "publications_by_primary_field.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 3: PRIMARY DOMAINS
# ---------------------------------------------------------------------

domains_plot = (
    domain_summary
    .sort_values(
        "publications"
    )
)


plt.figure(
    figsize=(10, 6)
)

plt.barh(
    domains_plot["primary_domain"],
    domains_plot["publications"]
)

plt.xlabel(
    "Number of publications"
)

plt.ylabel(
    "Primary scientific domain"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Publications by primary scientific domain"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "publications_by_primary_domain.png",
    dpi=300
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 4: PRIMARY TOPIC TRENDS THROUGH TIME
# ---------------------------------------------------------------------

top_topic_names = (
    topic_summary
    .head(TOP_N_TOPICS)[
        "primary_topic"
    ]
    .tolist()
)


trend_data = (
    topics_by_year[
        topics_by_year[
            "primary_topic"
        ].isin(
            top_topic_names
        )
    ]
    .pivot_table(
        index="publication_year",
        columns="primary_topic",
        values="publications",
        aggfunc="sum",
        fill_value=0
    )
)


# Ensure all years are present

all_years = pd.Index(
    range(
        START_YEAR,
        END_YEAR + 1
    ),
    name="publication_year"
)


trend_data = (
    trend_data
    .reindex(
        all_years,
        fill_value=0
    )
)


plt.figure(
    figsize=(12, 8)
)

for topic in trend_data.columns:

    plt.plot(
        trend_data.index,
        trend_data[topic],
        marker="o",
        label=topic
    )


plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Number of publications"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    f"Trends in top {TOP_N_TOPICS} primary research topics"
)

plt.legend(
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "primary_topic_trends.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ---------------------------------------------------------------------
# FIGURE 5: PRIMARY TOPIC HEATMAP
# ---------------------------------------------------------------------

heatmap_data = (
    trend_data
    .T
)


plt.figure(
    figsize=(14, 10)
)

plt.imshow(
    heatmap_data,
    aspect="auto"
)

plt.colorbar(
    label="Number of publications"
)

plt.xticks(
    range(
        len(
            heatmap_data.columns
        )
    ),
    heatmap_data.columns,
    rotation=90
)

plt.yticks(
    range(
        len(
            heatmap_data.index
        )
    ),
    heatmap_data.index
)

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Primary research topic"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Primary research topics through time"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR
    / "primary_topic_heatmap.png",
    dpi=300
)

plt.close()


# =====================================================================
# SUMMARY
# =====================================================================

print("\n")
print("=" * 70)
print("PRIMARY PUBLICATION TOPIC ANALYSIS")
print("=" * 70)

print(
    f"Total publications: "
    f"{total_publications}"
)

print(
    f"Publications with primary topic: "
    f"{publications_with_topics}"
)

print(
    f"Publications without topic: "
    f"{no_topic_count}"
)

print(
    f"Unique primary topics: "
    f"{topic_summary['primary_topic_id'].nunique()}"
)

print(
    f"Unique primary subfields: "
    f"{subfield_summary['primary_subfield_id'].nunique()}"
)

print(
    f"Unique primary fields: "
    f"{field_summary['primary_field_id'].nunique()}"
)

print(
    f"Unique primary domains: "
    f"{domain_summary['primary_domain_id'].nunique()}"
)


print("\nTop primary topics:")

print(
    topic_summary[
        [
            "primary_topic",
            "primary_subfield",
            "primary_field",
            "publications",
            "percentage_of_publications",
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print("\nAnalysis complete.")