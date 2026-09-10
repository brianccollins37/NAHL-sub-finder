import datetime
import difflib
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

MASTER_SCHEDULE_URL = "https://docs.google.com/spreadsheets/d/1wi75UkV9rdhvsys2dAVDG2n1B0bGznIE1wISeLoUBWM/export?format=csv&gid=0"

NICKNAME_MAP = {
    "dan": "daniel", "danny": "daniel", "jim": "james", "jimmy": "james",
    "bob": "robert", "rob": "robert", "bobby": "robert", "robby": "robert",
    "bill": "william", "billy": "william", "will": "william", "willie": "william",
    "mike": "michael", "mikey": "michael", "steve": "stephen", "steven": "stephen",
    "tom": "thomas", "tommy": "thomas", "matt": "matthew", "matty": "matthew",
    "chris": "christopher", "dave": "david", "davy": "david", "joe": "joseph",
    "joey": "joseph", "jon": "jonathan", "tim": "timothy", "timmy": "timothy",
    "ed": "edward", "eddie": "edward", "ben": "benjamin", "benny": "benjamin",
    "sam": "samuel", "sammy": "samuel"
}

def clean_text(value):
    value = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()

def normalize_name(name):
    clean = re.sub(r'[^a-zA-Z]', '', str(name).lower())
    for nick, real in NICKNAME_MAP.items():
        if clean.startswith(nick):
            clean = clean.replace(nick, real, 1)
            break
    return clean

def fuzzy_match_team(team1, team2):
    t1 = re.sub(r'[^a-z0-9]', '', str(team1).lower())
    t2 = re.sub(r'[^a-z0-9]', '', str(team2).lower())
    
    if not t1 or not t2:
        return False
    if t1 in t2 or t2 in t1:
        return True
        
    similarity = difflib.SequenceMatcher(None, t1, t2).ratio()
    return similarity > 0.85

@st.cache_data(ttl=300)
def fetch_csv_text(url):
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
    subs = df.copy()
    subs["Name"] = (subs["First Name"].map(clean_text) + " " + subs["Last Name"].map(clean_text)).map(clean_text)
    subs["JoinKey"] = subs["Name"].apply(normalize_name)
    subs["Rating"] = pd.to_numeric(subs["Rating"], errors="coerce")
    subs = subs.dropna(subset=["Name", "Rating", "Position"])
    
    display_columns = ["Name", "Rating", "Position"]
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns:
            display_columns.append(optional_column)
            
    return subs[display_columns + ["JoinKey"]].sort_values(["Rating", "Name"], ascending=[False, True]).copy()

def normalize_rosters(df):
    df = df.rename(columns=lambda x: str(x).strip())
    if "Position" not in df.columns and "Pos" in df.columns:
        df = df.rename(columns={"Pos": "Position"})
    
    roster = df.copy()
    
    def fix_name(name):
        name_str = str(name).strip()
        if "," in name_str:
            parts = name_str.split(",")
            if len(parts) >= 2:
                return f"{parts[1].strip()} {parts[0].strip()}"
        return name_str
        
    roster["Name"] = roster["Name"].apply(fix_name).map(clean_text)
    roster["JoinKey"] = roster["Name"].apply(normalize_name)
    roster["Rating"] = pd.to_numeric(roster["Rating"], errors="coerce")
    return roster.dropna(subset=["Name", "Rating"]).sort_values(["Team", "Rating", "Name"], ascending=[True, False, True]).copy()

@st.cache_data(ttl=300)
def get_daily_schedule(target_date):
    df = read_table_from_sheet(MASTER_SCHEDULE_URL, ["Date", "Time", "Home", "Away", "Rink"])
    
    date_str_1 = f"{target_date.month}/{target_date.day}"
    date_str_2 = f"{target_date.month:02d}/{target_date.day:02d}"
    date_str_3 = f"{target_date.year}-{target_date.month:02d}-{target_date.day:02d}"
    date_str_4 = f"{target_date.year}-{target_date.month}-{target_date.day}"
    
    today_games = df[
        (df["Date"] == date_str_1) | 
        (df["Date"] == date_str_2) |
        (df["Date"] == date_str_3) |
        (df["Date"] == date_str_4)
    ]
    
    schedule_map = {}
    for _, row in today_games.iterrows():
        home = str(row["Home"]).strip()
        away = str(row["Away"]).strip()
        raw_time = str(row["Time"])
        
        clean_time = re.sub(r'[^a-zA-Z0-9:]', ' ', raw_time)
        clean_time = re.sub(r'\s+', ' ', clean_time).strip()
        
        location = str(row["Rink"]).strip()
        time_loc = f"{clean_time} ({location})"
        
        if home: schedule_map[home] = time_loc
        if away: schedule_map[away] = time_loc
        
    return schedule_map

def load_subs(url): return normalize_subs(read_table_from_sheet(url, ["First Name", "Last Name"]))
def load_roster(url): return normalize_rosters(read_table_from_sheet(url, ["Name", "Team", "Rating"]))
def is_goalie(position): return str(position).strip().upper() in {"G", "GOAL", "GOALIE", "GOALTENDER"} or str(position).strip().upper().startswith("GOAL")
def format_rating(value): return f"{float(value):g}"

