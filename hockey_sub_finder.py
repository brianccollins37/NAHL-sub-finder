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
        "Roster_Sheet": "YOUR_NAHL_ROSTER_CSV_URL_HERE", 
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

@st.cache_data(ttl=600)
def load_data(league, sub_url):
    """
    Loads Sub Sheet with fuzzy column matching and guaranteed defaults.
    """
    try:
        raw_df = pd.read_csv(sub_url, header=None)
        
        # 1. Find the header row (skipping junk at the top of Google Sheets)
        header_idx = 0
        for i in range(min(15, len(raw_df))):
            row_str = " ".join(str(x).lower() for x in raw_df.iloc[i].values)
            if 'name' in row_str and ('rating' in row_str or 'pos' in row_str):
                header_idx = i
                break
        
        raw_df.columns = raw_df.iloc[header_idx]
        df = raw_df[header_idx + 1:].reset_index(drop=True)
        
        # 2. Fuzzy Column Mapping
        col_map = {str(c).strip().lower(): c for c in df.columns}
        
        # Mapping logic
        def get_col(keywords):
            for k in keywords:
                for c in col_map:
                    if k in c: return col_map[c]
            return None

        # Build clean dataframe
        clean_df = pd.DataFrame()
        
        # Name Logic
        first = get_col(['first'])
        last = get_col(['last'])
        name = get_col(['name'])
        if first and last:
            clean_df['Name'] = df[first].astype(str) + " " + df[last].astype(str)
        else:
            clean_df['Name'] = df[name]
            
        clean_df['Rating'] = pd.to_numeric(df[get_col(['rating'])], errors='coerce').fillna(0)
        clean_df['Pos'] = df[get_col(['pos', 'position'])]
        clean_df['Team'] = df[get_col(['team'])] if get_col(['team']) else "Unknown"
        clean_df['Phone'] = df[get_col(['phone', 'cell'])] if get_col(['phone', 'cell']) else "N/A"
        clean_df['Email'] = df[get_col(['email'])] if get_col(['email']) else "N/A"
        
        return clean_df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

st.title("Hockey Sub Finder")

# 1. League Selection
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
df, error_msg = load_data(league, LEAGUE_CONFIG[league]["Sub_Sheet"])

if error_msg:
    st.error(f"Error loading sheet: {error_msg}")

# 2. Safety check: Ensure columns exist before showing UI
if 'Name' not in df.columns:
    st.warning("Could not find a 'Name' column in your sheet. Please check the header names.")
    st.stop()

# 3. Roster-First Workflow
team_list = df['Team'].dropna().unique().tolist()
selected_team = st.selectbox("Your Team", team_list)
team_roster = df[df['Team'] == selected_team]

if team_roster.empty:
    st.warning("No players found for this team.")
    st.stop()

missing_player = st.selectbox("Missing Player", team_roster['Name'].tolist())
player_row = team_roster[team_roster['Name'] == missing_player].iloc[0]

st.info(f"Targeting: **{missing_player}** (Rating: {player_row['Rating']} | Pos: {player_row['Pos']})")

# 4. Filtering Logic
filtered_df = df[df['Rating'] <= player_row['Rating']] # Subs equal or lower
filtered_df = filtered_df[filtered_df['Team'] != selected_team] # Filter out own team
filtered_df = filtered_df[filtered_df['Pos'] == player_row['Pos']] # Only show same position

st.dataframe(filtered_df[['Name', 'Team', 'Rating', 'Pos', 'Phone', 'Email']], use_container_width=True)

st.caption("Contact BC at [brian.c.collins.37@gmail.com](mailto:brian.c.collins.37@gmail.com) if your league needs an update to use the system.")
