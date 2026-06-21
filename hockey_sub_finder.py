import streamlit as st
import pandas as pd
import datetime
import re

st.set_page_config(page_title="Hockey Sub Finder", layout="wide")

# =====================================================================
# CONFIGURATION
# =====================================================================
LEAGUE_CONFIG = {
    "NAHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/1EG4O-c6YaAcij24OjtSFlyPNq9jKjYjSFIKSGZNfS7k/export?format=csv&gid=0",
        "Roster_Sheet": "https://docs.google.com/spreadsheets/d/15mWSFY4vfarNrKh49SoXsOqCJFiUz8y68JGSemtVzv4/export?format=csv&gid=0"
    },
    "OFHL": {
        "Sub_Sheet": "https://docs.google.com/spreadsheets/d/16MuuVSUj3RCyiDCkypRjA3B31cfe0VRaH-Fn4N4xfBg/export?format=csv&gid=0",
        "Roster_Sheet": "YOUR_OFHL_ROSTER_CSV_URL_HERE"
    }
}

def load_data(url):
    """
    Reads CSV and finds the header row dynamically.
    """
    # 1. Read raw CSV without headers
    raw_df = pd.read_csv(url, header=None)
    
    # 2. Find the row index that contains 'Name' (case-insensitive)
    header_row_idx = -1
    for i, row in raw_df.iterrows():
        row_str = " ".join(str(val).lower() for val in row.values)
        if 'name' in row_str:
            header_row_idx = i
            break
            
    if header_row_idx == -1:
        raise ValueError(f"Could not find 'Name' column. Found columns: {list(raw_df.iloc[0].values)}")

    # 3. Create clean dataframe
    df = pd.read_csv(url, skiprows=header_row_idx)
    df.columns = [str(c).strip().capitalize() for c in df.columns]
    
    # 4. Enforce required columns
    required = ['Name', 'Team', 'Rating', 'Position']
    for col in required:
        if col not in df.columns:
            # If Team is missing but not required for Sub List, create it
            if col == 'Team':
                df['Team'] = 'Unknown'
            else:
                raise ValueError(f"Missing required column: {col}. Available: {list(df.columns)}")
                
    return df

# =====================================================================
# UI
# =====================================================================
st.title("Hockey Sub Finder")
league = st.selectbox("League", list(LEAGUE_CONFIG.keys()))

try:
    df = load_data(LEAGUE_CONFIG[league]["Sub_Sheet"])
    
    # UI: Player Selection
    st.subheader("1. Select Missing Player")
    team_list = sorted(df['Team'].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list)
    
    team_roster = df[df['Team'] == selected_team]
    missing_player = st.selectbox("Missing Player", team_roster['Name'].tolist())
    player_row = team_roster[team_roster['Name'] == missing_player].iloc[0]
    
    st.info(f"Targeting: {missing_player} (Rating: {player_row['Rating']} | Pos: {player_row['Position']})")
    
    # Filters
    eligible = df[df['Team'] != selected_team]
    eligible = eligible[eligible['Rating'] <= player_row['Rating']]
    
    # Position logic
    if 'G' in str(player_row['Position']).upper():
        eligible = eligible[eligible['Position'].astype(str).str.contains('G', case=False)]
    else:
        eligible = eligible[~eligible['Position'].astype(str).str.contains('G', case=False)]

    st.subheader(f"Eligible Subs ({len(eligible)})")
    st.dataframe(eligible[['Name', 'Team', 'Rating', 'Position', 'Phone', 'Email']], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
```

### 2. Updated README
Save this as `README.md`. It explicitly notes the header requirements for your flat file.

```markdown:README.md
# 🏒 Hockey Sub Finder

A tool to help captains find eligible substitutes based on ratings, position, and team availability.

## 📝 Required Google Sheet Format
For the best results, use the "Flat File" format. Your sheet should have a continuous table without merged cells or extra instruction blocks at the top.

| Position | Name | Rating | Team | Email | Cell Phone |
| :--- | :--- | :--- | :--- | :--- | :--- |
| F | Buonomo, Frank | 108 | Hells Kitchen | email@test.com | 412-555-1234 |
| D | Stofka, Misho | 103 | Hells Kitchen | email@test.com | 412-555-5678 |

### Setup Instructions
1. **Prepare Sheet:** Create a tab in Google Sheets with the headers above.
2. **Publish:** Go to `File > Share > Publish to web`.
3. **Format:** Select `Comma-separated values (.csv)`.
4. **Copy Link:** Copy the resulting URL.
5. **Update Code:** Paste the link into `hockey_sub_finder.py` under the appropriate `LEAGUE_CONFIG` entry. 
   * *Note: Ensure your URL ends in `.../export?format=csv&gid=0`.*
