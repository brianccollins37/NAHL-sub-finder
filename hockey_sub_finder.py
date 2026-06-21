import streamlit as st
import pandas as pd
import datetime
import re

# =====================================================================
# CONFIGURATION
# Ensure Google Sheets are "Anyone with the link can view"
# Link format: .../export?format=csv&gid=0
# =====================================================================
LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/15mWSFY4vfarNrKh49SoXsOqCJFiUz8y68JGSemtVzv4/export?format=csv&gid=0"
    }
}

@st.cache_data(ttl=600)
def load_data(sub_url, roster_url):
    """Loads and merges the Sub list and Roster list."""
    try:
        # Load Sub Sheet
        df = pd.read_csv(sub_url)
        # Load Roster Sheet (if valid link)
        roster_df = pd.read_csv(roster_url) if "http" in roster_url else pd.DataFrame()
        
        # Standardize columns: Strip whitespace and ensure Proper Case
        for d in [df, roster_df]:
            d.columns = d.columns.str.strip().str.capitalize()
            
        # Merge if roster is available
        if not roster_df.empty and 'Name' in roster_df.columns:
            # Drop duplicates and merge by name
            roster_df = roster_df.drop_duplicates(subset=['Name'])
            df = df.merge(roster_df[['Name', 'Team']], on='Name', how='left', suffixes=('', '_roster'))
            if 'Team_roster' in df.columns:
                df['Team'] = df['Team_roster'].combine_first(df['Team'])
                df = df.drop(columns=['Team_roster'])
        
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

# =====================================================================
# UI
# =====================================================================
st.title("Hockey Sub Finder")

league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
df, err = load_data(LEAGUE_CONFIG[league]["Sub_Sheet"], LEAGUE_CONFIG[league]["Roster_Sheet"])

if err:
    st.error(f"Error loading data: {err}")
    st.stop()

# Ensure required columns exist
required = ['Name', 'Team', 'Rating', 'Position']
for col in required:
    if col not in df.columns:
        st.error(f"Missing column: {col}. Please check your Google Sheet headers.")
        st.stop()

# Roster-First Workflow
team_list = sorted([t for t in df['Team'].dropna().unique() if t != 'Unknown'])
selected_team = st.selectbox("Select Your Team", team_list)
team_roster = df[df['Team'] == selected_team]

missing_player = st.selectbox("Who are you replacing?", team_roster['Name'].tolist())
player_row = team_roster[team_roster['Name'] == missing_player].iloc[0]

st.info(f"Targeting: {missing_player} (Rating: {player_row['Rating']} | Pos: {player_row['Position']})")

# Filtering
# 1. Filter out own team
eligible = df[df['Team'] != selected_team]
# 2. Filter by Rating (Equal or Lower)
eligible = eligible[eligible['Rating'] <= player_row['Rating']]
# 3. Filter by Position (Goalie matches Goalie)
if 'Goalie' in str(player_row['Position']):
    eligible = eligible[eligible['Position'].astype(str).str.contains('G', case=False)]
else:
    eligible = eligible[~eligible['Position'].astype(str).str.contains('G', case=False)]

st.subheader(f"Eligible Subs ({len(eligible)})")
st.dataframe(eligible[['Name', 'Team', 'Rating', 'Position', 'Phone', 'Email']], use_container_width=True)
