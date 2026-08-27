from pathlib import Path
import pandas as pd
from pyalex import Authors, config

# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------

INPUT_FILE_1 = Path("../data/gok_present_people_seed.csv")
INPUT_FILE_2 = Path("../data/gok_past_people_seed.csv")
OUTPUT_FILE = Path("../data/gok_people.csv")


# ---------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------

def find_openalex_author(name):
    """
    Search OpenAlex for an author by name.

    Returns the best candidate and a few useful fields.
    """

    results = list(
        Authors()
        .search(name)
        .get(per_page=10)
    )

    if not results:
        return None

    author = results[0]

    return {
        "openalex_author_id": author["id"],
        "display_name_openalex": author.get("display_name"),
        "orcid": author.get("orcid"),
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "last_known_institutions": (
            author.get("last_known_institutions")
        ),
    }


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    with open("../user_key", "r") as f:
        user_key = f.read()
    config.email = user_key

    with open("../api_key", "r") as f:
        api_key = f.read()
    config.api_key = api_key

    results = []

    people = pd.read_csv(INPUT_FILE_1)
    for _, person in people.iterrows():
        name = person["name"]
        print(f"Searching OpenAlex: {name}")
        match = find_openalex_author(name)
        row = person.to_dict()
        if match:
            row.update(match)
        else:
            row.update({
                "openalex_author_id": None,
                "display_name_openalex": None,
                "orcid": None,
                "works_count": None,
                "cited_by_count": None,
                "last_known_institutions": None,
            })
        results.append(row)

    people = pd.read_csv(INPUT_FILE_2)
    for _, person in people.iterrows():

        name = person["name"]
        print(f"Searching OpenAlex: {name}")
        match = find_openalex_author(name)
        row = person.to_dict()
        if match:
            row.update(match)
        else:
            row.update({
                "openalex_author_id": None,
                "display_name_openalex": None,
                "orcid": None,
                "works_count": None,
                "cited_by_count": None,
                "last_known_institutions": None,
            })
        results.append(row)

    output = pd.DataFrame(results)

    output.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"\nSaved {len(output)} people to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()