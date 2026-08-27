from pathlib import Path
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


# ---------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------

pubs = pd.read_csv(PUBLICATIONS_FILE)
authors = pd.read_csv(AUTHORS_FILE)


pubs = pubs[
    pubs["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()

pubs = pubs[pubs["type"] == "article"]

# ---------------------------------------------------------------------
# PUBLICATIONS PER YEAR
# ---------------------------------------------------------------------

pubs_per_year = (
    pubs
    .groupby("publication_year")
    .agg(
        publications=("openalex_id", "nunique"),
        citations=("cited_by_count", "sum"),
    )
    .reset_index()
)

pubs_per_year["mean_citations"] = (
    pubs_per_year["citations"]
    / pubs_per_year["publications"]
)

pubs_per_year.to_csv(
    OUTPUT_DIR / "publications_by_year.csv",
    index=False
)


# ---------------------------------------------------------------------
# JOURNALS
# ---------------------------------------------------------------------

# primary_location contains nested information, so depending on the
# exact pyalex/OpenAlex response structure we may need to extract the
# source name here.

def get_journal(work_location):

    if not isinstance(work_location, dict):
        return None

    source = work_location.get("source")

    if not isinstance(source, dict):
        return None

    return source.get("display_name")


pubs["journal"] = pubs[
    "primary_location"
].apply(get_journal)


journals = (
    pubs
    .groupby("journal")
    .agg(
        publications=("openalex_id", "nunique"),
        citations=("cited_by_count", "sum"),
    )
    .reset_index()
    .sort_values(
        "publications",
        ascending=False
    )
)

journals["percentage_of_output"] = (
    100
    * journals["publications"]
    / journals["publications"].sum()
)

journals.to_csv(
    OUTPUT_DIR / "publications_by_journal.csv",
    index=False
)


# ---------------------------------------------------------------------
# TOPICS
# ---------------------------------------------------------------------

topic_rows = []

for _, row in pubs.iterrows():

    topics = row["topics"]

    if pd.isna(topics):
        continue

    # If stored as a Python representation/string,
    # convert it appropriately here.

    # Placeholder for robust parsing:
    if isinstance(topics, list):

        for topic in topics:

            if isinstance(topic, dict):

                topic_rows.append({
                    "openalex_id":
                        row["openalex_id"],

                    "year":
                        row["publication_year"],

                    "topic":
                        topic.get("display_name"),

                    "score":
                        topic.get("score"),

                    "subfield":
                        (
                            topic
                            .get("subfield", {})
                            .get("display_name")
                        ),

                    "field":
                        (
                            topic
                            .get("field", {})
                            .get("display_name")
                        ),

                    "domain":
                        (
                            topic
                            .get("domain", {})
                            .get("display_name")
                        ),
                })


topics = pd.DataFrame(topic_rows)


if len(topics) > 0:

    topic_summary = (
        topics
        .groupby(
            [
                "domain",
                "field",
                "subfield",
                "topic"
            ]
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

    topic_summary.to_csv(
        OUTPUT_DIR / "topics.csv",
        index=False
    )


# ---------------------------------------------------------------------
# PLOT: PUBLICATIONS PER YEAR
# ---------------------------------------------------------------------

plt.figure()

plt.plot(
    pubs_per_year["publication_year"],
    pubs_per_year["publications"],
    marker="o"
)

plt.xlabel("Publication year")
plt.ylabel("Number of publications")

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Publication output"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "publications_per_year.png",
    dpi=300
)

plt.close()


print("Analysis complete.")