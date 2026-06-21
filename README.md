# NAHL Sub Finder

A Streamlit app for finding eligible substitute players for NAHL games using live Google Sheets data.

The app lets you select a team, choose the missing player from that team's roster, and then filters the sub list by rating and position so captains can quickly find valid replacement options.

## Current Status

NAHL is currently configured and active.

OFHL, CVHL, schedule conflict checking, and additional roster/schedule integrations are planned, but they are not active in the current version.

## Features

- Live Google Sheets data: Pulls the NAHL roster and sub list directly from published Google Sheets CSV URLs.
- Team and player selection: Uses the roster sheet to show the configured NAHL teams and the players on each team.
- Team name cleanup: Normalizes roster rows that contain numbered variants such as `10 Hole Strut - Ulrich` back to the configured team name, such as `5 Hole Strut - Ulrich`.
- Rating filtering: Shows subs whose rating is equal to or lower than the missing player's rating.
- Playoffs mode: When `Playoffs` is checked, eligible subs must be at least one rating point lower than the missing player.
- Position filtering: Goalie replacements only show goalies; skater replacements hide goalies.
- NAHL eligibility filtering: Only shows sub-list rows where the `NA` column is `Y`.
- Same-team exclusion: Removes players from the selected missing player's team from the eligible sub list.
- Contact fields: Displays available contact columns from the sub list, including email, phone, and NA eligibility.

## Tech Stack

- Python
- Streamlit
- Pandas
- Requests
- Certifi

## Running Locally

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/hockey-sub-finder.git
cd hockey-sub-finder
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run hockey_sub_finder.py
```

If you are using the fixed file generated during development, either rename `hockey_sub_finder_fixed.py` to `hockey_sub_finder.py`, or run:

```bash
streamlit run hockey_sub_finder_fixed.py
```

## Deploying to Streamlit Community Cloud

This app can be hosted on Streamlit Community Cloud.

1. Make sure the repository contains the app file and `requirements.txt`.
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click `New app`.
4. Select the repository.
5. Set the main file path to the app file, usually `hockey_sub_finder.py`.
6. Click `Deploy`.

If your app file is still named `hockey_sub_finder_fixed.py`, use that exact filename as the main file path or rename it before deploying.

## Requirements

The current `requirements.txt` should include:

```txt
streamlit
pandas
requests
certifi
```

`lxml` is not required for the current version because the app reads published CSV data instead of scraping HTML tables.

## Data Formatting Notes

The Google Sheets used by the app must be published or shared so Streamlit Community Cloud can read them.

The roster sheet should contain a table with these columns:

- `Position`
- `Name`
- `Rating`
- `Team`

The sub sheet should contain a table with these columns:

- `Player Rating`
- `Pos` or `Position`
- `First Name`
- `Last Name`
- `NA`

Optional sub sheet columns that will be displayed when present:

- `Email`
- `Cell Phone`

For NAHL, `NA` must be `Y` for the player to appear as an eligible sub.

The sheets may contain instruction rows above the actual player table. The app searches for the real header row before loading the table.

## Configuring Teams

NAHL team names are configured in the app under `LEAGUE_CONFIG["NAHL"]["Team_Names"]`.

Current configured teams:

- `Hells Kitchen - Shane`
- `No Regretskys - Deemer`
- `VIP After Hours - Ruefle`
- `Disco Biscuits - Hilborn`
- `8 Ball - Stevo`
- `Goal Diggers - BC`
- `5 Hole Strut - Ulrich`
- `Funkytown - Murawski`

Update this list if official team names change.

## Not Yet Included

The following items were mentioned in older documentation but are not currently active:

- OFHL and CVHL support
- Schedule conflict checking
- At-the-rink or adjacent-game indicators
- Admin settings UI
- Failsafe mock data
- HTML roster scraping with `lxml`

## License

This project is licensed under the MIT License if the repository includes an MIT `LICENSE` file.
