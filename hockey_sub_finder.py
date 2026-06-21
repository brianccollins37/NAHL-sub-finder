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
# ⚙️ CONFIGURATION BLOCK
# Update these URLs at the start of each new season!
# =====================================================================
LEAGUE_CONFIG = {
    "NAHL": {
        # Ensure the URL ends with /export?format=csv&gid=0
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Seasons": {
            "Season 54": "https://www.nahlpgh-mgmt.com/page/show/9527885-nahl-nahl-54-",
            "Season 53": "https://www.nahlpgh-mgmt.com/page/show/9439981-nahl-nahl-53-"
        }
    },
    "CVHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Seasons": {
            "Current Season": "https://www.nahlpgh-mgmt.com/page/show/example_cvhl"
        }
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Seasons": {
            "Season 17": "https://www.nahlpgh-mgmt.com/page/show/9489545-ofhl-ofhl-17-"
        }
    }
}

# Scheduling rules: Track side games start on the hour/20/40. Road side games stagger by 10 mins.
TIME_SLOTS = {
    "8:00 PM (Track Side)": {"offset": 0},
    "8:10 PM (Road Side)": {"offset": 10},
    "9:20 PM (Track Side)": {"offset": 80},
    "9:30 PM (Road Side)": {"offset": 90},
    "10:40 PM (Track Side)": {"offset": 160},
    "10:50 PM (Road Side)": {"offset": 170}
}
# =====================================================================

