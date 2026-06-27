import re
import shutil
import pandas as pd
from pathlib import Path

SOURCE_FOLDER = Path(
    "/Users/varunpanuganti/Desktop/NSF-REU-Project/RateMyProfessor SampleData, Contact hejibo@usee.tech for the whole 5G dataset"
)

OUTPUT_FOLDER = SOURCE_FOLDER / "selected_professor_files"
OUTPUT_FOLDER.mkdir(exist_ok=True)

SUMMARY_OUTPUT = SOURCE_FOLDER / "professor_summary.csv"
USABLE_OUTPUT = SOURCE_FOLDER / "usable_professors.csv"

COMMENTS_COL = "comments"

FEMALE_PATTERN = re.compile(r"\b(she|her|hers)\b", re.IGNORECASE)
MALE_PATTERN = re.compile(r"\b(he|him|his)\b", re.IGNORECASE)

USA_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID",
    "IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS",
    "MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK",
    "OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV",
    "WI","WY","DC"
}

CANADA_PROVINCES = {
    "AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"
}

HIGH_TIER = {
    "Massachusetts Institute of Technology",
    "MIT",
    "Stanford University",
    "Harvard University",
    "Princeton University",
    "Yale University",
    "California Institute of Technology",
    "Caltech",
}

MID_TIER = {
    "University of Washington",
    "Georgia Institute of Technology",
    "Georgia Tech",
    "University of Wisconsin Madison",
    "University of Wisconsin-Madison",
    "University of Michigan",
    "University of Illinois Urbana-Champaign",
    "Purdue University",
}


def clean_state(state):
    if pd.isna(state):
        return ""
    return str(state).strip().upper()


def infer_country(state):
    state = clean_state(state)

    if state in USA_STATES:
        return "USA"
    elif state in CANADA_PROVINCES:
        return "Canada"
    else:
        return "Other"


def infer_tier(school_name):
    school_name = str(school_name).strip()

    if school_name in HIGH_TIER:
        return "high"
    elif school_name in MID_TIER:
        return "middle"
    else:
        return "low"


def infer_gender_from_reviews(comments):
    all_reviews = " ".join(comments.dropna().astype(str))

    female_count = len(FEMALE_PATTERN.findall(all_reviews))
    male_count = len(MALE_PATTERN.findall(all_reviews))

    if female_count > 0 and male_count == 0:
        gender = "female"
    elif male_count > 0 and female_count == 0:
        gender = "male"
    elif female_count == 0 and male_count == 0:
        gender = "unknown"
    else:
        gender = "ambiguous"

    total = female_count + male_count

    if total > 0:
        confidence = max(female_count, male_count) / total
    else:
        confidence = 0

    return gender, female_count, male_count, confidence


def safe_get(row, col):
    return row[col] if col in row.index else None


# MAIN SCRIPT

records = []

csv_files = list(SOURCE_FOLDER.glob("*.csv"))

print(f"Found {len(csv_files)} CSV files.")

for file in csv_files:
    try:
        df = pd.read_csv(file)

        if df.empty:
            continue

        if COMMENTS_COL not in df.columns:
            print(f"Skipping {file.name}: no comments column")
            continue

        first_row = df.iloc[0]

        professor_name = safe_get(first_row, "professor_name")
        school_name = safe_get(first_row, "school_name")
        local_name = safe_get(first_row, "local_name")
        state_name = safe_get(first_row, "state_name")
        department_name = safe_get(first_row, "department_name")

        gender, female_count, male_count, confidence = infer_gender_from_reviews(df[COMMENTS_COL])

        country = infer_country(state_name)
        tier = infer_tier(school_name)

        avg_rating = df["star_rating"].mean() if "star_rating" in df.columns else None
        avg_difficulty = df["diff_index"].mean() if "diff_index" in df.columns else None

        records.append({
            "filename": file.name,
            "full_path": str(file),
            "professor_name": professor_name,
            "school_name": school_name,
            "city": local_name,
            "state": state_name,
            "country": country,
            "tier": tier,
            "department": department_name,
            "num_reviews": len(df),
            "female_pronoun_count": female_count,
            "male_pronoun_count": male_count,
            "total_gendered_pronouns": female_count + male_count,
            "pronoun_confidence": confidence,
            "inferred_gender": gender,
            "avg_rating": avg_rating,
            "avg_difficulty": avg_difficulty
        })

    except Exception as e:
        print(f"Error reading {file.name}: {e}")


summary = pd.DataFrame(records)

summary.to_csv(SUMMARY_OUTPUT, index=False)

usable_professors = summary[
    (summary["country"].isin(["USA", "Canada"])) &
    (summary["inferred_gender"].isin(["male", "female"]))
].copy()

usable_professors.to_csv(USABLE_OUTPUT, index=False)


# =========================
# PRINT SUMMARY
# =========================

print("\nDone.")
print(f"Saved full summary to: {SUMMARY_OUTPUT}")
print(f"Saved usable professor summary to: {USABLE_OUTPUT}")

print("\nCountry counts:")
print(summary["country"].value_counts(dropna=False))

print("\nGender counts:")
print(summary["inferred_gender"].value_counts(dropna=False))

print("\nTier counts:")
print(summary["tier"].value_counts(dropna=False))

print("\nUsable professors by country/gender:")
print(pd.crosstab(
    usable_professors["country"],
    usable_professors["inferred_gender"]
))

print("\nTop schools by usable professor count:")
print(
    usable_professors["school_name"]
    .value_counts()
    .head(30)
)