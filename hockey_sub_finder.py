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

@st.cache_data(ttl=600)
def load_data(sub_url):
    """
    Loads Sub Sheet with fuzzy column matching.
    """
    try:
        raw_df = pd.read_csv(sub_url, header=None)
        
        # 1. Find the header row
        header_idx = 0
        for i in range(min(15, len(raw_df))):
            row_str = " ".join(str(x).lower() for x in raw_df.iloc[i].values)
            if 'name' in row_str and 'rating' in row_str:
                header_idx = i
                break
        
        raw_df.columns = raw_df.iloc[header_idx]
        df = raw_df[header_idx + 1:].reset_index(drop=True)
        
        # 2. Fuzzy Column Mapping
        col_map = {str(c).strip().lower(): c for c in df.columns}
        
        def get_col(keywords):
            for k in keywords:
                for c in col_map:
                    if k in c: return col_map[c]
            return None

        # Build clean dataframe
        clean_df = pd.DataFrame()
        
        # Extract columns
        name_col = get_col(['name'])
        rating_col = get_col(['rating'])
        pos_col = get_col(['pos', 'position'])
        team_col = get_col(['team'])
        phone_col = get_col(['phone', 'cell'])
        email_col = get_col(['email'])
        
        clean_df['Name'] = df[name_col]
        clean_df['Rating'] = pd.to_numeric(df[rating_col].astype(str).str.extract(r'(\d+)', expand=False), errors='coerce').fillna(0)
        clean_df['Pos'] = df[pos_col] if pos_col else "F"
        clean_df['Team'] = df[team_col] if team_col else "Unknown"
        clean_df['Phone'] = df[phone_col] if phone_col else "N/A"
        clean_df['Email'] = df[email_col] if email_col else "N/A"
        
        return clean_df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

st.title("Hockey Sub Finder")

# 1. League Selection
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
df, error_msg = load_data(LEAGUE_CONFIG[league]["Sub_Sheet"])

if error_msg:
    st.error(f"Error loading sheet: {error_msg}")
    st.stop()

# 2. Safety check
if 'Name' not in df.columns:
    st.warning("Could not find a 'Name' column in your sheet. Please check the header names.")
    st.stop()

# 3. Roster Workflow
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
# Filter out current team
filtered_df = df[df['Team'] != selected_team] 
# Filter by rating (equal or lower)
filtered_df = filtered_df[filtered_df['Rating'] <= player_row['Rating']]
# Filter by position (simple contains)
filtered_df = filtered_df[filtered_df['Pos'].astype(str).str.contains(str(player_row['Pos'])[0], case=False)]

st.subheader(f"Eligible Subs ({len(filtered_df)})")
st.dataframe(filtered_df[['Name', 'Team', 'Rating', 'Pos', 'Phone', 'Email']], use_container_width=True)

st.caption("Contact BC at [brian.c.collins.37@gmail.com](mailto:brian.c.collins.37@gmail.com) if your league needs an update to use the system.")
