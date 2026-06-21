import streamlit as st
import pandas as pd
import datetime
import re

# Set up the page configuration
st.set_page_config(
    page_title="Hockey Sub Finder",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_NAHL_FLAT_ROSTER_CSV_URL_HERE", 
        "Schedule_Sheet": "YOUR_NAHL_SCHEDULE_CSV_URL_HERE"
    },
    "CVHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_CVHL_FLAT_ROSTER_CSV_URL_HERE",
        "Schedule_Sheet": "YOUR_CVHL_SCHEDULE_CSV_URL_HERE"
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_OFHL_FLAT_ROSTER_CSV_URL_HERE",
        "Schedule_Sheet": "YOUR_OFHL_SCHEDULE_CSV_URL_HERE"
    }
}

MOCK_ROSTER = [
    {"Name": "Brian Collins", "Team": "Goal Diggers", "Rating": 87, "Pos": "G"},
    {"Name": "Justin Kenepp", "Team": "Goal Diggers", "Rating": 104, "Pos": "D"},
    {"Name": "Mike OToole", "Team": "No Regretskys", "Rating": 95, "Pos": "F"},
    {"Name": "Tim Wilson", "Team": "No Regretskys", "Rating": 108, "Pos": "D"}
]

def normalize_name(name):
    """Standardizes names to help cross-reference sheets."""
    if pd.isna(name): return ""
    name = str(name).lower()
    name = re.sub(r'[^\w\s]', '', name)
    parts = name.split()
    parts.sort()
    return " ".join(parts)

@st.cache_data(ttl=600)
def load_data(league: str, sub_url: str, roster_url: str):
    """Loads and standardizes the Sub and Roster sheets."""
    
    # ---------------------------------------------------------
    # 1. Parse Roster Sheet (If available, otherwise Mock)
    # ---------------------------------------------------------
    try:
        if "YOUR_" not in roster_url:
            roster_df = pd.read_csv(roster_url)
            # Standardize columns dynamically
            r_cols = {c: str(c).strip().lower() for c in roster_df.columns}
            
            def find_r_col(keywords):
                for k in keywords:
                    for c in r_cols:
                        if k in str(c).lower(): return c
                return None
                
            r_name = find_r_col(['name', 'player'])
            r_team = find_r_col(['team'])
            r_rating = find_r_col(['rating', 'rate'])
            r_pos = find_r_col(['pos'])
            
            roster_df = roster_df.rename(columns={r_name: 'Name', r_team: 'Team', r_rating: 'Rating', r_pos: 'Pos'})
            roster_df['Norm_Name'] = roster_df['Name'].apply(normalize_name)
            
            # Create a quick dictionary to map a player's normalized name to their team
            team_map = dict(zip(roster_df['Norm_Name'], roster_df['Team']))
        else:
            roster_df = pd.DataFrame(MOCK_ROSTER)
            roster_df['Norm_Name'] = roster_df['Name'].apply(normalize_name)
            team_map = dict(zip(roster_df['Norm_Name'], roster_df['Team']))
    except Exception as e:
        roster_df = pd.DataFrame(MOCK_ROSTER)
        team_map = {}

    # ---------------------------------------------------------
    # 2. Parse Sub Sheet
    # ---------------------------------------------------------
    try:
        raw_df = pd.read_csv(sub_url, header=None)
        
        if raw_df.empty or any("html" in str(c).lower() for c in raw_df.iloc[0].values):
            raise ValueError("Sub Sheet is private. Must be 'Anyone with link can view'.")
            
        header_idx = 0
        name_keywords = ['name', 'first', 'last']
        rating_keywords = ['rating', 'level', 'skill', 'score', 'pts']
        
        # Smart Header Finder: Look for a row that actually has multiple columns of data
        for i in range(min(15, len(raw_df))):
            valid_cols = raw_df.iloc[i].dropna().astype(str).str.strip()
            valid_cols = valid_cols[valid_cols != ""]
            
            if len(valid_cols) >= 3: # Must have at least 3 valid columns to be a table header
                row_str = " ".join(valid_cols.str.lower())
                if any(k in row_str for k in name_keywords) and any(k in row_str for k in rating_keywords):
                    header_idx = i
                    break
                    
        raw_df.columns = raw_df.iloc[header_idx]
        sub_df = raw_df[header_idx + 1:].reset_index(drop=True)

        col_map = {c: str(c).strip().lower() for c in sub_df.columns}
        sub_df = sub_df.rename(columns=col_map)
        cols = sub_df.columns
        
        def find_col(possible_names):
            for p in possible_names:
                for col in cols:
                    if p in col: return col
            return None

        first_c = find_col(['first'])
        last_c = find_col(['last'])
        
        if first_c and last_c and first_c in sub_df.columns and last_c in sub_df.columns:
            sub_df['Name'] = sub_df[first_c].fillna('').astype(str).str.strip() + " " + sub_df[last_c].fillna('').astype(str).str.strip()
            sub_df['Name'] = sub_df['Name'].replace(r'^\s*$', pd.NA, regex=True)
        else:
            name_c = find_col(['name', 'sub'])
            if name_c:
                sub_df = sub_df.rename(columns={name_c: 'Name'})
            else:
                sub_df['Name'] = "Unknown"

        rating_c = find_col(['rating', 'level', 'skill', 'score'])
        pos_c = find_col(['pos'])
        phone_c = find_col(['cell', 'phone', 'mobile', 'text'])
        email_c = find_col(['email', 'mail'])

        rename_dict = {}
        if rating_c: rename_dict[rating_c] = 'Rating'
        if pos_c: rename_dict[pos_c] = 'Pos'
        if phone_c: rename_dict[phone_c] = 'Phone'
        if email_c: rename_dict[email_c] = 'Email'
        
        sub_df = sub_df.rename(columns=rename_dict)
        sub_df = sub_df.dropna(subset=['Name'])
        
        def extract_rating(val):
            match = re.search(r'\d+', str(val))
            return match.group() if match else 0
            
        sub_df['Rating'] = sub_df['Rating'].apply(extract_rating)
        sub_df['Rating'] = pd.to_numeric(sub_df['Rating'], errors='coerce').fillna(0)
        sub_df = sub_df[sub_df['Rating'] > 0]
        
        if sub_df.empty:
            raise ValueError("No valid players found after filtering. Check column names.")

        # Map Teams
        sub_df['Norm_Name'] = sub_df['Name'].apply(normalize_name)
        sub_df['Team'] = sub_df['Norm_Name'].map(team_map).fillna("Unknown")

        return sub_df, roster_df, None

    except Exception as e:
        # Failsafe mock data if the sub sheet entirely fails
        mock_data = [
            {"Name": "Mike Smith", "Rating": 88, "Pos": "Forward", "Team": "Lumberjacks", "Phone": "(412) 555-0101", "Email": "mike.s@example.com"},
            {"Name": "David Jones", "Rating": 85, "Pos": "Defense", "Team": "Ice Hogs", "Phone": "(412) 555-0102", "Email": "djones@example.com"}
        ]
        return pd.DataFrame(mock_data), roster_df, f"Showing Mock Data. Live read failed: {str(e)}"

