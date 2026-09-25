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
# publication-download script.
# ---------------------------------------------------------------------

GEUS_OPENALEX_ID = "https://openalex.org/I2801979204"


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
    Check whether an author had GEUS among their institutions
    on the publication.
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


# =====================================================================
# KEEP ONLY AUTHORS FROM QUALIFYING PUBLICATIONS
# =====================================================================

authors = authors[
    authors["openalex_work_id"].isin(
        pubs["openalex_id"]
    )
].copy()


# =====================================================================
# CONVERT AUTHOR POSITION TO NUMERIC
# =====================================================================

authors["author_position"] = pd.to_numeric(
    authors["author_position"],
    errors="coerce"
)


authors = authors[
    authors["author_position"].notna()
].copy()


authors["author_position"] = (
    authors["author_position"]
    .astype(int)
)


# =====================================================================
# IDENTIFY GEUS-AFFILIATED AUTHORS
# =====================================================================

authors["is_geus_author"] = (
    authors["institutions"]
    .apply(has_geus_affiliation)
)


print()
print(
    f"GEUS-affiliated authorships: "
    f"{authors['is_geus_author'].sum():,}"
)


# =====================================================================
# IDENTIFY FIRST AND LAST AUTHOR POSITIONS
# =====================================================================

# Each publication can have a different number of authors.
#
# Therefore:
#
#   first author = position 1
#   last author  = maximum author_position for that publication
#
# This is preferable to assuming a fixed position for the last author.

last_positions = (

    authors

    .groupby(
        "openalex_work_id"
    )["author_position"]

    .max()

    .rename(
        "last_author_position"
    )

    .reset_index()
)


authors = authors.merge(
    last_positions,
    on="openalex_work_id",
    how="left"
)


# =====================================================================
# IDENTIFY GEUS FIRST AUTHORS
# =====================================================================

geus_first = authors[
    (
        authors["is_geus_author"]
    )
    &
    (
        authors["author_position"] == 1
    )
].copy()


geus_first_work_ids = set(
    geus_first[
        "openalex_work_id"
    ]
)


print(
    f"Publications with GEUS first author: "
    f"{len(geus_first_work_ids):,}"
)


# =====================================================================
# IDENTIFY GEUS LAST AUTHORS
# =====================================================================

geus_last = authors[
    (
        authors["is_geus_author"]
    )
    &
    (
        authors["author_position"]
        ==
        authors["last_author_position"]
    )
].copy()


geus_last_work_ids = set(
    geus_last[
        "openalex_work_id"
    ]
)


print(
    f"Publications with GEUS last author: "
    f"{len(geus_last_work_ids):,}"
)


# =====================================================================
# IDENTIFY GEUS CO-AUTHORS
# =====================================================================

# A co-author here means a GEUS author who is neither first nor last.

geus_middle = authors[
    (
        authors["is_geus_author"]
    )
    &
    (
        authors["author_position"] != 1
    )
    &
    (
        authors["author_position"]
        !=
        authors["last_author_position"]
    )
].copy()


geus_middle_work_ids = set(
    geus_middle[
        "openalex_work_id"
    ]
)


print(
    f"Publications with GEUS co-author: "
    f"{len(geus_middle_work_ids):,}"
)


# =====================================================================
# ASSIGN ONE ROLE TO EACH PUBLICATION
# =====================================================================

# The categories are deliberately mutually exclusive.
#
# Priority:
#
#   1. First author
#   2. Last author
#   3. Co-author
#
# This means that if a publication has both a GEUS first author and
# a GEUS last author, it is classified as "First author".
#
# This prevents double-counting in the stacked bar chart.

def assign_role(work_id):

    if work_id in geus_first_work_ids:
        return "First author"

    elif work_id in geus_last_work_ids:
        return "Last author"

    elif work_id in geus_middle_work_ids:
        return "Co-author"

    else:
        return None


pubs["authorship_role"] = (
    pubs["openalex_id"]
    .apply(assign_role)
)


# Keep only publications with at least one GEUS author role
role_pubs = pubs[
    pubs["authorship_role"].notna()
].copy()


print()
print(
    f"Publications assigned to an authorship role: "
    f"{len(role_pubs):,}"
)


# =====================================================================
# CHECK THAT EVERY PUBLICATION HAS ONLY ONE ROLE
# =====================================================================

role_counts = (
    role_pubs
    .groupby(
        "authorship_role"
    )["openalex_id"]
    .nunique()
)


print()
print("=" * 70)
print("AUTHORSHIP ROLE COUNTS")
print("=" * 70)

print()

print(
    role_counts.to_string()
)


# =====================================================================
# PUBLICATIONS BY YEAR AND ROLE
# =====================================================================

