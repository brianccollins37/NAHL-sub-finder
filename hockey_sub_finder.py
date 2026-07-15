import datetime
from io import StringIO
import re

import pandas as pd
import requests
import streamlit as st

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

st.set_page_config(
    page_title="Hockey Sub Finder",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "League_Page": "https://www.nahlpgh-mgmt.com/page/show/9527885-nahl-nahl-54-",
        "Sub_Eligibility_Column": "NA",
        "Sub_Eligibility_Value": "Y",
    },
    "CVHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "League_Page": "https://www.nahlpgh-mgmt.com/page/show/9489537-cvhl-cvhl-18-",
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "League_Page": "https://www.nahlpgh-mgmt.com/page/show/9489545-ofhl-ofhl-17-",
    }
}

def is_placeholder_url(url):
    return not url or "YOUR_" in url

@st.cache_data(ttl=300)
def fetch_csv_text(url):
    if is_placeholder_url(url):
        raise ValueError("This sheet URL is still a placeholder.")

    verify = certifi.where() if certifi else True
    response = requests.get(url, timeout=20, verify=verify)
    response.raise_for_status()
    return response.text

def find_header_row(rows, required_headers):
    required = {header.lower() for header in required_headers}
    for index, row in enumerate(rows):
        normalized = {str(cell).strip().lower() for cell in row if str(cell).strip()}
        if required.issubset(normalized):
            return index
    return None

def read_table_from_sheet(url, required_headers):
    csv_text = fetch_csv_text(url)
    raw_rows = pd.read_csv(StringIO(csv_text), header=None, dtype=str).fillna("")
    header_row = find_header_row(raw_rows.values.tolist(), required_headers)

    if header_row is None:
        raise ValueError("Could not find a table header containing: " + ", ".join(required_headers))

    df = pd.read_csv(StringIO(csv_text), header=header_row, dtype=str).fillna("")
    df.columns = [str(column).strip() for column in df.columns]
    df = df.loc[:, [column for column in df.columns if not column.startswith("Unnamed")]]
    return df

def clean_player_name(name):
    name = clean_text(name)
    if "," not in name:
        return name
    last, first = [part.strip() for part in name.split(",", 1)]
    return f"{first} {last}".strip()

def clean_text(value):
    value = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()

def value_matches(value, expected_value):
    return clean_text(value).upper() == clean_text(expected_value).upper()

