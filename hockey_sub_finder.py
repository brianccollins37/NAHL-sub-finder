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
    roster = roster.dropna(subset=["Name", "Team", "Rating", "Position"])
    roster = roster[(roster["Name"] != "") & (roster["Team"] != "")]
    return roster.sort_values(["Team", "Rating", "Name"], ascending=[True, False, True])


def normalize_subs(df):
    df = df.rename(
        columns={
            "Player Rating": "Rating",
            "Pos": "Position",
            "First Name": "First Name",
            "Last Name": "Last Name",
            "Cell Phone": "Phone",
        }
    )

    required = ["Rating", "Position", "First Name", "Last Name"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Sub sheet is missing: " + ", ".join(missing))

    subs = df.copy()
    subs["Name"] = (
        subs["First Name"].astype(str).str.strip()
        + " "
        + subs["Last Name"].astype(str).str.strip()
    ).str.strip()
    subs["Position"] = subs["Position"].astype(str).str.strip()
    subs["Rating"] = pd.to_numeric(subs["Rating"], errors="coerce")
    subs = subs.dropna(subset=["Name", "Rating", "Position"])
    subs = subs[(subs["Name"] != "") & (subs["Position"] != "")]

    display_columns = ["Name", "Rating", "Position"]
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns:
            display_columns.append(optional_column)

    return subs[display_columns].sort_values(["Rating", "Name"], ascending=[False, True])


def load_roster(url):
    df = read_table_from_sheet(url, required_headers=["Position", "Name", "Team"])
    return normalize_roster(df)


def load_subs(url):
    df = read_table_from_sheet(url, required_headers=["Player Rating", "First Name", "Last Name"])
    return normalize_subs(df)


def is_goalie(position):
    value = str(position).strip().upper()
    return value in {"G", "GOAL", "GOALIE", "GOALTENDER"} or value.startswith("GOAL")


def format_rating(value):
    return f"{float(value):g}"


st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
config = LEAGUE_CONFIG[league]

try:
    subs_df = load_subs(config["Sub_Sheet"])
except Exception as error:
    st.error(f"Could not load the {league} sub sheet: {error}")
    st.stop()

roster_df = pd.DataFrame()
roster_error = None

try:
    roster_df = load_roster(config["Roster_Sheet"])
except Exception as error:
    roster_error = error


st.subheader("1. Select Missing Player")

if not roster_df.empty:
    team_list = sorted(roster_df["Team"].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list)

    team_roster = roster_df[roster_df["Team"] == selected_team].copy()
    team_roster["Label"] = team_roster.apply(
        lambda row: f"{row['Name']} - {row['Position']} - {format_rating(row['Rating'])}",
        axis=1,
    )

    selected_label = st.selectbox("Missing Player", team_roster["Label"].tolist())
    player_row = team_roster[team_roster["Label"] == selected_label].iloc[0]
    target_rating = float(player_row["Rating"])
    target_position = player_row["Position"]

    st.info(
        f"Targeting: {player_row['Name']} "
        f"(Rating: {format_rating(target_rating)} | Pos: {target_position})"
    )
else:
    st.warning(
        f"Roster could not be loaded for {league}: {roster_error}. "
        "Enter the missing player's rating and position manually."
    )
    selected_team = None
    target_rating = st.number_input("Missing Player Rating", min_value=0.0, value=100.0, step=1.0)
    target_position = st.selectbox("Missing Player Position", ["F", "D", "G"])


st.subheader("2. Eligible Subs")

eligible = subs_df[subs_df["Rating"] <= target_rating].copy()

if is_goalie(target_position):
    eligible = eligible[eligible["Position"].map(is_goalie)]
else:
    eligible = eligible[~eligible["Position"].map(is_goalie)]

if selected_team and not roster_df.empty:
    current_team_names = set(roster_df.loc[roster_df["Team"] == selected_team, "Name"])
    eligible = eligible[~eligible["Name"].isin(current_team_names)]

st.caption(
    f"Showing {len(eligible)} eligible sub(s) at rating {format_rating(target_rating)} or below."
)
st.dataframe(eligible, width="stretch", hide_index=True)
