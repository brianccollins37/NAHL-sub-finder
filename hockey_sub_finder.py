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

# Configuration for Leagues
LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/15mWSFY4vfarNrKh49SoXsOqCJFiUz8y68JGSemtVzv4/export?format=csv&gid=0",
        "Schedule_Sheet": "YOUR_NAHL_SCHEDULE_CSV_URL_HERE"
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_OFHL_ROSTER_CSV_URL_HERE",
        "Schedule_Sheet": "YOUR_OFHL_SCHEDULE_CSV_URL_HERE"
    }
}

def load_data(url):
    """
    Loads data and forces headers to a standard format to avoid KeyErrors.
    """
    try:
        df = pd.read_csv(url)
        # Force column names to capitalized, stripped strings to match the app's expectations
        df.columns = [str(col).strip().capitalize() for col in df.columns]
        
        # Verify required columns exist
        required = ['Name', 'Team', 'Rating', 'Position']
        for col in required:
            if col not in df.columns:
                # If a column is missing, add it as empty to prevent crashes
                df[col] = "Unknown"
        return df
    except Exception as e:
        st.error(f"Error loading {url}: {e}")
        return pd.DataFrame()

# UI Setup
st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))

df = load_data(LEAGUE_CONFIG[league]["Sub_Sheet"])

if not df.empty:
    st.subheader("1. Select Missing Player")
    
    # Get unique teams for the dropdown
    team_list = sorted(df['Team'].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list)
    
    # Filter for the team
    team_roster = df[df['Team'] == selected_team]
    
    # Select player
    missing_player = st.selectbox("Missing Player", team_roster['Name'].tolist())
    player_row = team_roster[team_roster['Name'] == missing_player].iloc[0]
    
    st.info(f"Targeting: {missing_player} (Rating: {player_row['Rating']} | Pos: {player_row['Position']})")
    
    # Filtering Logic
    eligible = df[df['Team'] != selected_team]
    eligible = eligible[eligible['Rating'].astype(float) <= float(player_row['Rating'])]
    
    # Position logic
    is_goalie = 'G' in str(player_row['Position']).upper()
    if is_goalie:
        eligible = eligible[eligible['Position'].astype(str).str.contains('G', case=False)]
    else:
        eligible = eligible[~eligible['Position'].astype(str).str.contains('G', case=False)]

    st.subheader(f"Eligible Subs ({len(eligible)})")
    st.dataframe(eligible[['Name', 'Team', 'Rating', 'Position']], use_container_width=True)
else:
    st.warning("Data could not be loaded. Please check your Google Sheet format.")
