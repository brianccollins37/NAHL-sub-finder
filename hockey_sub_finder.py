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
# Update these URLs at the start of each new season!
# Ensure all URLs end with /export?format=csv&gid=[YOUR_GID]
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

def normalize_name(name):
    """
    Standardizes names to help match between different sheets.
    Converts "O'Toole, Mike" and "Mike O'Toole" to "mike otoole".
    """
    if pd.isna(name): return ""
    name = str(name).lower()
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Split, sort alphabetically, and rejoin
    parts = name.split()
    parts.sort()
    return " ".join(parts)

@st.cache_data(ttl=600)
def load_data(league: str, sub_url: str, roster_url: str, schedule_url: str, check_schedules: bool, target_date: datetime.date):
    """
    Loads Sub, Roster, and Schedule data, merging them to determine availability.
    """
    try:
        # ==========================================
        # 1. Parse the Sub Sheet
        # ==========================================
        raw_df = pd.read_csv(sub_url, header=None)
        
        if raw_df.empty or any("html" in str(c).lower() for c in raw_df.iloc[0].values):
            raise ValueError("Sub Sheet is private or invalid.")
            
        header_idx = 0
        name_keywords = ['name', 'first', 'last']
        rating_keywords = ['rating', 'level', 'skill', 'score', 'pts']
        
        for i in range(min(15, len(raw_df))):
            row_str = " ".join(str(x).lower() for x in raw_df.iloc[i].values)
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
                    if p in col:
                        return col
            return None

        first_c = find_col(['first'])
        last_c = find_col(['last'])
        name_c = None
        
        if first_c and last_c:
            sub_df['Name'] = sub_df[first_c].fillna('').astype(str).str.strip() + " " + sub_df[last_c].fillna('').astype(str).str.strip()
            sub_df['Name'] = sub_df['Name'].replace(r'^\s*$', pd.NA, regex=True)
            name_c = 'Name'
        else:
            name_c = find_col(['name', 'sub'])

        rating_c = find_col(['rating', 'level', 'skill', 'score'])
        pos_c = find_col(['pos'])
        phone_c = find_col(['cell', 'phone', 'mobile', 'text'])
        email_c = find_col(['email', 'mail'])

        rename_dict = {}
        if name_c: rename_dict[name_c] = 'Name'
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
            raise ValueError("No valid players found after filtering.")

        # Default columns before applying cross-references
        sub_df['Team'] = "Unknown"
        sub_df['Scheduled_Time'] = "Free"
        
        # Add a normalized name column for merging
        sub_df['Norm_Name'] = sub_df['Name'].apply(normalize_name)

        # ==========================================
        # 2. Parse the Roster Sheet (if configured)
        # ==========================================
        if "YOUR_" not in roster_url:
            try:
                roster_df = pd.read_csv(roster_url)
                # Looking for standard columns: 'Name', 'Team'
                # Find columns using basic fuzzy matching
                r_cols = {str(c).lower(): c for c in roster_df.columns}
                r_name_c = next((r_cols[k] for k in r_cols if 'name' in k or 'player' in k), None)
                r_team_c = next((r_cols[k] for k in r_cols if 'team' in k), None)
                
                if r_name_c and r_team_c:
                    roster_df['Norm_Name'] = roster_df[r_name_c].apply(normalize_name)
                    # Create a dictionary mapping normalized name to team
                    team_map = dict(zip(roster_df['Norm_Name'], roster_df[r_team_c]))
                    # Apply team to sub_df where names match
                    sub_df['Team'] = sub_df['Norm_Name'].map(team_map).fillna("Unknown")
            except Exception as e:
                print(f"Failed to load rosters: {e}")

        # ==========================================
        # 3. Parse the Schedule Sheet (if configured)
        # ==========================================
        if check_schedules and "YOUR_" not in schedule_url:
            try:
                schedule_df = pd.read_csv(schedule_url)
                s_cols = {str(c).lower(): c for c in schedule_df.columns}
                
                s_date_c = next((s_cols[k] for k in s_cols if 'date' in k), None)
                s_time_c = next((s_cols[k] for k in s_cols if 'time' in k), None)
                # Assume home/away or team1/team2
                s_team_cols = [s_cols[k] for k in s_cols if 'team' in k or 'home' in k or 'away' in k]

                if s_date_c and s_time_c and len(s_team_cols) >= 2:
                    # Convert dates to match target_date
                    schedule_df[s_date_c] = pd.to_datetime(schedule_df[s_date_c], errors='coerce').dt.date
                    
                    # Filter for only games happening on our target date
                    todays_games = schedule_df[schedule_df[s_date_c] == target_date]
                    
                    # Build a dictionary mapping Team to their scheduled Time
                    time_map = {}
                    for _, game in todays_games.iterrows():
                        time_val = str(game[s_time_c]).strip()
                        # Clean up formatting (e.g. 8:00PM -> 8:00 PM)
                        time_val = re.sub(r'(?i)(am|pm)', r' \1', time_val).replace("  ", " ")
                        
                        team1 = str(game[s_team_cols[0]]).strip()
                        team2 = str(game[s_team_cols[1]]).strip()
                        time_map[team1] = time_val
                        time_map[team2] = time_val

                    # Assign Scheduled_Time to subs based on their assigned team
                    sub_df['Scheduled_Time'] = sub_df['Team'].map(time_map).fillna("Free")
            except Exception as e:
                print(f"Failed to load schedule: {e}")

        return sub_df, None

    except Exception as e:
        mock_data = [
            {"Name": "Mike Smith", "Rating": 88, "Pos": "Forward", "Team": "Lumberjacks", "Phone": "(412) 555-0101", "Email": "mike.s@example.com", "Scheduled_Time": "8:00 PM"},
            {"Name": "David Jones", "Rating": 85, "Pos": "Defense", "Team": "Ice Hogs", "Phone": "(412) 555-0102", "Email": "djones@example.com", "Scheduled_Time": "Free"},
            {"Name": "Chris Wilson", "Rating": 82, "Pos": "Forward", "Team": "Puck Hounds", "Phone": "(412) 555-0103", "Email": "cwilson@example.com", "Scheduled_Time": "9:30 PM"},
            {"Name": "Dan Miller", "Rating": 92, "Pos": "Goalie", "Team": "Iron Lungs", "Phone": "(724) 555-0105", "Email": "brickwall@example.com", "Scheduled_Time": "Free"}
        ]
        return pd.DataFrame(mock_data), f"Showing Mock Data. Live read failed: {str(e)}"

