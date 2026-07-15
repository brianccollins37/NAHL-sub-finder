import datetime
from io import StringIO
import re

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
        "League_Page": "https://www.nahlpgh-mgmt.com/page/show/9527885-nahl-nahl-54-",
        "Sub_Eligibility_Column": "NA",
        "Sub_Eligibility_Value": "Y",
        "Team_Names": [
            "Hells Kitchen - Shane",
            "No Regretskys - Deemer",
            "VIP After Hours - Ruefle",
            "Disco Biscuits - Hilborn",
            "8 Ball - Stevo",
            "Goal Diggers - BC",
            "5 Hole Strut - Ulrich",
            "Funkytown - Murawski",
        ],
    },
    "CVHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/1nI3pRgXvVDeK7RPM7chCPAhOm4RvdVFq5C_QrZDsf-0/export?format=csv&gid=0",
        "League_Page": "https://www.nahlpgh-mgmt.com/page/show/9489537-cvhl-cvhl-18-",
        # No NA requirement for CVHL subs
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/19OdJi43MGv1yCEN3eU4qw6LPH5maZKVzRScZytnfJCk/export?format=csv&gid=0",
        "League_Page": "https://www.nahlpgh-mgmt.com/page/show/9489545-ofhl-ofhl-17-",
        # No NA requirement for OFHL subs
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
        raise ValueError(
            "Could not find a table header containing: "
            + ", ".join(required_headers)
        )

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


def team_signature(team_name):
    team_name = clean_text(team_name)
    parts = [part.strip() for part in team_name.split(" - ", 1)]
    team_part = re.sub(r"^\d+\s+", "", parts[0]).strip()

    if len(parts) == 1:
        return team_part.lower()

    return f"{team_part} - {parts[1]}".lower()


def canonicalize_team_name(team_name, canonical_team_names):
    team_name = clean_text(team_name)
    if not canonical_team_names:
        return team_name

    canonical_lookup = {clean_text(name): clean_text(name) for name in canonical_team_names}
    if team_name in canonical_lookup:
        return canonical_lookup[team_name]

    signature_lookup = {
        team_signature(name): clean_text(name)
        for name in canonical_team_names
    }
    return signature_lookup.get(team_signature(team_name), team_name)

