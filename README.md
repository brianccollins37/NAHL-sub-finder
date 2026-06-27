# 🏒 Hockey Sub Finder

A Streamlit app for finding eligible substitute players for league games using live Google Sheets data.

The app lets you select a team, choose the missing player from that team's roster, and then filters the sub list by rating and position so captains can quickly find valid replacement options.

## Current Status

**NAHL, CVHL, and OFHL** are currently configured and active.

Schedule conflict checking and additional web-based schedule integrations are planned, but they are not active in the current version.

## Features

- **Live Google Sheets data:** Pulls league rosters and sub lists directly from published Google Sheets CSV URLs.
- **Dynamic Team and Player Selection:** Uses the roster sheets to dynamically show the configured teams and players for the selected league.
- **Team Name Cleanup:** Normalizes roster rows that contain numbered variants such as `10 Hole Strut - Ulrich` back to the configured team name, such as `5 Hole Strut - Ulrich`.
- **Rating Filtering:** Shows subs whose rating is equal to or lower than the missing player's rating. Includes a customizable minimum rating filter to keep lists manageable.
- **Playoffs Mode:** When `Playoffs` is checked, eligible subs must be at least one rating point lower than the missing player.
- **Position Filtering:** Goalie replacements only show goalies; skater replacements hide goalies. Supports the "E" (Either F/D) position for CVHL and OFHL.
- **League-Specific Eligibility:** Automatically enforces NAHL-specific rules (requiring the `NA` column to be `Y`). CVHL and OFHL do not require this flag.
- **Same-Team Exclusion:** Removes players from the selected missing player's team from the eligible sub list.
- **Interactive Contact Buttons:** Displays 1-click `💬 Text` and `📧 Email` buttons inside the data table for quick mobile messaging.
- **Direct Source Links:** Provides a quick link at the bottom of the app directly to the active Google Sheet in case a captain needs to request a goalie exception from the commissioner.

## Tech Stack

- Python
- Streamlit
- Pandas
- Requests
- Certifi

## Running Locally

Clone the repository:

```bash
git clone [https://github.com/YOUR-USERNAME/hockey-sub-finder.git](https://github.com/YOUR-USERNAME/hockey-sub-finder.git)
cd hockey-sub-finder