role_by_year = (

    role_pubs

    .groupby(
        [
            "publication_year",
            "authorship_role"
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
# PIVOT
# =====================================================================

role_pivot = (

    role_by_year

    .pivot(
        index="publication_year",
        columns="authorship_role",
        values="publications"
    )

    .fillna(0)

    .reset_index()
)


# ---------------------------------------------------------------------
# Make sure all three columns exist
# ---------------------------------------------------------------------

for column in [
    "First author",
    "Last author",
    "Co-author"
]:

    if column not in role_pivot.columns:

        role_pivot[column] = 0


# Convert counts to integers

for column in [
    "First author",
    "Last author",
    "Co-author"
]:

    role_pivot[column] = (
        role_pivot[column]
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


role_pivot = (

    all_years

    .merge(
        role_pivot,
        on="publication_year",
        how="left"
    )

    .fillna(0)
)


for column in [
    "First author",
    "Last author",
    "Co-author"
]:

    role_pivot[column] = (
        role_pivot[column]
        .astype(int)
    )


# =====================================================================
# TOTAL
# =====================================================================

role_pivot["total"] = (

    role_pivot["First author"]

    + role_pivot["Last author"]

    + role_pivot["Co-author"]
)


# =====================================================================
# SAVE SUMMARY
# =====================================================================

role_pivot.to_csv(

    OUTPUT_DIR
    / "publications_by_authorship_role_by_year.csv",

    index=False
)


# =====================================================================
# SAVE PUBLICATION-LEVEL DATA
# =====================================================================

publication_roles = role_pubs[
    [
        "openalex_id",
        "publication_year",
        "title",
        "doi",
        "authorship_role"
    ]
].copy()


publication_roles = publication_roles.sort_values(
    [
        "publication_year",
        "authorship_role",
        "title"
    ]
)


publication_roles.to_csv(

    OUTPUT_DIR
    / "publications_by_authorship_role.csv",

    index=False
)


# =====================================================================
# PRINT YEARLY SUMMARY
# =====================================================================

print()
print("=" * 70)
print("PUBLICATIONS BY AUTHORSHIP ROLE")
print("=" * 70)

print()

print(
    role_pivot.to_string(
        index=False
    )
)


# =====================================================================
# STACKED BAR CHART WITH VALUE LABELS
# =====================================================================

plt.figure(
    figsize=(10, 6)
)


# ---------------------------------------------------------------------
# First-author publications
# ---------------------------------------------------------------------

plt.bar(

    role_pivot["publication_year"],

    role_pivot["First author"],

    label="First author"
)


# ---------------------------------------------------------------------
# Last-author publications
# ---------------------------------------------------------------------

plt.bar(

    role_pivot["publication_year"],

    role_pivot["Last author"],

    bottom=role_pivot["First author"],

    label="Last author"
)


# ---------------------------------------------------------------------
# Co-author publications
# ---------------------------------------------------------------------

plt.bar(

    role_pivot["publication_year"],

    role_pivot["Co-author"],

    bottom=(
        role_pivot["First author"]
        +
        role_pivot["Last author"]
    ),

    label="Co-author"
)


# =====================================================================
# ADD LABELS TO EACH BAR SEGMENT
# =====================================================================

for i, row in role_pivot.iterrows():

    year = row["publication_year"]

    first = row["First author"]
    last = row["Last author"]
    coauthor = row["Co-author"]


    # -------------------------------------------------------------
    # First-author label
    # -------------------------------------------------------------

    if first > 0:

        plt.text(

            year,

            first / 2,

            str(first),

            ha="center",

            va="center",

            fontsize=9
        )


    # -------------------------------------------------------------
    # Last-author label
    # -------------------------------------------------------------

    if last > 0:

        plt.text(

            year,

            first + (last / 2),

            str(last),

            ha="center",

            va="center",

            fontsize=9
        )


    # -------------------------------------------------------------
    # Co-author label
    # -------------------------------------------------------------

    if coauthor > 0:

        plt.text(

            year,

            first + last + (coauthor / 2),

            str(coauthor),

            ha="center",

            va="center",

            fontsize=9
        )


# =====================================================================
# AXIS / TITLE
# =====================================================================

plt.xlabel(
    "Publication year"
)

plt.ylabel(
    "Number of publications"
)

plt.title(
    "GEUS Department of Glaciology and Climate\n"
    "Publications by authorship role"
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
    / "publications_by_authorship_role_by_year.png",

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
    f"{OUTPUT_DIR / 'publications_by_authorship_role_by_year.csv'}"
)

print(
    f"Saved publication list: "
    f"{OUTPUT_DIR / 'publications_by_authorship_role.csv'}"
)

print(
    f"Saved figure: "
    f"{FIGURE_DIR / 'publications_by_authorship_role_by_year.png'}"
)