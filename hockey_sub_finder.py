from io import StringIO

import pandas as pd
import requests
import streamlit as st

try:
    import certifi
except ImportError:  # pragma: no cover - only used on machines missing certifi
    certifi = None


st.set_page_config(
    page_title="Hockey Sub Finder",
    layout="wide",
    initial_sidebar_state="collapsed",
)


LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/15mWSFY4vfarNrKh49SoXsOqCJFiUz8y68JGSemtVzv4/export?format=csv&gid=0",
        "Schedule_Sheet": "YOUR_NAHL_SCHEDULE_CSV_URL_HERE",
    },
}


def is_placeholder_url(url):
    return not url or "YOUR_" in url


@st.cache_data(ttl=300)
def fetch_csv_text(url):
    if is_placeholder_url(url):
        raise ValueError("This sheet URL is still a placeholder.")

    verify = certifi.where() if certifi else True
    response = requests.get(url, timeout=20, verify=verify)
    response.raise_for_status()
    return response.text


def find_header_row(rows, required_headers):
    required = {header.lower() for header in required_headers}

    for index, row in enumerate(rows):
        normalized = {str(cell).strip().lower() for cell in row if str(cell).strip()}
        if required.issubset(normalized):
            return index

    return None


def read_table_from_sheet(url, required_headers):
    csv_text = fetch_csv_text(url)
    raw_rows = pd.read_csv(StringIO(csv_text), header=None, dtype=str).fillna("")
    header_row = find_header_row(raw_rows.values.tolist(), required_headers)

    if header_row is None:
        raise ValueError(
            "Could not find a table header containing: "
            + ", ".join(required_headers)
        )

    df = pd.read_csv(StringIO(csv_text), header=header_row, dtype=str).fillna("")
    df.columns = [str(column).strip() for column in df.columns]
    df = df.loc[:, [column for column in df.columns if not column.startswith("Unnamed")]]
    return df


def clean_player_name(name):
    name = str(name).strip()
    if "," not in name:
        return name

    last, first = [part.strip() for part in name.split(",", 1)]
    return f"{first} {last}".strip()


def normalize_roster(df):
    column_map = {
        "Position": "Position",
        "Name": "Name",
        "Rating": "Rating",
        "Rating ": "Rating",
        "Team": "Team",
    }

    df = df.rename(columns={column: column_map.get(column, column) for column in df.columns})
    required = ["Name", "Team", "Rating", "Position"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Roster sheet is missing: " + ", ".join(missing))

    roster = df[required].copy()
    roster["Name"] = roster["Name"].map(clean_player_name)
    roster["Team"] = roster["Team"].astype(str).str.strip()
    roster["Position"] = roster["Position"].astype(str).str.strip()
    roster["Rating"] = pd.to_numeric(roster["Rating"], errors="coerce")
