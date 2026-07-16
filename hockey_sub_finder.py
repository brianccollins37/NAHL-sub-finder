import datetime
from io import StringIO
import re

import pandas as pd
import requests
import streamlit as st

try:
    import certifi
except ImportError:
    certifi = None

st.set_page_config(
    page_title="Hockey Sub Finder",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MASTER_SCHEDULE_URL = "https://docs.google.com/spreadsheets/d/1wi75UkV9rdhvsys2dAVDG2n1B0bGznIE1wISeLoUBWM/export?format=csv&gid=0"

LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/15mWSFY4vfarNrKh49SoXsOqCJFiUz8y68JGSemtVzv4/export?format=csv&gid=0",
        "Sub_Eligibility_Column": "NA",
        "Sub_Eligibility_Value": "Y",
    },
    "CVHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/1nI3pRgXvVDeK7RPM7chCPAhOm4RvdVFq5C_QrZDsf-0/export?format=csv&gid=0",
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/19OdJi43MGv1yCEN3eU4qw6LPH5maZKVzRScZytnfJCk/export?format=csv&gid=0",
    }
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
        raise ValueError("Could not find a table header containing: " + ", ".join(required_headers))
    df = pd.read_csv(StringIO(csv_text), header=header_row, dtype=str).fillna("")
    df.columns = [str(column).strip() for column in df.columns]
    df = df.loc[:, [column for column in df.columns if not column.startswith("Unnamed")]]
    return df

def clean_player_name(name):
    name = clean_text(name)
    if "," not in name:
        return name
    last, first = [part.strip() for part in name.split(",", 1)]
    return f"{first} {last}".strip()

def clean_text(value):
    value = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()

def value_matches(value, expected_value):
    return clean_text(value).upper() == clean_text(expected_value).upper()

def fuzzy_match_team(team_a, team_b):
    """
    Fuzzy matches teams by stripping all spaces/punctuation and checking for substrings.
    Matches 'Disco Biscuits - Hilborn' to 'Disco Biscuits' perfectly.
    """
    if not team_a or not team_b:
        return False
    a_clean = re.sub(r'[^a-z0-9]', '', str(team_a).lower())
    b_clean = re.sub(r'[^a-z0-9]', '', str(team_b).lower())
    if not a_clean or not b_clean:
        return False
    return a_clean in b_clean or b_clean in a_clean

