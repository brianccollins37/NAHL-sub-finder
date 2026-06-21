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

# =====================================================================
# CONFIGURATION BLOCK
# =====================================================================
LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/15mWSFY4vfarNrKh49SoXsOqCJFiUz8y68JGSemtVzv4/edit?usp=sharing", 
        "Schedule_Sheet": "YOUR_NAHL_SCHEDULE_CSV_URL_HERE"
    },
    "CVHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_CVHL_ROSTER_CSV_URL_HERE",
        "Schedule_Sheet": "YOUR_CVHL_SCHEDULE_CSV_URL_HERE"
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_OFHL_ROSTER_CSV_URL_HERE",
        "Schedule_Sheet": "YOUR_OFHL_SCHEDULE_CSV_URL_HERE"
    }
}

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).lower()
    name = re.sub(r'[^\w\s]', '', name)
    parts = name.split()
    parts.sort()
    return " ".join(parts)

@st.cache_data(ttl=600)
def load_data(league, sub_url, roster_url, schedule_url, check_schedules, target_date):
    try:
        # Load Sub Sheet
        raw_df = pd.read_csv(sub_url, header=None)
        header_idx = 0
        for i in range(min(15, len(raw_df))):
            row_str = " ".join(str(x).lower() for x in raw_df.iloc[i].values)
            if any(k in row_str for k in ['name', 'first']) and any(k in row_str for k in ['rating', 'score']):
                header_idx = i
                break
        raw_df.columns = raw_df.iloc[header_idx]
        sub_df = raw_df[header_idx + 1:].reset_index(drop=True)
        
        # Standardize Columns
        col_map = {str(c).strip().lower(): c for c in sub_df.columns}
        sub_df = sub_df.rename(columns={
            next((col_map[k] for k in col_map if 'first' in k), None): 'FirstName',
            next((col_map[k] for k in col_map if 'last' in k), None): 'LastName',
            next((col_map[k] for k in col_map if 'rating' in k), None): 'Rating',
            next((col_map[k] for k in col_map if 'pos' in k), None): 'Pos',
            next((col_map[k] for k in col_map if 'phone' in k), None): 'Phone',
            next((col_map[k] for k in col_map if 'email' in k), None): 'Email'
        })
        sub_df['Name'] = sub_df['FirstName'].astype(str) + " " + sub_df['LastName'].astype(str)
        sub_df['Norm_Name'] = sub_df['Name'].apply(normalize_name)
        sub_df['Rating'] = pd.to_numeric(sub_df['Rating'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        
        # Load Roster
        if "YOUR_" not in roster_url:
            roster_df = pd.read_csv(roster_url)
            r_col_map = {str(c).strip().lower(): c for c in roster_df.columns}
            team_map = dict(zip(roster_df[r_col_map['name']].apply(normalize_name), roster_df[r_col_map['team']]))
            sub_df['Team'] = sub_df['Norm_Name'].map(team_map).fillna("Unknown")
        else:
            sub_df['Team'] = "Unknown"
            
        return sub_df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
df, error_msg = load_data(league, LEAGUE_CONFIG[league]["Sub_Sheet"], LEAGUE_CONFIG[league]["Roster_Sheet"], LEAGUE_CONFIG[league]["Schedule_Sheet"], False, datetime.date.today())

if error_msg: st.error(f"Live read failed: {error_msg}")

# Ensure 'Team' column exists even if failed to load
if 'Team' not in df.columns: df['Team'] = "Unknown"

# Roster-First Workflow
team_list = df['Team'].dropna().unique().tolist()
selected_team = st.selectbox("Your Team", team_list)
team_roster = df[df['Team'] == selected_team]
missing_player = st.selectbox("Missing Player", team_roster['Name'].tolist())
player_row = team_roster[team_roster['Name'] == missing_player].iloc[0]

st.info(f"Targeting: **{missing_player}** (Rating: {player_row['Rating']} | Pos: {player_row['Pos']})")

filtered_df = df[df['Rating'] <= player_row['Rating']]
filtered_df = filtered_df[filtered_df['Team'] != selected_team]
st.dataframe(filtered_df[['Name', 'Team', 'Rating', 'Pos', 'Phone', 'Email']])

st.caption("Contact BC at [brian.c.collins.37@gmail.com](mailto:brian.c.collins.37@gmail.com) if your league needs an update to use the system.")
