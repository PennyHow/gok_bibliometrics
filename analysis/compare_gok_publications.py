from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

GOK_PUBLICATIONS_FILE = Path(
    "../data/gok_publications.csv"
)

GEUS_PUBLICATIONS_FILE = Path(
    "../data/geus_publications.csv"
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

pubs1 = pd.read_csv(GOK_PUBLICATIONS_FILE)
pubs2 = pd.read_csv(GEUS_PUBLICATIONS_FILE)
authors = pd.read_csv(AUTHORS_FILE)


gok_pubs = pubs1[
    pubs1["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()

gok_pubs = gok_pubs[gok_pubs["type"] == "article"]


geus_pubs = pubs2[
    pubs2["publication_year"].between(
        START_YEAR,
        END_YEAR
    )
].copy()

geus_pubs = geus_pubs[geus_pubs["type"] == "article"]

# ---------------------------------------------------------------------
# PUBLICATIONS PER YEAR
# ---------------------------------------------------------------------

gok_pubs_per_year = (
    gok_pubs
    .groupby("publication_year")
    .agg(
        publications=("openalex_id", "nunique"),
        citations=("cited_by_count", "sum"),
    )
    .reset_index()
)

gok_pubs_per_year["mean_citations"] = (
    gok_pubs_per_year["citations"]
    / gok_pubs_per_year["publications"]
)

geus_pubs_per_year = (
    geus_pubs
    .groupby("publication_year")
    .agg(
        publications=("openalex_id", "nunique"),
        citations=("cited_by_count", "sum"),
    )
    .reset_index()
)

geus_pubs_per_year["mean_citations"] = (
    geus_pubs_per_year["citations"]
    / geus_pubs_per_year["publications"]
)

pub_percentage = []
for yr,gok,geus in zip(gok_pubs_per_year["publication_year"], gok_pubs_per_year["publications"], geus_pubs_per_year["publications"]):
    print(f"{yr}: {gok} / {geus} publications ({(gok/geus)*100} %)")
    pub_percentage.append((gok / geus) * 100)

# ---------------------------------------------------------------------
# PLOT: PUBLICATIONS PER YEAR
# ---------------------------------------------------------------------

plt.figure()

plt.plot(
    gok_pubs_per_year["publication_year"],
    gok_pubs_per_year["publications"],
    marker="o",
    color="red",
    label="Gok publications",
)

plt.plot(
    geus_pubs_per_year["publication_year"],
    geus_pubs_per_year["publications"],
    marker="o",
    color="blue",
    label="GEUS publications",
)

for i, percent in enumerate(pub_percentage):
    if i % 2 == 0:
        txt = f"{percent:.0f}%"
        plt.annotate(
            txt,
            (gok_pubs_per_year["publication_year"][i], gok_pubs_per_year["publications"][i]),
            textcoords="offset points",
            xytext=(0,10),
            fontsize="x-small",
            ha="center",
    )

plt.xlabel("Publication year")
plt.ylabel("Number of publications")
plt.legend(loc="upper left")

plt.title(
    "GEUS vs. GOK\n"
    "Publication output"
)

plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "publication_comparison.png",
    dpi=300
)

plt.close()


print("Analysis complete.")