@st.cache_data(ttl=600)
def load_data(league: str, sub_url: str, roster_url: str, check_schedules: bool):
    """
    Attempts to load live data using fuzzy column matching.
    Returns a tuple of (DataFrame, error_message).
    """
    try:
        # 1. Read the Sub Google Sheet
        sub_df = pd.read_csv(sub_url)
        
        # 2. Fuzzy Column Matching
        # Normalize columns to lowercase strings for easy searching
        col_map = {c: str(c).strip().lower() for c in sub_df.columns}
        sub_df = sub_df.rename(columns=col_map)
        cols = sub_df.columns
        
        def find_col(possible_names):
            for p in possible_names:
                for col in cols:
                    if p in col:
                        return col
            return None

        name_c = find_col(['name', 'player', 'sub'])
        rating_c = find_col(['rating', 'level', 'skill', 'score'])
        pos_c = find_col(['pos'])
        phone_c = find_col(['phone', 'cell', 'mobile', 'text'])
        email_c = find_col(['email', 'mail'])
        
        # Edge case: If they split First and Last name into two columns
        if not name_c:
            first_c = find_col(['first'])
            last_c = find_col(['last'])
            if first_c and last_c:
                sub_df['Name'] = sub_df[first_c].astype(str) + " " + sub_df[last_c].astype(str)
                name_c = 'Name'

        # Rename whatever we found to our standard internal names
        rename_dict = {}
        if name_c: rename_dict[name_c] = 'Name'
        if rating_c: rename_dict[rating_c] = 'Rating'
        if pos_c: rename_dict[pos_c] = 'Pos'
        if phone_c: rename_dict[phone_c] = 'Phone'
        if email_c: rename_dict[email_c] = 'Email'
        
        sub_df = sub_df.rename(columns=rename_dict)
        
        # Ensure we have the minimum required columns, filling missing ones safely
        required_cols = ['Name', 'Rating', 'Pos', 'Phone', 'Email', 'Team', 'Scheduled_Date', 'Scheduled_Time']
        for col in required_cols:
            if col not in sub_df.columns:
                sub_df[col] = "Unknown" if col in ['Team', 'Phone', 'Email'] else None
                if col == 'Scheduled_Time':
                    sub_df[col] = "Free"
        
        # Drop rows where Name is missing
        sub_df = sub_df.dropna(subset=['Name'])
        
        # Clean up Rating (Extracts just the numbers, handles cases like "92 (A)")
        # We wrap 'x' in str() to prevent 'expected string or bytes-like object, got float' errors
        sub_df['Rating'] = sub_df['Rating'].apply(lambda x: re.sub(r'\D', '', str(x)))
        sub_df['Rating'] = pd.to_numeric(sub_df['Rating'], errors='coerce').fillna(0)
        
        # Drop anyone who has a 0 rating (usually means the row was just notes/blank)
        sub_df = sub_df[sub_df['Rating'] > 0]
        
        # 3. Attempt to scrape the Roster/Schedule page if enabled
        if check_schedules and roster_url:
            try:
                # pandas read_html is incredibly powerful but brittle to website changes.
                web_tables = pd.read_html(roster_url)
                # Future expansion: Cross-reference 'web_tables' with 'sub_df' here.
                pass 
            except Exception as e:
                print(f"Schedule scrape bypassed or failed: {e}")
        
        return sub_df, None

    except Exception as e:
        # FALLBACK: Generate Mock Data if the Google Sheet URL is invalid/private
        mock_data = [
            {"Name": "Mike Smith", "Rating": 88, "Pos": "Forward", "Team": "Lumberjacks", "Phone": "(412) 555-0101", "Email": "mike.s@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "8:00 PM (Track Side)"},
            {"Name": "David Jones", "Rating": 85, "Pos": "Defense", "Team": "Ice Hogs", "Phone": "(412) 555-0102", "Email": "djones@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"},
            {"Name": "Chris Wilson", "Rating": 82, "Pos": "Forward", "Team": "Puck Hounds", "Phone": "(412) 555-0103", "Email": "cwilson@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "9:30 PM (Road Side)"},
            {"Name": "Dan Miller", "Rating": 92, "Pos": "Goalie", "Team": "Iron Lungs", "Phone": "(724) 555-0105", "Email": "brickwall@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"}
        ]
        return pd.DataFrame(mock_data), f"Failed to read live sheet. Showing Mock Data. Error: {str(e)}"

def calculate_status(row, our_date, our_time, check_schedules):
    """Determines the availability status of a player based on time offsets."""
    if not check_schedules:
        return "[!] Schedule Check Disabled"
    
    if row['Scheduled_Time'] == "Free" or pd.isna(row['Scheduled_Date']):
        return "[Free]"
    
    # If the dates don't match (and neither is None), they are free today
    if str(row['Scheduled_Date']) != str(our_date):
        return "[Free]"

    their_time = row['Scheduled_Time']
    
    if our_time in TIME_SLOTS and their_time in TIME_SLOTS:
        our_offset = TIME_SLOTS[our_time]['offset']
        their_offset = TIME_SLOTS[their_time]['offset']
        time_diff = abs(our_offset - their_offset)
        
        if time_diff == 0:
            return "[X] Unavailable (Exact Conflict)"
        elif time_diff < 80:
            return f"[X] Unavailable (Overlaps {their_time})"
        elif time_diff <= 100:
            return f"[~] At Rink ({their_time})"
        else:
            return f"[i] Playing at {their_time}"
            
    return "[?] Unknown Schedule"

st.title("Hockey Sub Finder")
st.markdown("Easily find eligible replacements for missing players by filtering ratings, positions, and schedules.")

col1, col2 = st.columns([1, 1])
with col1:
    league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
with col2:
    # Dynamically populate the season dropdown based on the selected league
    available_seasons = list(LEAGUE_CONFIG[league]["Seasons"].keys())
    season = st.selectbox("Season", available_seasons)

# Grab the correct URLs based on the user's dropdown choices
current_sub_url = LEAGUE_CONFIG[league]["Sub_Sheet"]
current_roster_url = LEAGUE_CONFIG[league]["Seasons"][season]

st.divider()

st.subheader("Match Parameters")

# Creating a nice 5-column layout for inputs
param_cols = st.columns(5)

with param_cols[0]:
    missing_rating = st.number_input("Missing Player Rating", min_value=40, max_value=110, value=85, step=1)

with param_cols[1]:
    missing_position = st.selectbox("Missing Position", ["Skater (F/D)", "Goalie"])

with param_cols[2]:
    our_game_date = st.date_input("Game Date", value=datetime.date.today())

with param_cols[3]:
    our_game_time = st.selectbox("Game Time & Rink", list(TIME_SLOTS.keys()), index=2)

with param_cols[4]:
    st.markdown("<br>", unsafe_allow_html=True) # Spacer to align toggles
    is_playoff_mode = st.toggle("Playoff Mode (Stricter Rating)", value=False)
    check_schedules = st.toggle("Check Web Schedules", value=True)

df, error_msg = load_data(league, current_sub_url, current_roster_url, check_schedules)

if error_msg:
    st.error(error_msg)

st.divider()

# 1. Position Filter
if missing_position == "Goalie":
    # Using str.contains to be forgiving of how they type it (e.g. "G", "Goalie", "Netminder")
    filtered_df = df[df['Pos'].astype(str).str.contains('G|Goalie', case=False, na=False)].copy()
else:
    filtered_df = df[~df['Pos'].astype(str).str.contains('G|Goalie', case=False, na=False)].copy()

# 2. Rating Filter
if is_playoff_mode:
    filtered_df = filtered_df[filtered_df['Rating'] < missing_rating]
else:
    filtered_df = filtered_df[filtered_df['Rating'] <= missing_rating]

# 3. Schedule Check
filtered_df['Status'] = filtered_df.apply(
    lambda row: calculate_status(row, our_game_date, our_game_time, check_schedules), axis=1
)

# Sort the dataframe so Free players are at the top, then At Rink, then Unavailable
def status_sort_key(status):
    if "[Free]" in status: return 1
    if "[~]" in status: return 2
    if "[!]" in status: return 3
    if "[i]" in status: return 4
    return 5

filtered_df['SortOrder'] = filtered_df['Status'].apply(status_sort_key)
filtered_df = filtered_df.sort_values(['SortOrder', 'Rating'], ascending=[True, False]).drop(columns=['SortOrder'])

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
