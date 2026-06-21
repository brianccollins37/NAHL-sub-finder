🏒 Hockey Sub Finder

A Streamlit web application designed to take the headache out of finding eligible substitute players for amateur adult hockey leagues (e.g., NAHL, CVHL, OFHL).

The app cross-references live sub lists (Google Sheets) with league schedules and rosters to ensure you find a player who matches your team's needs, fits the rating rules, and isn't already playing a game at the same time.

✨ Features

Dynamic Rating Rules: Filters subs based on the missing player's rating. Includes a "Playoff Mode" toggle for stricter rating requirements.

Position Filtering: Easily swap between searching for Skaters (Forwards/Defense) or Goalies.

Smart Schedule Checking: Calculates time offsets between games to flag players who have exact schedule conflicts, or highlights players who will already be "At the Rink" playing in an adjacent time slot.

Live Data Integration: Pulls sub data directly from published Google Sheets and scrapes team rosters from league webpages using Pandas.

Admin Settings UI: No hardcoding required! Change the target Google Sheet or Roster URLs directly from a collapsible sidebar in the app. Changes apply instantly to your session.

Failsafe Mock Data: If the app cannot reach the live URLs (due to permissions or network issues), it automatically loads realistic mock data so the app won't crash.

🛠️ Tech Stack

Python

Streamlit (for the frontend and hosting)

Pandas & lxml (for data manipulation and web scraping)

🚀 Running Locally

If you want to test or develop the app on your own machine:

Clone the repository:

git clone https://github.com/YOUR-USERNAME/hockey-sub-finder.git
cd hockey-sub-finder


Install the dependencies:
Make sure you have Python installed, then run:

pip install -r requirements.txt


Run the app:

streamlit run hockey_sub_finder.py


The app will open automatically in your default web browser.

☁️ Deploying to Streamlit Community Cloud

This app is designed to be hosted for free on Streamlit Community Cloud.

Ensure your repository contains hockey_sub_finder.py and requirements.txt.

Go to share.streamlit.io and log in with your GitHub account.

Click "New App".

Select your hockey-sub-finder repository.

Set the Main file path to hockey_sub_finder.py.

Click Deploy.

Important Note on Dependencies:
Ensure your requirements.txt file contains the following exactly, otherwise the live web-scraping will fail:

pandas
lxml


📊 Data Formatting Notes

For the app to read your live Google Sheets, ensure the sharing settings on the sheet are set to "Anyone with the link can view". The app currently expects columns for Player Name, Rating, Pos (Position), and Contact Information.

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
