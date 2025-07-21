
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title="Live Sports Arbitrage Scanner", layout="wide")
st.title("🏟️ Live Sports Arbitrage Scanner")

API_KEY = "your_api_key_here"  # Replace with real key
SPORTS_URL = "https://api.the-odds-api.com/v4/sports/?apiKey=" + API_KEY
ODDS_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds?regions=au,us,uk&markets=h2h&oddsFormat=decimal&apiKey=" + API_KEY

# Fetch sports list
@st.cache_data(ttl=600)
def get_supported_sports():
    try:
        response = requests.get(SPORTS_URL)
        response.raise_for_status()
        sports_data = response.json()
        return [s for s in sports_data if s["active"]]
    except Exception as e:
        st.error(f"Failed to fetch sports: {e}")
        return []

# Sidebar setup
sports_list = get_supported_sports()
sport_options = {s["title"]: s["key"] for s in sports_list}
selected_sport_title = st.sidebar.selectbox("Select Sport", list(sport_options.keys()))
selected_sport_key = sport_options[selected_sport_title]

min_profit = st.sidebar.slider("Minimum Arbitrage Profit (%)", 0.5, 10.0, 1.0, step=0.1)
time_frame = st.sidebar.selectbox(
    "Show Matches Within:",
    ("Next 7 Days", "Next 1 Month", "Next 3 Months", "Next 6 Months")
)
days_map = {"Next 7 Days": 7, "Next 1 Month": 30, "Next 3 Months": 90, "Next 6 Months": 180}
cutoff_date = datetime.utcnow() + timedelta(days=days_map[time_frame])

# Arbitrage calc
def calc_stake_split(o1, o2, total=100):
    s1 = total / (1 + (o1 / o2))
    s2 = total - s1
    return round(s1, 2), round(s2, 2)

def fetch_odds_for_sport(sport_key):
    try:
        url = ODDS_URL.format(sport=sport_key)
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching odds: {e}")
        return []

if st.button("🔍 Scan for Arbitrage Opportunities"):
    odds_data = fetch_odds_for_sport(selected_sport_key)
    matches = []

    for event in odds_data:
        try:
            h2h = {bm['title']: bm['markets'][0]['outcomes'] for bm in event['bookmakers'] if bm['markets']}
            if len(h2h) < 2:
                continue

            bm_list = list(h2h.items())
            for i in range(len(bm_list)):
                for j in range(i+1, len(bm_list)):
                    bm1, outcomes1 = bm_list[i]
                    bm2, outcomes2 = bm_list[j]

                    for o1 in outcomes1:
                        for o2 in outcomes2:
                            if o1['name'] == o2['name']:
                                continue
                            if o1['name'] == event['home_team']:
                                opp = event['away_team']
                            else:
                                opp = event['home_team']

                            stake1, stake2 = calc_stake_split(o1['price'], o2['price'])
                            profit = round(100 - (stake1 + stake2), 2)

                            if profit >= min_profit:
                                matches.append({
                                    "Match": f"{event['home_team']} vs {event['away_team']}",
                                    "Team 1": o1['name'],
                                    "Odds 1": o1['price'],
                                    "Bookmaker 1": bm1,
                                    "Team 2": o2['name'],
                                    "Odds 2": o2['price'],
                                    "Bookmaker 2": bm2,
                                    "Profit": profit,
                                    "Match Date": pd.to_datetime(event['commence_time']),
                                    "Stake 1 (%)": stake1,
                                    "Stake 2 (%)": stake2
                                })
        except:
            continue

    df = pd.DataFrame(matches)
    df = df[df["Match Date"] <= cutoff_date]
    df = df.sort_values(by="Profit", ascending=False)

    def pie_chart(row):
        fig, ax = plt.subplots()
        ax.pie([row["Stake 1 (%)"], row["Stake 2 (%)"]],
               labels=[row["Bookmaker 1"], row["Bookmaker 2"]],
               autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

    for _, row in df.iterrows():
        with st.expander(f"📅 {row['Match Date'].strftime('%Y-%m-%d')} | {row['Match']} — 💰 {row['Profit']}% profit"):
            st.write(f"**{row['Team 1']} ({row['Bookmaker 1']})** @ {row['Odds 1']}")
            st.write(f"**{row['Team 2']} ({row['Bookmaker 2']})** @ {row['Odds 2']}")
            st.write(f"**Recommended Stake Split:** {row['Stake 1 (%)']}% vs {row['Stake 2 (%)']}%")
            pie_chart(row)
