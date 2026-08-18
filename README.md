# 🏒 Hockey Sub Finder

A Streamlit app for finding eligible substitute players for league games using live Google Sheets data.

The app lets you select a team, choose the missing player from that team's roster, and then filters the sub list by rating, position, and real-time schedule conflicts so captains can quickly find valid replacement options.

## Current Status

**NAHL, CVHL, and OFHL** are currently configured and active.
**Schedule Conflict Checking** is active via a centralized Master Schedule Google Sheet.

## Features

- **Live Google Sheets Data:** Pulls league rosters, sub lists, and the master game schedule directly from published Google Sheets CSV URLs.
- **Dynamic Team and Player Selection:** Uses the roster sheets to dynamically show the configured teams and players for the selected league.
- **Schedule Overlap Detection:** Cross-references the target game date against the Master Schedule. Subs are automatically flagged as "At Rink: [Time] (Rink)" or "Free" based on their own team's schedule.
- **Captain's Game Context:** Automatically displays a banner showing the requesting captain's game time and rink location to make comparing adjacent game times easy.
- **Fuzzy Team Matching:** Smoothly handles slight variations in team names between the Roster Sheet and the Master Schedule (e.g., matching `Disco Biscuits - Hilborn` to `Disco Biscuits`).
- **Player Nickname Mapping:** Automatically reconciles common first name variations across different data sources (e.g., matching "Dan" to "Daniel" or "Jim" to "James") to guarantee players are recognized accurately.
- **Rating Filtering:** Shows subs whose rating is equal to or lower than the missing player's rating. Includes a customizable minimum rating filter to keep lists manageable.
- **Playoffs Mode:** When `Playoffs` is checked, eligible subs must be at least one rating point lower than the missing player.
- **Position Filtering:** Goalie replacements only show goalies; skater replacements hide goalies. Supports the "E" (Either F/D) position for CVHL and OFHL.
- **League-Specific Eligibility:** Automatically enforces NAHL-specific rules (requiring the `NA` column to be `Y`). CVHL and OFHL do not require this flag.
- **Same-Team Exclusion:** Removes players from the selected missing player's team from the eligible sub list.
- **Interactive Contact Buttons:** Displays 1-click `💬 Text` and `📧 Email` buttons inside the data table for quick mobile messaging.

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