def calculate_status(row, our_time_str, check_schedules):
    """Determines the availability status of a player."""
    if not check_schedules:
        return "[!] Schedule Check Disabled"
    
    if row['Scheduled_Time'] == "Free":
        return "[Free]"

    their_time = str(row['Scheduled_Time']).upper()
    our_time_upper = our_time_str.upper()
    
    # Exact string match for time conflict
    if their_time == our_time_upper:
        return f"[X] Unavailable (Plays at {their_time})"
    else:
        return f"[i] Playing at {their_time}"

st.title("Hockey Sub Finder")
st.markdown("Easily find eligible replacements for missing players by filtering ratings, positions, and schedules.")

col1, col2 = st.columns([1, 1])
with col1:
    league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
with col2:
    st.info("Schedule tracking relies on configuring Flat Roster and Schedule Google Sheets in the source code.")

current_sub_url = LEAGUE_CONFIG[league]["Sub_Sheet"]
current_roster_url = LEAGUE_CONFIG[league]["Roster_Sheet"]
current_schedule_url = LEAGUE_CONFIG[league]["Schedule_Sheet"]

st.divider()

st.subheader("Match Parameters")

param_cols = st.columns(5)

with param_cols[0]:
    missing_rating = st.number_input("Missing Player Rating", min_value=40, max_value=400, value=85, step=1)

with param_cols[1]:
    missing_position = st.selectbox("Missing Position", ["Skater (F/D)", "Goalie"])

with param_cols[2]:
    our_game_date = st.date_input("Game Date", value=datetime.date.today())

with param_cols[3]:
    time_options = []
    for h in range(24):
        for m in range(0, 60, 5):
            period = "AM" if h < 12 else "PM"
            display_h = h % 12
            if display_h == 0: 
                display_h = 12
            time_options.append(f"{display_h}:{m:02d} {period}")
            
    default_idx = time_options.index("8:00 PM")
    formatted_time = st.selectbox("Our Game Time", time_options, index=default_idx)

with param_cols[4]:
    st.markdown("<br>", unsafe_allow_html=True)
    is_playoff_mode = st.toggle("Playoff Mode (Stricter Rating)", value=False)
    check_schedules = st.toggle("Check Sub Schedules", value=True)

df, error_msg = load_data(league, current_sub_url, current_roster_url, current_schedule_url, check_schedules, our_game_date)

if error_msg:
    st.error(error_msg)

st.divider()

if missing_position == "Goalie":
    filtered_df = df[df['Pos'].astype(str).str.contains('G|Goalie', case=False, na=False)].copy()
else:
    filtered_df = df[~df['Pos'].astype(str).str.contains('G|Goalie', case=False, na=False)].copy()

if is_playoff_mode:
    filtered_df = filtered_df[filtered_df['Rating'] < missing_rating]
else:
    filtered_df = filtered_df[filtered_df['Rating'] <= missing_rating]

filtered_df['Status'] = filtered_df.apply(
    lambda row: calculate_status(row, formatted_time, check_schedules), axis=1
)

def status_sort_key(status):
    if "[Free]" in status: return 1
    if "[~]" in status: return 2
    if "[!]" in status: return 3
    if "[i]" in status: return 4
    return 5

filtered_df['SortOrder'] = filtered_df['Status'].apply(status_sort_key)
filtered_df = filtered_df.sort_values(['SortOrder', 'Rating'], ascending=[True, False]).drop(columns=['SortOrder', 'Norm_Name'], errors='ignore')

st.subheader(f"Eligible Subs ({len(filtered_df)})")
st.caption(f"Filtering for {missing_position}s {'<' if is_playoff_mode else '<='} {missing_rating}")

if filtered_df.empty:
    st.warning("No eligible subs found for the current criteria. (Or the Google Sheet is empty/private!)")
else:
    display_df = filtered_df[['Name', 'Team', 'Rating', 'Pos', 'Status', 'Phone', 'Email']].copy()
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Player Name", width="medium"),
            "Team": st.column_config.TextColumn("Team", width="medium"),
            "Rating": st.column_config.NumberColumn("Rating", format="%d", width="small"),
            "Pos": st.column_config.TextColumn("Position", width="small"),
            "Status": st.column_config.TextColumn("Availability Status", width="large"),
            "Phone": st.column_config.TextColumn("Phone"),
            "Email": st.column_config.TextColumn("Email")
        }
    )

st.divider()
st.caption("Contact BC at **[brian.c.collins.37@gmail.com](mailto:brian.c.collins.37@gmail.com)** if your league needs an update to use the system.")