def normalize_roster(df):
    column_map = {
        "Position": "Position",
        "Pos": "Position",
        "Name": "Name",
        "Player": "Name",
        "Rating": "Rating",
        "Team": "Team",
    }
    df = df.rename(columns={col: column_map.get(str(col).strip(), col) for col in df.columns})
    required = ["Name", "Team", "Rating", "Position"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Roster sheet is missing: " + ", ".join(missing))

    roster = df[required].copy()
    roster["Name"] = roster["Name"].map(clean_player_name)
    roster["Position"] = roster["Position"].map(clean_text)
    roster["Rating"] = pd.to_numeric(roster["Rating"], errors="coerce")
    roster = roster.dropna(subset=["Name", "Team", "Rating", "Position"])
    roster = roster[(roster["Name"] != "") & (roster["Team"] != "")]
    return roster.sort_values(["Team", "Rating", "Name"], ascending=[True, False, True])

def normalize_subs(df):
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if c_lower in ['player rating', 'rating']: col_mapping[col] = 'Rating'
        elif c_lower in ['pos', 'position']: col_mapping[col] = 'Position'
        elif c_lower in ['first name']: col_mapping[col] = 'First Name'
        elif c_lower in ['last name']: col_mapping[col] = 'Last Name'
        elif c_lower in ['cell phone', 'phone', 'mobile']: col_mapping[col] = 'Phone'
        elif c_lower in ['email', 'e-mail']: col_mapping[col] = 'Email'
        elif c_lower in ['na', 'n/a']: col_mapping[col] = 'NA'

    df = df.rename(columns=col_mapping)
    required = ["Rating", "Position", "First Name", "Last Name"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Sub sheet is missing: " + ", ".join(missing))

    subs = df.copy()
    subs["Name"] = (subs["First Name"].map(clean_text) + " " + subs["Last Name"].map(clean_text)).map(clean_text)
    subs["Position"] = subs["Position"].map(clean_text)
    subs["Rating"] = pd.to_numeric(subs["Rating"], errors="coerce")
    
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns:
            subs[optional_column] = subs[optional_column].map(clean_text)

    subs = subs.dropna(subset=["Name", "Rating", "Position"])
    subs = subs[(subs["Name"] != "") & (subs["Position"] != "")]

    display_columns = ["Name", "Rating", "Position"]
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns: display_columns.append(optional_column)

    return subs[display_columns].sort_values(["Rating", "Name"], ascending=[False, True])

@st.cache_data(ttl=300)
def load_roster(url):
    df = read_table_from_sheet(url, required_headers=["Name", "Team"])
    return normalize_roster(df)

@st.cache_data(ttl=300)
def load_subs(url):
    df = read_table_from_sheet(url, required_headers=["First Name", "Last Name"])
    return normalize_subs(df)

@st.cache_data(ttl=300)
def get_daily_schedule(target_date):
    """Pulls the master schedule from Google Sheets and filters for the target date."""
    try:
        # Looking for columns: Date, Time, Rink, Home, Away
        df = read_table_from_sheet(MASTER_SCHEDULE_URL, required_headers=["Date", "Time", "Rink", "Home", "Away"])
        
        # The sheet date is M/D or MM/DD format without year.
        search_date_1 = f"{target_date.month}/{target_date.day}"  # e.g. 6/1
        search_date_2 = f"{target_date.strftime('%m/%d')}"        # e.g. 06/01
        
        # Filter down to just the games played on this date
        daily_games = df[df['Date'].str.strip().isin([search_date_1, search_date_2])]
        return daily_games
    except Exception as e:
        return pd.DataFrame()

def is_goalie(position):
    value = str(position).strip().upper()
    return value in {"G", "GOAL", "GOALIE", "GOALTENDER"} or value.startswith("GOAL")

def format_rating(value):
    return f"{float(value):g}"

# --- UI START ---
st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
config = LEAGUE_CONFIG[league]

# Load Subs
try:
    subs_df = load_subs(config["Sub_Sheet"])
except Exception as error:
    st.error(f"Could not load the {league} sub sheet: {error}")
    st.stop()

# Eligibility filter for NAHL
eligibility_column = config.get("Sub_Eligibility_Column")
eligibility_value = config.get("Sub_Eligibility_Value")
if eligibility_column:
    if eligibility_column not in subs_df.columns:
        st.error(f"Could not find required `{eligibility_column}` column in {league} sub sheet.")
        st.stop()
    subs_df = subs_df[subs_df[eligibility_column].map(lambda value: value_matches(value, eligibility_value))].copy()

# Load Rosters
roster_error = None
try:
    with st.spinner(f"Loading {league} rosters..."):
        roster_df = load_roster(config["Roster_Sheet"])
except Exception as error:
    roster_df = pd.DataFrame()
    roster_error = error

st.subheader("1. Select Missing Player")

if not roster_df.empty:
    team_list = sorted(roster_df["Team"].drop_duplicates())
    selected_team = st.selectbox("Select Team", team_list)

    team_roster = roster_df[roster_df["Team"] == selected_team].copy()
    team_roster = team_roster.sort_values(by=["Rating", "Name"], ascending=[False, True])
    
    team_roster["Label"] = team_roster.apply(
        lambda row: f"{row['Name']} - {row['Position']} - {format_rating(row['Rating'])}", axis=1
    )

    selected_label = st.selectbox("Missing Player", team_roster["Label"].tolist())
    player_row = team_roster[team_roster["Label"] == selected_label].iloc[0]
    target_rating = float(player_row["Rating"])
    target_position = player_row["Position"]

    st.info(f"Targeting: {player_row['Name']} (Rating: {format_rating(target_rating)} | Pos: {target_position})")
else:
    st.warning(f"Roster could not be loaded for {league}: {roster_error}")
    selected_team = None
    target_rating = st.number_input("Missing Player Rating", min_value=0.0, value=100.0, step=1.0)
    target_position = st.selectbox("Missing Player Position", ["F", "D", "G", "E"])

st.subheader("2. Eligible Subs")

col_date, col_sched = st.columns(2)
with col_date:
    target_date = st.date_input("Game Date", datetime.date.today())
with col_sched:
    st.markdown("<br>", unsafe_allow_html=True)
    check_schedule = st.checkbox("Check Master Schedule", value=True, help="Checks the Master Google Sheet to see if players have a game on this date.")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    playoffs = st.checkbox("Playoffs Mode (Strictly Lower Rating)")
    rating_cutoff = target_rating - 1 if playoffs else target_rating
with col2:
    default_min = max(0.0, float(rating_cutoff) - 10.0)
    min_rating = st.number_input("Minimum Rating Filter", min_value=0.0, max_value=float(rating_cutoff), value=default_min, step=1.0)

eligible = subs_df[(subs_df["Rating"] <= rating_cutoff) & (subs_df["Rating"] >= min_rating)].copy()

if is_goalie(target_position):
    eligible = eligible[eligible["Position"].map(is_goalie)]
else:
    eligible = eligible[~eligible["Position"].map(is_goalie)]

if selected_team and not roster_df.empty:
    current_team_names = set(roster_df.loc[roster_df["Team"] == selected_team, "Name"])
    eligible = eligible[~eligible["Name"].isin(current_team_names)]

display_cols = ["Name", "Rating", "Position"]

# Evaluate Schedule Overlaps
if check_schedule:
    with st.spinner("Checking schedule overlaps..."):
        daily_games_df = get_daily_schedule(target_date)
        
    if not roster_df.empty and not daily_games_df.empty:
        # Create a dictionary mapping Player Name -> Team Name
        player_teams = dict(zip(roster_df['Name'].apply(clean_text), roster_df['Team']))
        
        def get_game_status(player_name):
            p_name = clean_text(player_name)
            team_name = player_teams.get(p_name)
            
            if not team_name:
                return "Free"
                
            # Check if this team is playing today using fuzzy matching
            for _, game in daily_games_df.iterrows():
                if fuzzy_match_team(team_name, game['Home']) or fuzzy_match_team(team_name, game['Away']):
                    time = str(game['Time']).strip()
                    rink = str(game['Rink']).strip()
                    return f"At Rink: {time} ({rink})"
                    
            return "Free"
            
        eligible["Schedule Status"] = eligible["Name"].apply(get_game_status)
    else:
        # Fallback if no games are found or roster failed
        eligible["Schedule Status"] = "Free"
        
    display_cols.insert(1, "Schedule Status")

st.caption(f"Showing {len(eligible)} eligible sub(s) between {format_rating(min_rating)} and {format_rating(rating_cutoff)}.")

column_config = {}
if "NA" in eligible.columns: display_cols.append("NA")

if "Phone" in eligible.columns:
    display_cols.append("Phone")
    eligible["Send Text"] = eligible["Phone"].apply(
        lambda x: f"sms:{re.sub(r'[^0-9]', '', str(x))}" if pd.notna(x) and str(x).strip() else None
    )
    display_cols.append("Send Text")
    column_config["Send Text"] = st.column_config.LinkColumn("Text Link", display_text="💬 Text")

if "Email" in eligible.columns:
    display_cols.append("Email")
    eligible["Send Email"] = eligible["Email"].apply(
        lambda x: f"mailto:{str(x).strip()}" if pd.notna(x) and str(x).strip() else None
    )
    display_cols.append("Send Email")
    column_config["Send Email"] = st.column_config.LinkColumn("Email Link", display_text="📧 Email")

st.dataframe(eligible[display_cols], width="stretch", hide_index=True, column_config=column_config)

st.markdown("---")
sheet_view_link = config['Sub_Sheet'].replace("/export?format=csv&", "/edit?")
st.markdown(f"<div style='text-align: center;'><small><b>Need an exception?</b> <br> <a href='{sheet_view_link}' target='_blank'>View the full {league} Sub List source data</a></small></div>", unsafe_allow_html=True)