st.title("Hockey Sub Finder")
st.markdown("Easily find eligible replacements for missing players by filtering ratings, positions, and schedules.")

league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))

current_sub_url = LEAGUE_CONFIG[league]["Sub_Sheet"]
current_roster_url = LEAGUE_CONFIG[league]["Roster_Sheet"]

sub_df, roster_df, error_msg = load_data(league, current_sub_url, current_roster_url)

if error_msg:
    st.error(error_msg)
    
if "YOUR_" in current_roster_url:
    st.info("Showing Mock Roster Data. Provide a Roster Google Sheet URL in the source code to see real teams.")

st.divider()

# ---------------------------------------------------------
# 1. Roster Selection Workflow
# ---------------------------------------------------------
st.subheader("1. Select Missing Player")

team_list = roster_df['Team'].dropna().unique().tolist()
team_list.sort()

col_team, col_player = st.columns(2)
with col_team:
    selected_team = st.selectbox("Your Team", team_list)

# Filter roster to just the selected team
team_roster = roster_df[roster_df['Team'] == selected_team]

with col_player:
    if not team_roster.empty:
        missing_player_name = st.selectbox("Missing Player", team_roster['Name'].tolist())
        # Grab the specific row for the missing player
        player_row = team_roster[team_roster['Name'] == missing_player_name].iloc[0]
        p_rating = pd.to_numeric(player_row['Rating'], errors='coerce')
        p_pos = str(player_row['Pos'])
    else:
        st.warning("No players found on this team.")
        missing_player_name = "Unknown"
        p_rating = 85
        p_pos = "Skater"

st.info(f"Targeting subs for **{missing_player_name}** (Rating: **{p_rating}** | Pos: **{p_pos}**)")

# ---------------------------------------------------------
# 2. Sub Filters & Display
# ---------------------------------------------------------
st.subheader("2. Sub Filters")

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    is_playoff_mode = st.toggle("Playoff Mode (Require strictly lower rating)", value=False)
with filter_col2:
    strict_position = st.toggle("Strict Position Match (Goalies ↔ Goalies)", value=True)

# Rating Filter
target_rating = p_rating - 1 if is_playoff_mode else p_rating
filtered_df = sub_df[sub_df['Rating'] <= target_rating].copy()

# Position Filter
if strict_position:
    is_goalie = "G" in p_pos.upper() or "GOALIE" in p_pos.upper()
    if is_goalie:
        filtered_df = filtered_df[filtered_df['Pos'].astype(str).str.contains('G|Goalie', case=False, na=False)]
    else:
        filtered_df = filtered_df[~filtered_df['Pos'].astype(str).str.contains('G|Goalie', case=False, na=False)]

# Own Team Exclusion
filtered_df = filtered_df[filtered_df['Team'] != selected_team]

# ---------------------------------------------------------
# 3. Hidden Schedule Feature
# ---------------------------------------------------------
with st.expander("Advanced: Schedule Conflict Tracking (Requires Setup)"):
    st.write("Configure the Schedule CSV URL in the code to enable automatic conflict detection.")
    check_schedules = st.toggle("Enable Schedule Tracking", value=False)
    if check_schedules:
        st.warning("Schedule tracking is currently disabled until a valid Schedule CSV is provided.")

# ---------------------------------------------------------
# Rendering Results
# ---------------------------------------------------------
filtered_df = filtered_df.sort_values(by='Rating', ascending=False).drop(columns=['Norm_Name'], errors='ignore')

st.subheader(f"Eligible Subs ({len(filtered_df)})")

if filtered_df.empty:
    st.warning("No eligible subs found for the current criteria.")
else:
    display_df = filtered_df[['Name', 'Team', 'Rating', 'Pos', 'Phone', 'Email']].copy()
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Player Name", width="medium"),
            "Team": st.column_config.TextColumn("Current Team", width="medium"),
            "Rating": st.column_config.NumberColumn("Rating", format="%d", width="small"),
            "Pos": st.column_config.TextColumn("Position", width="small"),
            "Phone": st.column_config.TextColumn("Phone"),
            "Email": st.column_config.TextColumn("Email")
        }
    )

st.divider()
st.caption("Contact BC at **[brian.c.collins.37@gmail.com](mailto:brian.c.collins.37@gmail.com)** if your league needs an update to use the system.")
