import pandas as pd
from pathlib import Path

# Define inputs and outputs
url = (
    "https://eng.geus.dk/about/contact/"
    "phone-book?departmentId=Glaciology+and+Climate"
)

OUTPUT_FILE = Path("../data/gok_present_people_seed.csv")


# Read HTML from url
tables = pd.read_html(url)


# Create people database
people = (
    tables[0]
    .rename(columns={
        "Name": "name",
        "Position": "role",
        "Email": "email",
        "Department": "department",
        "Phone": "phone",
    })
)
people["department"] = people["department"].str.strip()


# Assert that all people are in GoK department
assert people["department"].eq(
    "Glaciology and Climate"
).all()
print(f"{len(people)} people found")


# Save to csv file
people.to_csv(
    OUTPUT_FILE,
    index=False
)
print(f"\nSaved to: {OUTPUT_FILE}")