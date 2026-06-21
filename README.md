4. [cite_start]Go to share.streamlit.io, log in with GitHub, and click New App. [cite: 16]
5. [cite_start]Select your repository, type `hockey_sub_finder.py` as the Main file path, and click Deploy. [cite: 17]

## Data Formatting Notes
[cite_start]For the app to read your live Google Sheets seamlessly, ensure the sharing settings on the sheet are set to "Anyone with the link can view". [cite: 19]

[cite_start]In your `hockey_sub_finder.py` configuration block, ensure your URLs end with `/export?format=csv&gid=0` (the gid number at the end changes depending on which specific tab in the Google Sheet you are linking to). [cite: 20, 21]

### 1. The Roster Sheet
The roster sheet needs to be a "flat" database. [cite_start]Do not use merged cells, blank spacer rows, or split teams horizontally across the page. [cite: 23] [cite_start]Put all players in one continuous, vertical list. [cite: 24]

| Name | Team | Rating | Pos |
| :--- | :--- | :--- | :--- |
| Mike O'Toole | No Regretskys | 95 | F |
| Brian Collins | Goal Diggers | 87 | G |
| Justin Kenepp | Goal Diggers | 104 | D |
| Tim Wilson | No Regretskys | 108 | [cite_start]D | [cite: 28]

### 2. The Sub Sheet
[cite_start]The app is designed to natively parse the standard sub sheets provided by the league. [cite: 31] [cite_start]It intelligently skips the instructional text at the top and looks for a row containing names and ratings. [cite: 32] [cite_start]Ensure columns roughly match: First Name, Last Name, Player Rating, Position, Email, Cell Phone. [cite: 33]

### 3. The Schedule Sheet (Advanced/Optional)
[cite_start]To use the advanced schedule conflict tracking, format a Google Sheet tab like this (ensure the time format matches what is in your app's drop-down): [cite: 34, 35]

| Date | Time | Away Team | Home Team |
| :--- | :--- | :--- | :--- |
| 2026-06-25 | 8:00 PM (Track Side) | Goal Diggers | Puck Hounds |
| 2026-06-25 | 8:10 PM (Road Side) | Ice Hogs | [cite_start]Lumberjacks | [cite: 37]

## License
[cite_start]This project is licensed under the MIT License - see the LICENSE file for details. [cite: 38, 39]
"""

with open("hockey_sub_finder.md", "w") as f:
    f.write(markdown_content)