def normalize_subs(df):
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if c_lower in ['player rating', 'rating']: col_mapping[col] = 'Rating'
        elif c_lower in ['pos', 'position']: col_mapping[col] = 'Position'
        elif c_lower in ['first name']: col_mapping[col] = 'First Name'
        elif c_lower in ['last name']: col_mapping[col] = 'Last Name'
        elif c_lower in ['cell phone', 'phone', 'mobile']: col_mapping[col] = 'Phone'
        elif c_lower in ['email', 'e-mail']: col_mapping[col] = 'Email'
        elif c_lower in ['na', 'n/a']: col_mapping[col] = 'NA'

    df = df.rename(columns=col_mapping)
    required = ["Rating", "Position", "First Name", "Last Name"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Sub sheet is missing: " + ", ".join(missing))

    subs = df.copy()
    subs["Name"] = (subs["First Name"].map(clean_text) + " " + subs["Last Name"].map(clean_text)).map(clean_text)
    
    # Create Alpha-Only key for flawless cross-referencing
    subs["JoinKey"] = subs["Name"].apply(lambda x: re.sub(r'[^A-Z]', '', str(x).upper()))
    
    subs["Position"] = subs["Position"].map(clean_text)
    subs["Rating"] = pd.to_numeric(subs["Rating"], errors="coerce")
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns:
            subs[optional_column] = subs[optional_column].map(clean_text)

    subs = subs.dropna(subset=["Name", "Rating", "Position"])
    subs = subs[(subs["Name"] != "") & (subs["Position"] != "")]

    display_columns = ["Name", "Rating", "Position"]
    for optional_column in ["Email", "Phone", "NA"]:
        if optional_column in subs.columns: display_columns.append(optional_column)

    return subs[display_columns + ["JoinKey"]].sort_values(["Rating", "Name"], ascending=[False, True])

@st.cache_data(ttl=3600)
def get_web_rosters(league_page_url):
    """Scrapes SportsEngine using pure Regex to build a master roster of all teams."""
    if not league_page_url or is_placeholder_url(league_page_url):
        return pd.DataFrame()

    roster_list = []
    # Spoof headers to prevent SportsEngine from blocking the request as a bot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        verify = certifi.where() if certifi else True
        with requests.Session() as session:
            session.verify = verify
            session.headers.update(headers)
            
            base_resp = session.get(league_page_url, timeout=20)
            base_resp.raise_for_status()
            
            # Find the team links nested in the page
            match_children = re.search(r'<ul class="children" id="child_nodes">(.*?)</ul>', base_resp.text, re.DOTALL)
            if not match_children:
                return pd.DataFrame()
                
            team_links = re.findall(r'<a href="(/page/show/(\d+)[^"]*\?subseason=(\d+))"[^>]*>(.*?)</a>', match_children.group(1))
            
            for path, team_id, subseason_id, team_name in team_links:
                team_name_clean = team_name.replace('&amp;', '&').strip()
                roster_url = f"https://www.nahlpgh-mgmt.com/roster/show/{team_id}?subseason={subseason_id}"
                
                try:
                    r_resp = session.get(roster_url, timeout=15)
                    # Pure Regex to hunt for "Last, First" name structures inside HTML table rows
                    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', r_resp.text, re.DOTALL)
                    for row in rows:
                        clean_row = re.sub(r'<[^>]+>', ' ', row) # Strip HTML tags
                        # Match name formats like "Doe, John" or "O'Connor, Tim"
                        match = re.search(r'([A-Za-z\-\']+(?: [A-Za-z\-\']+)?,\s*[A-Za-z\-\']+(?: [A-Za-z\-\']+)?)', clean_row)
                        if match:
                            name = clean_player_name(match.group(1))
                            roster_list.append({
                                "Name": name,
                                "Team": team_name_clean,
                                "Position": "F" # Position defaults to F, Subs handle specific pos matching
                            })
                except Exception:
                    continue
    except Exception as e:
        return pd.DataFrame()

    df = pd.DataFrame(roster_list)
    return df.drop_duplicates() if not df.empty else df

@st.cache_data(ttl=600)
def get_web_schedule(league_page_url, target_date):
    """Scrapes SportsEngine via Regex to find the game schedule for a specific date."""
    schedule_map = {}
    if not league_page_url or is_placeholder_url(league_page_url):
        return schedule_map

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    try:
        verify = certifi.where() if certifi else True
        with requests.Session() as session:
            session.verify = verify
            session.headers.update(headers)
            
            base_resp = session.get(league_page_url, timeout=20)
            base_resp.raise_for_status()
            
            # Find the link to the daily schedule
            match_sched = re.search(r'href="(?:https?://[^/]+)?(/schedule/day/league_instance/\d+\?subseason=\d+)"', base_resp.text)
            if match_sched:
                sched_path = match_sched.group(1).replace('&amp;', '&')
                parts = sched_path.split('?')
                full_url = f"https://www.nahlpgh-mgmt.com{parts[0]}/{target_date.year}/{target_date.month}/{target_date.day}?{parts[1]}"
                
                sched_resp = session.get(full_url, timeout=20)
                # Regex out the game rows
                rows = re.findall(r'<tr id="game_list_row_[^>]*>(.*?)</tr>', sched_resp.text, re.DOTALL)
                for row in rows:
                    teams = re.findall(r'<a class="teamName"[^>]*>([^<]+)</a>', row)
                    if len(teams) >= 2:
                        visitor, home = teams[0].strip().upper(), teams[1].strip().upper()
                        
                        loc_match = re.search(r'<div class="scheduleListTeam">\s*([^<a]+?)\s*</div>', row)
                        location = loc_match.group(1).strip() if loc_match else "Rink"
                        
                        time_match = re.search(r'<span>([^<]+)</span>', row)
                        time_str = time_match.group(1).replace(' EDT', '').replace(' EST', '').strip() if time_match else "Game"
                        
                        status_str = f"{time_str} ({location})"
                        schedule_map[visitor] = status_str
                        schedule_map[home] = status_str
    except Exception:
        pass
        
    return schedule_map

def load_subs(url):
    df = read_table_from_sheet(url, required_headers=["First Name", "Last Name"])
    return normalize_subs(df)

def is_goalie(position):
    value = str(position).strip().upper()
    return value in {"G", "GOAL", "GOALIE", "GOALTENDER"} or value.startswith("GOAL")

def format_rating(value):
    return f"{float(value):g}"

st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))
config = LEAGUE_CONFIG[league]

try:
    subs_df = load_subs(config["Sub_Sheet"])
except Exception as error:
    st.error(f"Could not load the {league} sub sheet: {error}")
    st.stop()

# Eligibility filtering
eligibility_column = config.get("Sub_Eligibility_Column")
eligibility_value = config.get("Sub_Eligibility_Value")
if eligibility_column:
    if eligibility_column not in subs_df.columns:
        st.error(f"Could not find required `{eligibility_column}` column in {league} sub sheet.")
        st.stop()
    subs_df = subs_df[subs_df[eligibility_column].map(lambda value: value_matches(value, eligibility_value))].copy()

# Load Web Rosters
roster_error = None
with st.spinner(f"Syncing live rosters from the {league} website..."):
    raw_roster_df = get_web_rosters(config.get("League_Page"))

if not raw_roster_df.empty:
    roster_df = raw_roster_df.copy()
    roster_df['JoinKey'] = roster_df['Name'].apply(lambda x: re.sub(r'[^A-Z]', '', str(x).upper()))
    
    # Merge ratings from Sub Sheet
    rating_map = dict(zip(subs_df['JoinKey'], subs_df['Rating']))
    pos_map = dict(zip(subs_df['JoinKey'], subs_df['Position']))
    
    roster_df['Rating'] = roster_df['JoinKey'].map(rating_map).fillna(100.0)
    # Update positions to what they are classified as in the Sub Sheet (F/D/G/E)
    roster_df['Position'] = roster_df['JoinKey'].map(pos_map).fillna(roster_df['Position'])
    
    roster_df = roster_df.sort_values(["Team", "Rating", "Name"], ascending=[True, False, True])
