import streamlit as st
import pandas as pd
import datetime

# Set up the page configuration
st.set_page_config(
    page_title="Hockey Sub Finder",
    page_icon="🏒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Scheduling rules: Track side games start on the hour/20/40. Road side games stagger by 10 mins.
TIME_SLOTS = {
    "8:00 PM (Track Side)": {"offset": 0},
    "8:10 PM (Road Side)": {"offset": 10},
    "9:20 PM (Track Side)": {"offset": 80},
    "9:30 PM (Road Side)": {"offset": 90},
    "10:40 PM (Track Side)": {"offset": 160},
    "10:50 PM (Road Side)": {"offset": 170}
}

# Initialize Session State for URLs (Admin Settings)
if 'urls' not in st.session_state:
    st.session_state.urls = {
        "NAHL_SUB": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "NAHL_ROSTER": "https://www.nahlpgh-mgmt.com/page/show/9527885-nahl-nahl-54-",
        "CVHL_SUB": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "CVHL_ROSTER": "https://www.nahlpgh-mgmt.com/page/show/example_cvhl",
        "OFHL_SUB": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "OFHL_ROSTER": "https://www.nahlpgh-mgmt.com/page/show/9489545-ofhl-ofhl-17-"
    }

# Admin Sidebar
with st.sidebar:
    st.header("⚙️ Admin Settings")
    st.write("Override default data URLs. Changes apply to your current session.")
    
    st.subheader("NAHL Links")
    st.session_state.urls["NAHL_SUB"] = st.text_input("NAHL Sub Sheet CSV", value=st.session_state.urls["NAHL_SUB"])
    st.session_state.urls["NAHL_ROSTER"] = st.text_input("NAHL Webpage", value=st.session_state.urls["NAHL_ROSTER"])
    
    st.subheader("CVHL Links")
    st.session_state.urls["CVHL_SUB"] = st.text_input("CVHL Sub Sheet CSV", value=st.session_state.urls["CVHL_SUB"])
    st.session_state.urls["CVHL_ROSTER"] = st.text_input("CVHL Webpage", value=st.session_state.urls["CVHL_ROSTER"])
    
    st.subheader("OFHL Links")
    st.session_state.urls["OFHL_SUB"] = st.text_input("OFHL Sub Sheet CSV", value=st.session_state.urls["OFHL_SUB"])
    st.session_state.urls["OFHL_ROSTER"] = st.text_input("OFHL Webpage", value=st.session_state.urls["OFHL_ROSTER"])

@st.cache_data(ttl=600)
def load_data(league: str, sub_url: str, roster_url: str, check_schedules: bool) -> pd.DataFrame:
    """
    Attempts to load live data. Falls back to mock data if it fails.
    """
    try:
        # 1. Read the Sub Google Sheet
        # The URL must end in /export?format=csv&gid=0 for Pandas to read it directly
        sub_df = pd.read_csv(sub_url)
        
        # Standardize standard column names to what the app expects
        rename_dict = {
            'Player Name': 'Name',
            'Player': 'Name',
            'Position': 'Pos',
            'Phone Number': 'Phone',
            'Email Address': 'Email'
        }
        sub_df = sub_df.rename(columns=rename_dict)
        
        # Ensure we have the minimum required columns, filling missing ones with blanks
        required_cols = ['Name', 'Rating', 'Pos', 'Phone', 'Email', 'Team', 'Scheduled_Date', 'Scheduled_Time']
        for col in required_cols:
            if col not in sub_df.columns:
                sub_df[col] = "Unknown" if col in ['Team', 'Phone', 'Email'] else None
                if col == 'Scheduled_Time':
                    sub_df[col] = "Free"
        
        # 2. Attempt to scrape the Roster/Schedule page if enabled
        if check_schedules and roster_url:
            try:
                web_tables = pd.read_html(roster_url)
                # In a real scenario, you'd inspect web_tables to find the exact index.
                # For now, we will just rely on the Sub Sheet data and mock schedule defaults.
                pass 
            except Exception as e:
                st.toast(f"Could not read schedule from website: {e}", icon="⚠️")
        
        # Drop rows where Name or Rating is missing
        sub_df = sub_df.dropna(subset=['Name', 'Rating'])
        
        # Ensure Rating is a number
        sub_df['Rating'] = pd.to_numeric(sub_df['Rating'], errors='coerce').fillna(0)
        
        return sub_df

    except Exception as e:
        # Show exactly what failed on the screen so we can debug it
        st.error(f"Failed to load live data for {league}. Ensure the Google Sheet is set to 'Anyone with link can view'. Error details: {e}")
        
        # FALLBACK: Generate Mock Data
        mock_data = [
            {"Name": "Mike Smith", "Rating": 88, "Pos": "Forward", "Team": "Lumberjacks", "Phone": "(412) 555-0101", "Email": "mike.s@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "8:00 PM (Track Side)"},
            {"Name": "David Jones", "Rating": 85, "Pos": "Defense", "Team": "Ice Hogs", "Phone": "(412) 555-0102", "Email": "djones@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"},
            {"Name": "Chris Wilson", "Rating": 82, "Pos": "Forward", "Team": "Puck Hounds", "Phone": "(412) 555-0103", "Email": "cwilson@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "9:30 PM (Road Side)"},
            {"Name": "Dan Miller", "Rating": 92, "Pos": "Goalie", "Team": "Iron Lungs", "Phone": "(724) 555-0105", "Email": "brickwall@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"}
        ]
        return pd.DataFrame(mock_data)

def calculate_status(row, our_date, our_time, check_schedules):
    """Determines the availability status of a player based on time offsets."""
    if not check_schedules:
        return "⚪ Schedule Check Disabled"
    
    if row['Scheduled_Time'] == "Free" or pd.isna(row['Scheduled_Date']):
        return "🟢 Free"
    
    # If the dates don't match (and neither is None), they are free today
    if str(row['Scheduled_Date']) != str(our_date):
        return "🟢 Free"

    their_time = row['Scheduled_Time']
    
    if our_time in TIME_SLOTS and their_time in TIME_SLOTS:
        our_offset = TIME_SLOTS[our_time]['offset']
        their_offset = TIME_SLOTS[their_time]['offset']
        time_diff = abs(our_offset - their_offset)
        
        if time_diff == 0:
            return "🔴 Unavailable (Exact Conflict)"
        elif time_diff < 80:
            return f"🔴 Unavailable (Overlaps {their_time})"
        elif time_diff <= 100:
            return f"🟡 At Rink ({their_time})"
        else:
            return f"🔵 Playing at {their_time}"
            
    return "⚪ Unknown Schedule"

st.title("🏒 Hockey Sub Finder")
st.markdown("Easily find eligible replacements for missing players by filtering ratings, positions, and schedules.")

col1, col2 = st.columns([1, 1])
with col1:
    league = st.selectbox("League", ["NAHL", "CVHL", "OFHL"])
with col2:
    season = st.selectbox("Season", ["Season 54", "Season 53", "Season 17 (OFHL)"])

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

# Load data based on league selection and current session state URLs
df = load_data(league, st.session_state.urls[f"{league}_SUB"], st.session_state.urls[f"{league}_ROSTER"], check_schedules)

st.divider()

# 1. Position Filter
if missing_position == "Goalie":
    filtered_df = df[df['Pos'] == "Goalie"].copy()
else:
    filtered_df = df[df['Pos'] != "Goalie"].copy()

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
    if "Free" in status: return 1
    if "At Rink" in status: return 2
    if "Schedule Check Disabled" in status: return 3
    if "Playing at" in status: return 4
    return 5

filtered_df['SortOrder'] = filtered_df['Status'].apply(status_sort_key)
filtered_df = filtered_df.sort_values(['SortOrder', 'Rating'], ascending=[True, False]).drop(columns=['SortOrder'])

st.subheader(f"Eligible Subs ({len(filtered_df)})")
st.caption(f"Filtering for {missing_position}s {'<' if is_playoff_mode else '<='} {missing_rating}")

if filtered_df.empty:
    st.warning("No eligible subs found for the current criteria.")
else:
    # Clean up the dataframe for display
    display_df = filtered_df[['Name', 'Team', 'Rating', 'Pos', 'Status', 'Phone', 'Email']].copy()
    
    # Configure columns for a better UI experience
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
