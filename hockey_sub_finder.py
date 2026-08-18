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

# A dictionary to normalize common nicknames into formal names for perfect matching
NICKNAME_MAP = {
    "dan": "daniel", "danny": "daniel",
    "jim": "james", "jimmy": "james",
    "mike": "michael", "mikey": "michael",
    "tom": "thomas", "tommy": "thomas",
    "matt": "matthew",
    "dave": "david", "davy": "david",
    "chris": "christopher",
    "rob": "robert", "bob": "robert", "bobby": "robert", "robby": "robert",
    "rich": "richard", "rick": "richard", "ricky": "richard", "dick": "richard",
    "steve": "stephen", "steven": "stephen",
    "bill": "william", "billy": "william", "will": "william", "willy": "william",
    "ben": "benjamin", "benny": "benjamin",
    "joe": "joseph", "joey": "joseph",
    "jon": "jonathan", "johnny": "johnathan", "john": "johnathan",
    "greg": "gregory", "gregg": "gregory",
    "alex": "alexander",
    "zach": "zachary", "zack": "zachary",
    "nick": "nicholas", "nicky": "nicholas",
    "andy": "andrew", "drew": "andrew",
    "pat": "patrick", "patty": "patrick",
    "tim": "timothy", "timmy": "timothy",
    "ed": "edward", "eddie": "edward", "eddy": "edward",
    "phil": "philip", "phillip": "philip",
    "ken": "kenneth", "kenny": "kenneth",
    "ron": "ronald", "ronnie": "ronald",
    "jeff": "jeffrey", "geoff": "jeffrey",
    "tony": "anthony",
    "sam": "samuel", "sammy": "samuel",
    "josh": "joshua",
    "chuck": "charles", "charlie": "charles",
    "pete": "peter", "petey": "peter"
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

def get_player_key(name):
    """Reduces a name to just lowercase letters to guarantee matches, applying nickname rules."""
    name = clean_player_name(name)
    parts = str(name).lower().split(" ")
    if parts:
        # Check if the first name is in our nickname map
        first_name = parts[0]
        if first_name in NICKNAME_MAP:
            parts[0] = NICKNAME_MAP[first_name]
        # Rejoin the normalized name
        name = "".join(parts)
        
    return re.sub(r'[^a-z]', '', name)

def clean_text(value):
    value = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()

def value_matches(value, expected_value):
    return clean_text(value).upper() == clean_text(expected_value).upper()

def fuzzy_match_team(team_a, team_b):
    """
    Fuzzy matches teams by stripping all spaces/punctuation. 
    Includes SequenceMatcher to tolerate slight spelling typos (like Z vs S).
    """
    if pd.isna(team_a) or pd.isna(team_b) or not str(team_a).strip() or not str(team_b).strip():
        return False
        
    a_clean = re.sub(r'[^a-z0-9]', '', str(team_a).lower())
    b_clean = re.sub(r'[^a-z0-9]', '', str(team_b).lower())
    
    if not a_clean or not b_clean:
        return False
        
    if a_clean in b_clean or b_clean in a_clean:
        return True
        
    shorter = a_clean if len(a_clean) < len(b_clean) else b_clean
    longer = b_clean if len(a_clean) < len(b_clean) else a_clean
    
    prefix = longer[:len(shorter)]
    ratio = difflib.SequenceMatcher(None, shorter, prefix).ratio()
    
    return ratio > 0.85

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
        df = read_table_from_sheet(MASTER_SCHEDULE_URL, required_headers=["Date", "Time", "Rink", "Home", "Away"])
        
        # Strip invisible characters from dates just in case
        df['Clean_Date'] = df['Date'].apply(lambda x: re.sub(r'[^0-9/]', '', str(x)))
        
        search_date_1 = f"{target_date.month}/{target_date.day}"  
        search_date_2 = f"{target_date.strftime('%m/%d')}"        
        
        daily_games = df[df['Clean_Date'].isin([search_date_1, search_date_2])]
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

# Eligibility filter
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
    target_date = st.date_input("Game Date (For Schedule Check)", value=None, help="Select a date to see if subs are already scheduled for another game.")

check_schedule = False
if target_date:
    with col_sched:
        st.markdown("<br>", unsafe_allow_html=True)
        check_schedule = st.checkbox("Check Live Web Schedules", value=True)

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
    # Use the new get_player_key to ensure robust exclusion
    current_team_keys = set(roster_df.loc[roster_df["Team"] == selected_team, "Name"].apply(get_player_key))
    eligible = eligible[~eligible["Name"].apply(get_player_key).isin(current_team_keys)]

display_cols = ["Name", "Rating", "Position"]

if check_schedule and target_date:
    with st.spinner("Checking schedule overlaps..."):
        daily_games_df = get_daily_schedule(target_date)
        
    if not roster_df.empty and not daily_games_df.empty:
        # Create hyper-stripped player keys using the nickname dictionary
        player_teams = dict(zip(roster_df['Name'].apply(get_player_key), roster_df['Team']))
        
        captain_game_time = None
        if selected_team:
            for _, game in daily_games_df.iterrows():
                if fuzzy_match_team(selected_team, game['Home']) or fuzzy_match_team(selected_team, game['Away']):
                    raw_time = str(game['Time'])
                    clean_time = re.sub(r'[^a-zA-Z0-9:]', ' ', raw_time)
                    clean_time = re.sub(r'\s+', ' ', clean_time).strip()
                    
                    clean_rink = str(game['Rink']).strip()
                    captain_game_time = f"{clean_time} ({clean_rink})"
                    break
        
        if captain_game_time:
            st.info(f"📍 **Your Game Today:** {selected_team} plays at {captain_game_time}.")
        
        def get_game_status(player_name):
            p_key = get_player_key(player_name)
            team_name = player_teams.get(p_key)
            
            if not team_name:
                return "Free"
                
            for _, game in daily_games_df.iterrows():
                if fuzzy_match_team(team_name, game['Home']) or fuzzy_match_team(team_name, game['Away']):
                    raw_time = str(game['Time'])
                    clean_time = re.sub(r'[^a-zA-Z0-9:]', ' ', raw_time)
                    clean_time = re.sub(r'\s+', ' ', clean_time).strip()
                    
                    clean_rink = str(game['Rink']).strip()
                    return f"At Rink: {clean_time} ({clean_rink})"
                    
            return "Free"
            
        eligible["Schedule Status"] = eligible["Name"].apply(get_game_status)
    else:
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