else:
    roster_df = pd.DataFrame()
    roster_error = "Could not reach the SportsEngine League Page."

st.subheader("1. Select Missing Player")

if not roster_df.empty:
    team_list = sorted(roster_df["Team"].drop_duplicates())
    selected_team = st.selectbox("Select Team", team_list)

    team_roster = roster_df[roster_df["Team"] == selected_team].copy()
    team_roster = team_roster.sort_values(by=["Rating", "Name"], ascending=[False, True])
    
    team_roster["Label"] = team_roster.apply(
        lambda row: f"{row['Name']} - {row['Position']} - {format_rating(row['Rating'])}", axis=1
    )

    selected_label = st.selectbox("Missing Player", team_roster["Label"].tolist())
    player_row = team_roster[team_roster["Label"] == selected_label].iloc[0]
    target_rating = float(player_row["Rating"])
    target_position = player_row["Position"]

    st.info(f"Targeting: {player_row['Name']} (Rating: {format_rating(target_rating)} | Pos: {target_position})")
else:
    st.warning(f"Roster could not be loaded for {league}: {roster_error} Enter the missing player's rating and position manually.")
    selected_team = None
    target_rating = st.number_input("Missing Player Rating", min_value=0.0, value=100.0, step=1.0)
    target_position = st.selectbox("Missing Player Position", ["F", "D", "G", "E"])

st.subheader("2. Eligible Subs")

col_date, col_sched = st.columns(2)
with col_date:
    target_date = st.date_input("Game Date (For Schedule Check)", datetime.date.today())
with col_sched:
    st.markdown("<br>", unsafe_allow_html=True)
    check_schedule = st.checkbox("Check Live Web Schedules", value=True, help="Scrapes the league website to see if subs are already at the rink.")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    playoffs = st.checkbox("Playoffs Mode (Strictly Lower Rating)")
    rating_cutoff = target_rating - 1 if playoffs else target_rating
with col2:
    default_min = max(0.0, float(rating_cutoff) - 10.0)
    min_rating = st.number_input("Minimum Rating Filter", min_value=0.0, max_value=float(rating_cutoff), value=default_min, step=1.0)

eligible = subs_df[(subs_df["Rating"] <= rating_cutoff) & (subs_df["Rating"] >= min_rating)].copy()

if is_goalie(target_position):
    eligible = eligible[eligible["Position"].map(is_goalie)]
else:
    eligible = eligible[~eligible["Position"].map(is_goalie)]

if selected_team and not roster_df.empty:
    current_team_names = set(roster_df.loc[roster_df["Team"] == selected_team, "JoinKey"])
    eligible = eligible[~eligible["JoinKey"].isin(current_team_names)]

display_cols = ["Name", "Rating", "Position"]

if check_schedule:
    with st.spinner("Checking live web schedules..."):
        schedule_map = get_web_schedule(config.get("League_Page"), target_date)
        
    if not roster_df.empty:
        player_to_team = dict(zip(roster_df['JoinKey'], roster_df['Team']))
    else:
        player_to_team = {}
        
    def get_status(join_key):
        team = player_to_team.get(join_key)
        if not team: return "Free"
        game = schedule_map.get(team.upper())
        if game: return f"At Rink: {game} ({team.title()})"
        return "Free"
        
    eligible["Schedule Status"] = eligible["JoinKey"].map(get_status)
    display_cols.insert(1, "Schedule Status")

st.caption(f"Showing {len(eligible)} eligible sub(s) between {format_rating(min_rating)} and {format_rating(rating_cutoff)}.")

column_config = {}
if "NA" in eligible.columns: display_cols.append("NA")
if "Phone" in eligible.columns:
    display_cols.append("Phone")
    eligible["Send Text"] = eligible["Phone"].apply(lambda x: f"sms:{re.sub(r'[^0-9]', '', str(x))}" if pd.notna(x) and str(x).strip() else None)
    display_cols.append("Send Text")
    column_config["Send Text"] = st.column_config.LinkColumn("Text Link", display_text="💬 Text")
if "Email" in eligible.columns:
    display_cols.append("Email")
    eligible["Send Email"] = eligible["Email"].apply(lambda x: f"mailto:{str(x).strip()}" if pd.notna(x) and str(x).strip() else None)
    display_cols.append("Send Email")
    column_config["Send Email"] = st.column_config.LinkColumn("Email Link", display_text="📧 Email")

st.dataframe(eligible[display_cols], width="stretch", hide_index=True, column_config=column_config)
st.markdown("---")
sheet_view_link = config['Sub_Sheet'].replace("/export?format=csv&", "/edit?")
st.markdown(f"<div style='text-align: center;'><small><b>Need an exception?</b> <br> <a href='{sheet_view_link}' target='_blank'>View the full {league} Sub List source data</a></small></div>", unsafe_allow_html=True)