def normalize_roster(df, canonical_team_names=None):
    # Fuzzy match columns
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if c_lower in ['player rating', 'rating']:
            col_mapping[col] = 'Rating'
        elif c_lower in ['pos', 'position']:
            col_mapping[col] = 'Position'
        elif c_lower in ['name', 'player']:
            col_mapping[col] = 'Name'
        elif c_lower in ['team']:
            col_mapping[col] = 'Team'

    df = df.rename(columns=col_mapping)
    
    required = ["Name", "Team", "Rating", "Position"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Roster sheet is missing: " + ", ".join(missing))

    roster = df[required].copy()
    roster["Name"] = roster["Name"].map(clean_player_name)
    roster["Team"] = roster["Team"].map(
        lambda team_name: canonicalize_team_name(team_name, canonical_team_names)
    )
    roster["Position"] = roster["Position"].map(clean_text)
    roster["Rating"] = pd.to_numeric(roster["Rating"], errors="coerce")
    roster = roster.dropna(subset=["Name", "Team", "Rating", "Position"])
    roster = roster[(roster["Name"] != "") & (roster["Team"] != "")]
    return roster.sort_values(["Team", "Rating", "Name"], ascending=[True, False, True])


def normalize_subs(df):
    # Fuzzy match columns for different leagues
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if c_lower in ['player rating', 'rating']:
            col_mapping[col] = 'Rating'
        elif c_lower in ['pos', 'position']:
            col_mapping[col] = 'Position'
        elif c_lower in ['first name']:
            col_mapping[col] = 'First Name'
        elif c_lower in ['last name']:
            col_mapping[col] = 'Last Name'
        elif c_lower in ['cell phone', 'phone', 'mobile']:
            col_mapping[col] = 'Phone'
        elif c_lower in ['email', 'e-mail']:
            col_mapping[col] = 'Email'
        elif c_lower in ['na', 'n/a']:
            col_mapping[col] = 'NA'

    df = df.rename(columns=col_mapping)

    required = ["Rating", "Position", "First Name", "Last Name"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Sub sheet is missing: " + ", ".join(missing))

    subs = df.copy()
    subs["Name"] = (
        subs["First Name"].map(clean_text)
        + " "
        + subs["Last Name"].map(clean_text)
    ).map(clean_text)
    subs["Position"] = subs["Position"].map(clean_text)
    subs["Rating"] = pd.to_numeric(subs["Rating"], errors="coerce")
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns:
            subs[optional_column] = subs[optional_column].map(clean_text)

    subs = subs.dropna(subset=["Name", "Rating", "Position"])
    subs = subs[(subs["Name"] != "") & (subs["Position"] != "")]

    display_columns = ["Name", "Rating", "Position"]
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns:
            display_columns.append(optional_column)

    return subs[display_columns].sort_values(["Rating", "Name"], ascending=[False, True])

@st.cache_data(ttl=600)
def get_daily_schedule(league_page_url, target_date, canonical_team_names):
    """Scrapes the SportsEngine schedule to find games on the target date."""
    if not league_page_url or is_placeholder_url(league_page_url):
        return {}

    try:
        verify = certifi.where() if certifi else True
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # 1. Fetch base page to find the underlying schedule URL for the season
        base_resp = requests.get(league_page_url, timeout=20, verify=verify, headers=headers)
        base_resp.raise_for_status()
        
        match = re.search(r'href="(?:https?://[^/]+)?(/schedule/day/league_instance/\d+\?subseason=\d+)"', base_resp.text)
        if not match:
            return {}
            
        sched_path = match.group(1).replace('&amp;', '&')
        parts = sched_path.split('?')
        
        # 2. Inject the specific Game Date into the schedule URL
        date_path = f"{parts[0]}/{target_date.year}/{target_date.month}/{target_date.day}?{parts[1]}"
        full_url = "https://www.nahlpgh-mgmt.com" + date_path
        
        # 3. Fetch the daily schedule HTML
        sched_resp = requests.get(full_url, timeout=20, verify=verify, headers=headers)
        sched_resp.raise_for_status()
        
        # 4. Use Pandas to parse the HTML table
        dfs = pd.read_html(StringIO(sched_resp.text))
        sched_df = None
        for df in dfs:
            if 'Visitor' in df.columns and 'Home' in df.columns and 'Location' in df.columns:
                sched_df = df
                break
                
        if sched_df is None:
            return {}
            
        # 5. Extract games and map to canonical team names
        schedule_map = {}
        for _, row in sched_df.iterrows():
            visitor = str(row.get('Visitor', '')).strip()
            home = str(row.get('Home', '')).strip()
            location = str(row.get('Location', '')).strip()
            status = str(row.get('Status', '')).replace(' EDT', '').replace(' EST', '').strip()
            
            if status == 'nan': status = 'Game'
            if location == 'nan': location = 'Unknown Rink'
            
            time_loc = f"{status} ({location})"
            
            v_canon = canonicalize_team_name(visitor, canonical_team_names)
            h_canon = canonicalize_team_name(home, canonical_team_names)
            
            schedule_map[v_canon] = time_loc
            schedule_map[h_canon] = time_loc
            
        return schedule_map
    except Exception as e:
        # Silently fail if web scraping breaks to prevent app crashes
        return {}


def load_roster(url, canonical_team_names=None):
    df = read_table_from_sheet(url, required_headers=["Name", "Team"])
    return normalize_roster(df, canonical_team_names)


def load_subs(url):
    df = read_table_from_sheet(url, required_headers=["First Name", "Last Name"])
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

# Rule check: Does this specific league enforce an Eligibility check?
eligibility_column = config.get("Sub_Eligibility_Column")
eligibility_value = config.get("Sub_Eligibility_Value")
if eligibility_column:
    if eligibility_column not in subs_df.columns:
        st.error(
            f"Could not find the required `{eligibility_column}` eligibility column "
            f"in the {league} sub sheet."
        )
        st.stop()

    subs_df = subs_df[
        subs_df[eligibility_column].map(
            lambda value: value_matches(value, eligibility_value)
        )
    ].copy()

roster_df = pd.DataFrame()
roster_error = None

try:
    roster_df = load_roster(config["Roster_Sheet"], config.get("Team_Names"))
except Exception as error:
    roster_error = error

st.subheader("1. Select Missing Player")

if not roster_df.empty:
    team_list = [
        team_name
        for team_name in config.get("Team_Names", sorted(roster_df["Team"].drop_duplicates()))
        if team_name in set(roster_df["Team"])
    ]
    selected_team = st.selectbox("Select Team", team_list)

    team_roster = roster_df[roster_df["Team"] == selected_team].copy()
    
    # EXPLICIT SORTING: Ensure highest rated players appear at the top of the dropdown
    team_roster = team_roster.sort_values(by=["Rating", "Name"], ascending=[False, True])
    
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
    target_position = st.selectbox("Missing Player Position", ["F", "D", "G", "E"])

st.subheader("2. Eligible Subs")

col_date, col_sched = st.columns(2)
with col_date:
    target_date = st.date_input("Game Date (For Schedule Check)", datetime.date.today())
with col_sched:
    st.markdown("<br>", unsafe_allow_html=True)
    check_schedule = st.checkbox("Check Live Web Schedules", value=True, help="Scrapes the league website to see if subs are already at the rink.")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    playoffs = st.checkbox("Playoffs Mode (Strictly Lower Rating)")
    rating_cutoff = target_rating - 1 if playoffs else target_rating

with col2:
    # Default min rating to 10 points below the max to prevent massive lists
    default_min = max(0.0, float(rating_cutoff) - 10.0)
    min_rating = st.number_input(
        "Minimum Rating Filter", 
        min_value=0.0, 
        max_value=float(rating_cutoff), 
        value=default_min, 
        step=1.0, 
        help="Narrow down your list so you aren't texting 100 people at once."
    )

# Apply both maximum and minimum rating filters
eligible = subs_df[(subs_df["Rating"] <= rating_cutoff) & (subs_df["Rating"] >= min_rating)].copy()

# The E (Either) position automatically matches Skaters since it isn't a goalie.
if is_goalie(target_position):
    eligible = eligible[eligible["Position"].map(is_goalie)]
else:
    eligible = eligible[~eligible["Position"].map(is_goalie)]

if selected_team and not roster_df.empty:
    current_team_names = set(roster_df.loc[roster_df["Team"] == selected_team, "Name"])
    eligible = eligible[~eligible["Name"].isin(current_team_names)]

display_cols = ["Name", "Rating", "Position"]

# Check Live Schedule
if check_schedule and not roster_df.empty:
    with st.spinner("Checking live web schedule..."):
        schedule_map = get_daily_schedule(config.get("League_Page"), target_date, config.get("Team_Names"))
        
    # Create quick lookup map for Player -> Team
    player_to_team = dict(zip(roster_df['Name'].str.upper(), roster_df['Team']))
    
    def get_status(player_name):
        team = player_to_team.get(str(player_name).upper())
        if not team:
            return "Free"
        
        game = schedule_map.get(team)
        if game:
            short_team = team.split(' - ')[0] # E.g., 'Hells Kitchen' instead of 'Hells Kitchen - Shane'
            return f"At Rink: {game} ({short_team})"
        return "Free"
        
    eligible["Schedule Status"] = eligible["Name"].map(get_status)
    display_cols.insert(1, "Schedule Status") # Put Schedule Status immediately after Name

st.caption(
    f"Showing {len(eligible)} eligible sub(s) between {format_rating(min_rating)} and {format_rating(rating_cutoff)}."
)

# Build interactive columns for 1-click mobile messaging
column_config = {}

if "NA" in eligible.columns:
    display_cols.append("NA")

if "Phone" in eligible.columns:
    display_cols.append("Phone")
    # Generate SMS links
    eligible["Send Text"] = eligible["Phone"].apply(
        lambda x: f"sms:{re.sub(r'[^0-9]', '', str(x))}" if pd.notna(x) and str(x).strip() else None
    )
    display_cols.append("Send Text")
    column_config["Send Text"] = st.column_config.LinkColumn("Text Link", display_text="💬 Text")

if "Email" in eligible.columns:
    display_cols.append("Email")
    # Generate Mailto links
    eligible["Send Email"] = eligible["Email"].apply(
        lambda x: f"mailto:{str(x).strip()}" if pd.notna(x) and str(x).strip() else None
    )
    display_cols.append("Send Email")
    column_config["Send Email"] = st.column_config.LinkColumn("Email Link", display_text="📧 Email")

# Display the interactive dataframe
st.dataframe(
    eligible[display_cols], 
    width="stretch", 
    hide_index=True,
    column_config=column_config
)

st.markdown("---")

# Convert the CSV export link back to a standard Google Sheets viewing link
sheet_view_link = config['Sub_Sheet'].replace("/export?format=csv&", "/edit?")

# Subtle link to the source data
st.markdown(
    f"<div style='text-align: center;'><small><b>Need an exception?</b> <br> "
    f"<a href='{sheet_view_link}' target='_blank'>View the full {league} Sub List source data</a></small></div>", 
    unsafe_allow_html=True
)