st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
config = LEAGUE_CONFIG[league]

try:
    subs_df = load_subs(config["Sub_Sheet"])
    roster_df = load_roster(config["Roster_Sheet"])
except Exception as error:
    st.error(f"Could not load the {league} sheets: {error}")
    st.stop()

eligibility_column = config.get("Sub_Eligibility_Column")
eligibility_value = config.get("Sub_Eligibility_Value")
if eligibility_column and eligibility_column in subs_df.columns:
    subs_df = subs_df[subs_df[eligibility_column].map(lambda value: clean_text(value).upper() == clean_text(eligibility_value).upper())].copy()

st.subheader("1. Select Missing Player")
team_list = sorted(roster_df["Team"].drop_duplicates())
selected_team = st.selectbox("Select Team", team_list)

team_roster = roster_df[roster_df["Team"] == selected_team].copy()
team_roster["Label"] = team_roster.apply(lambda row: f"{row['Name']} - {row['Position']} - {format_rating(row['Rating'])}", axis=1)

selected_label = st.selectbox("Missing Player", team_roster["Label"].tolist())
player_row = team_roster[team_roster["Label"] == selected_label].iloc[0]
target_rating = float(player_row["Rating"])
target_position = player_row["Position"]

st.info(f"Targeting: {player_row['Name']} (Rating: {format_rating(target_rating)} | Pos: {target_position})")

st.subheader("2. Eligible Subs")

target_date = st.date_input("Game Date (For Schedule Check)", value=None)
check_schedule = False
schedule_map = {}

if target_date:
    check_schedule = st.checkbox("Check Live Web Schedules", value=True, help="Scrapes the master schedule to see if subs are already at the rink.")
    if check_schedule:
        with st.spinner("Checking master schedule..."):
            schedule_map = get_daily_schedule(target_date)
            
            captain_game = None
            for sched_team, time_loc in schedule_map.items():
                if fuzzy_match_team(sched_team, selected_team):
                    captain_game = time_loc
                    break
            
            if captain_game:
                st.info(f"📍 **Your Game Today:** {selected_team} plays at {captain_game}.")

st.markdown("---")

rating_cutoff = target_rating

col1, _ = st.columns(2)
with col1:
    default_min = max(0.0, float(rating_cutoff) - 10.0)
    min_rating = st.number_input(
        "Minimum Rating Filter", 
        min_value=0.0, 
        max_value=float(rating_cutoff), 
        value=default_min, 
        step=1.0, 
        help="Narrow down your list so you aren't texting 100 people at once."
    )

eligible = subs_df[(subs_df["Rating"] <= rating_cutoff) & (subs_df["Rating"] >= min_rating)].copy()

if is_goalie(target_position):
    eligible = eligible[eligible["Position"].map(is_goalie)]
else:
    eligible = eligible[~eligible["Position"].map(is_goalie)]

current_team_keys = set(roster_df.loc[roster_df["Team"] == selected_team, "JoinKey"])
eligible = eligible[~eligible["JoinKey"].isin(current_team_keys)]

display_cols = ["Name", "Rating", "Position"]
player_to_team = dict(zip(roster_df['JoinKey'], roster_df['Team']))

def get_status(join_key):
    if not check_schedule: return ""
    team = player_to_team.get(join_key)
    if not team: return "Free"
    
    for sched_team, time_loc in schedule_map.items():
        if fuzzy_match_team(sched_team, team):
            return f"At Rink: {time_loc} ({team})"
    return "Free"

if check_schedule:
    eligible["Schedule Status"] = eligible["JoinKey"].map(get_status)
    display_cols.insert(1, "Schedule Status")

st.caption(f"Showing {len(eligible)} eligible sub(s) between {format_rating(min_rating)} and {format_rating(rating_cutoff)}.")

column_config = {}
if "NA" in eligible.columns: display_cols.append("NA")

if "Phone" in eligible.columns:
    display_cols.append("Phone")
    eligible["Send Text"] = eligible["Phone"].apply(lambda x: f"sms:{re.sub(r'[^0-9]', '', str(x))}" if pd.notna(x) and str(x).strip() else None)
    display_cols.append("Send Text")
    column_config["Send Text"] = st.column_config.LinkColumn("Text Link", display_text="Text")

if "Email" in eligible.columns:
    display_cols.append("Email")
    eligible["Send Email"] = eligible["Email"].apply(lambda x: f"mailto:{str(x).strip()}" if pd.notna(x) and str(x).strip() else None)
    display_cols.append("Send Email")
    column_config["Send Email"] = st.column_config.LinkColumn("Email Link", display_text="Email")

st.dataframe(eligible[display_cols], width="stretch", hide_index=True, column_config=column_config)

sheet_view_link = config['Sub_Sheet'].replace("/export?format=csv&", "/edit?")
st.markdown(f"<div style='text-align: center;'><small><b>Need an exception?</b> <br> <a href='{sheet_view_link}' target='_blank'>View the full {league} Sub List source data</a></small></div>", unsafe_allow_html=True)
