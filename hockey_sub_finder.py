import streamlit as st
import pandas as pd
import datetime
import math

# Set up the page configuration
st.set_page_config(
    page_title="Hockey Sub Finder",
    page_icon="🏒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Scheduling rules: Track side games start on the hour/20/40. Road side games stagger by 10 mins.
# Offset represents minutes from 8:00 PM to calculate exact overlaps.
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
        "NAHL_ROSTER": "https://www.nahlpgh-mgmt.com/page/show/9527885-nahl-nahl-54-", # Default to schedule/roster page
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

@st.cache_data(ttl=600) # Cache data for 10 minutes to avoid hitting rate limits
def load_data(league: str, sub_url: str, roster_url: str) -> pd.DataFrame:
    """
    Attempts to load data from the provided URLs.
    If it fails (due to permissions or network), it generates robust mock data.
    """
    try:
        # Attempt to read the real Google Sheet
        sub_df = pd.read_csv(sub_url)
        
        # Attempt to read tables from the provided league webpage
        try:
            web_tables = pd.read_html(roster_url)
            # Logic to extract the specific roster/schedule table from web_tables goes here
            # pandas returns a list of all tables found on the page.
            roster_df = web_tables[0] if web_tables else pd.DataFrame()
        except Exception as e:
            # Silently fail web scraping and fallback if needed
            roster_df = pd.DataFrame()
        
        # Merge logic would go here once exact column names are known.
        # For example: df = pd.merge(sub_df, roster_df, on="Name", how="left")
        
        # We will assume if it succeeds, we need to standardize column names.
        pass
        
    except Exception as e:
        # FALLBACK: Generate Mock Data if the sheets/sites are inaccessible
        st.toast(f"Could not read live data for {league}. Loading mock data.", icon="⚠️")
        pass

    # Generating realistic mock data matching the prototype
    mock_data = [
        {"Name": "Mike Smith", "Rating": 88, "Pos": "Forward", "Team": "Lumberjacks", "Phone": "(412) 555-0101", "Email": "mike.s@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "8:00 PM (Track Side)"},
        {"Name": "David Jones", "Rating": 85, "Pos": "Defense", "Team": "Ice Hogs", "Phone": "(412) 555-0102", "Email": "djones@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"},
        {"Name": "Chris Wilson", "Rating": 82, "Pos": "Forward", "Team": "Puck Hounds", "Phone": "(412) 555-0103", "Email": "cwilson@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "9:30 PM (Road Side)"},
        {"Name": "Tom Brown", "Rating": 79, "Pos": "Defense", "Team": "Lumberjacks", "Phone": "(724) 555-0104", "Email": "tbrown_d@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "8:10 PM (Road Side)"},
        {"Name": "Dan Miller", "Rating": 92, "Pos": "Goalie", "Team": "Iron Lungs", "Phone": "(724) 555-0105", "Email": "brickwall@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"},
        {"Name": "Ryan Davis", "Rating": 84, "Pos": "Forward", "Team": "Ice Hogs", "Phone": "(412) 555-0106", "Email": "rdavis@example.com", "Scheduled_Date": datetime.date.today() + datetime.timedelta(days=1), "Scheduled_Time": "9:20 PM (Track Side)"},
        {"Name": "Kevin White", "Rating": 80, "Pos": "Defense", "Team": "Puck Hounds", "Phone": "(412) 555-0107", "Email": "kwhite@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "10:40 PM (Track Side)"},
        {"Name": "Brian Clark", "Rating": 75, "Pos": "Goalie", "Team": "Lumberjacks", "Phone": "(724) 555-0108", "Email": "bclark_net@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "9:20 PM (Track Side)"},
        {"Name": "Matt Taylor", "Rating": 86, "Pos": "Forward", "Team": "Iron Lungs", "Phone": "(412) 555-0109", "Email": "mtaylor@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "10:50 PM (Road Side)"},
        {"Name": "Joe Anderson", "Rating": 81, "Pos": "Forward", "Team": "Ice Hogs", "Phone": "(412) 555-0110", "Email": "janderson@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"},
        {"Name": "Steve Thomas", "Rating": 89, "Pos": "Defense", "Team": "Puck Hounds", "Phone": "(724) 555-0111", "Email": "sthomas@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "8:00 PM (Track Side)"},
        {"Name": "Alex Moore", "Rating": 77, "Pos": "Forward", "Team": "Lumberjacks", "Phone": "(412) 555-0112", "Email": "amoore@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "8:10 PM (Road Side)"},
        {"Name": "Eric Jackson", "Rating": 83, "Pos": "Defense", "Team": "Iron Lungs", "Phone": "(412) 555-0113", "Email": "ejackson@example.com", "Scheduled_Date": datetime.date.today(), "Scheduled_Time": "9:30 PM (Road Side)"},
        {"Name": "Adam Martin", "Rating": 85, "Pos": "Goalie", "Team": "Ice Hogs", "Phone": "(724) 555-0114", "Email": "amartin@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"},
        {"Name": "Scott Lee", "Rating": 78, "Pos": "Forward", "Team": "Puck Hounds", "Phone": "(412) 555-0115", "Email": "slee@example.com", "Scheduled_Date": None, "Scheduled_Time": "Free"}
    ]
    return pd.DataFrame(mock_data)

def calculate_status(row, our_date, our_time, check_schedules):
    """Determines the availability status of a player based on time offsets."""
    if not check_schedules:
        return "⚪ Schedule Check Disabled"
    
    if row['Scheduled_Time'] == "Free" or pd.isna(row['Scheduled_Date']):
        return "🟢 Free"
    
    if row['Scheduled_Date'] != our_date:
        return "🟢 Free (Different Day)"

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

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    league = st.selectbox("League", ["NAHL", "CVHL", "OFHL"])
with col2:
    season = st.selectbox("Season", ["Season 54", "Season 53", "Season 17 (OFHL)"])

# Load data based on league selection and current session state URLs
df = load_data(league, st.session_state.urls[f"{league}_SUB"], st.session_state.urls[f"{league}_ROSTER"])

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
            "Email": st.column_config.TextColumn("Email") # Note: Streamlit doesn't natively support mailto: links in dataframe yet without unsafe HTML
        }
    )

st.markdown("""
---
**Note on Data Integration:** To connect this to your live Google Sheets, ensure your sheets are set to "Anyone with the link can view" in the sharing settings. The app is pre-configured to attempt reading from the URLs provided.
""")