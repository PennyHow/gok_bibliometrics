from pathlib import Path
import pandas as pd
from pyalex import Works, config


# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

with open("../user_key", "r") as f:
    user_key = f.read()
config.email = user_key

with open("../api_key", "r") as f:
    api_key = f.read()
config.api_key = api_key

PEOPLE_FILE = Path("../data/gok_people.csv")

PUBLICATIONS_FILE = Path(
    "../data/gok_publications.csv"
)

AUTHORS_FILE = Path(
    "../data/gok_authors.csv"
)


START_YEAR = 2000
END_YEAR = 2026


# OpenAlex institution ID for:
# Geological Survey of Denmark and Greenland (GEUS)
GEUS_OPENALEX_ID = "https://openalex.org/I2801979204"


# ---------------------------------------------------------------------
# LOAD PEOPLE
# ---------------------------------------------------------------------

people = pd.read_csv(PEOPLE_FILE)

gok_author_ids = set(
    people["openalex_author_id"]
    .dropna()
    .astype(str)
)

print(
    f"Found {len(gok_author_ids)} GoK OpenAlex author IDs"
)


# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------

def get_author_id(authorship):
    """
    Return the OpenAlex author ID from an authorship.
    """
    author = authorship.get("author") or {}

    return author.get("id")


def get_institution_ids(authorship):
    """
    Return all OpenAlex institution IDs associated with
    an authorship.
    """
    institutions = authorship.get(
        "institutions"
    ) or []

    return {
        institution.get("id")
        for institution in institutions
        if institution.get("id")
    }


def is_gok_geus_authorship(authorship):
    """
    True if this authorship belongs to one of our
    GoK researchers AND the authorship lists GEUS.
    """
    author_id = get_author_id(authorship)

    if author_id not in gok_author_ids:
        return False

    institution_ids = get_institution_ids(
        authorship
    )

    return GEUS_OPENALEX_ID in institution_ids


# ---------------------------------------------------------------------
# DOWNLOAD WORKS
# ---------------------------------------------------------------------

all_works = []

for author_id in gok_author_ids:

    print(
        f"Downloading works for {author_id}"
    )

    works = (
        Works()
        .filter(
            author={"id": author_id},
            publication_year=(
                f"{START_YEAR}-{END_YEAR}"
            )
        )
    )

    for page in works.paginate(
        per_page=200
    ):
        all_works.extend(page)


print(
    f"\nDownloaded {len(all_works)} "
    "author-work records"
)


# ---------------------------------------------------------------------
# REMOVE DUPLICATE WORKS
# ---------------------------------------------------------------------

unique_works = {}
for work in all_works:
    unique_works[work["id"]] = work

print(
    f"Unique publications before "
    f"affiliation filtering: "
    f"{len(unique_works)}"
)


# ---------------------------------------------------------------------
# IDENTIFY QUALIFYING PUBLICATIONS AND RETAIN
# ---------------------------------------------------------------------

qualifying_works = {}
qualifying_authorships = {}

for work_id, work in unique_works.items():
    authorships = work.get(
        "authorships",
        []
    )

    # Find all GoK authors who ALSO have GEUS affiliation
    gok_geus_authorships = [
        authorship
        for authorship in authorships
        if is_gok_geus_authorship(authorship)
    ]

    # Keep publication only if at least one such author exists
    if len(gok_geus_authorships) == 0:
        continue
    qualifying_works[work_id] = work
    qualifying_authorships[work_id] = (
        gok_geus_authorships
    )

print(
    f"Publications with GoK + GEUS "
    f"affiliation: "
    f"{len(qualifying_works)}"
)


# Flatten publication entries
publication_rows = []
author_rows = []
for work_id, work in qualifying_works.items():

    # QUALIFYING GOK AUTHORS
    gok_authorships = (
        qualifying_authorships[work_id]
    )

    gok_author_names = []
    gok_author_ids_for_work = []

    for authorship in gok_authorships:
        author = authorship.get(
            "author"
        ) or {}
        author_id = author.get("id")
        author_name = author.get(
            "display_name"
        )
        if author_name:
            gok_author_names.append(
                author_name
            )
        if author_id:
            gok_author_ids_for_work.append(
                author_id
            )


    # PUBLICATION RECORD
    publication_rows.append({

        "openalex_id":
            work["id"],

        "doi":
            work.get("doi"),

        "title":
            work.get("title"),

        "publication_year":
            work.get("publication_year"),

        "publication_date":
            work.get("publication_date"),

        "type":
            work.get("type"),

        "cited_by_count":
            work.get("cited_by_count"),

        "is_oa":
            (
                work.get("open_access", {})
                .get("is_oa")
            ),

        "oa_status":
            (
                work.get("open_access", {})
                .get("oa_status")
            ),

        "primary_location":
            work.get("primary_location"),

        "primary_topic":
            work.get("primary_topic"),

        "topics":
            work.get("topics"),

        "keywords":
            work.get("keywords"),

        "concepts":
            work.get("concepts"),


        # GOK-SPECIFIC INFORMATION
        "gok_author_count":
            len(gok_authorships),

        "gok_authors":
            "; ".join(gok_author_names),

        "gok_author_ids":
            "; ".join(gok_author_ids_for_work),

    })


    # ALL AUTHORS
    # We retain ALL authors, not just GoK authors.
    # This allows later analysis of collaborations.
    for position, authorship in enumerate(
        work.get("authorships", [])
    ):

        author = authorship.get(
            "author",
            {}
        )

        author_id = author.get("id")

        institution_ids = (
            get_institution_ids(
                authorship
            )
        )

        is_gok_author = (
            author_id in gok_author_ids
        )

        has_geus_affiliation = (
            GEUS_OPENALEX_ID
            in institution_ids
        )

        author_rows.append({

            "openalex_work_id":
                work["id"],

            "author_position":
                position + 1,

            "author_id":
                author_id,

            "author_name":
                author.get(
                    "display_name"
                ),

            "orcid":
                author.get("orcid"),

            "is_corresponding":
                authorship.get(
                    "is_corresponding"
                ),

            "institutions":
                authorship.get(
                    "institutions"
                ),

            "institution_ids":
                "; ".join(
                    sorted(
                        institution_ids
                    )
                ),

            "raw_affiliation_strings":
                authorship.get(
                    "raw_affiliation_strings"
                ),

            "is_gok_author":
                is_gok_author,

            "has_geus_affiliation":
                has_geus_affiliation,

            "is_gok_geus_author":
                (
                    is_gok_author
                    and
                    has_geus_affiliation
                ),

        })


# ---------------------------------------------------------------------
# SAVE
# ---------------------------------------------------------------------

publications = pd.DataFrame(
    publication_rows
)

authors = pd.DataFrame(
    author_rows
)


# Pickle versions preserve the nested Python objects.
publications.to_pickle(
    "data/gok_publications.pkl"
)

authors.to_pickle(
    "data/gok_authors.pkl"
)


# CSV versions are convenient for inspection
# and analysis in other software.

publications.to_csv(
    PUBLICATIONS_FILE,
    index=False
)

authors.to_csv(
    AUTHORS_FILE,
    index=False
)


# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------

print("\nDone.")

print(
    f"Qualifying publications: "
    f"{len(publications)}"
)

print(
    f"Author records: "
    f"{len(authors)}"
)

print(
    "Publications with multiple "
    "GoK/GEUS authors: "
    f"{sum(publications['gok_author_count'] > 1)}"
)