
import streamlit as st
import requests
import pandas as pd

# ----- CONFIG -----
API_KEY = "979c4f7d8b58f830230296daa778327f"
REGION = "au"
MARKET = "h2h"

SPORT_KEYS = {
    "EPL (Soccer)": "soccer_epl",
    "NBA": "basketball_nba",
    "Tennis (ATP)": "tennis_atp",
    "AFL": "aussie_rules_afl",
    "UFC / MMA": "mma_mixed_martial_arts",
    "Cricket (T20I)": "cricket_international_t20"
}

st.set_page_config(page_title="Sports Arbitrage Scanner", layout="wide")
st.title("🏆 Live Sports Arbitrage Scanner")
st.caption("Scanning odds from SportsBet, TAB, Bet365, Ladbrokes, Dabble, Betfair (via TheOddsAPI)")

# ----- SIDEBAR FILTERS -----
st.sidebar.title("⚙️ Filters")
selected_league = st.sidebar.selectbox("Select League", ["All Leagues"] + list(SPORT_KEYS.keys()))
min_profit = st.sidebar.slider("Minimum Arbitrage Profit %", 0.0, 10.0, 1.0, step=0.1)

# ----- FETCH ODDS -----
@st.cache_data(ttl=60)
def fetch_sport_odds():
    urls = []
    if selected_league == "All Leagues":
        urls = [
            f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds?apiKey={API_KEY}&regions={REGION}&markets={MARKET}&oddsFormat=decimal"
            for sport_key in SPORT_KEYS.values()
        ]
    else:
        league_key = SPORT_KEYS[selected_league]
        urls = [
            f"https://api.the-odds-api.com/v4/sports/{league_key}/odds?apiKey={API_KEY}&regions={REGION}&markets={MARKET}&oddsFormat=decimal"
        ]

    all_data = []
    for url in urls:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                all_data.extend(r.json())
        except Exception as e:
            st.warning(f"Failed to fetch data from: {url}")
    return all_data

# ----- FIND ARBITRAGE -----
def detect_arbitrage(data):
    rows = []
    for event in data:
        match = f"{event['home_team']} vs {event['away_team']}"
        sport = event['sport_title']
        best_odds = {}

        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                for outcome in market["outcomes"]:
                    team = outcome["name"]
                    price = outcome["price"]
                    if team not in best_odds or price > best_odds[team]["price"]:
                        best_odds[team] = {
                            "price": price,
                            "bookmaker": bookmaker["title"]
                        }

        if len(best_odds) >= 2:
            inv_total = sum(1 / best_odds[t]["price"] for t in best_odds)
            arb_margin = (1 - inv_total) * 100
            if arb_margin >= min_profit:
                for team, info in best_odds.items():
                    rows.append({
                        "Sport": sport,
                        "Match": match,
                        "Team": team,
                        "Bookmaker": info["bookmaker"],
                        "Odds": info["price"],
                        "Arbitrage Profit %": round(arb_margin, 2)
                    })
    return pd.DataFrame(rows)

# ----- SCAN BUTTON -----
if st.button("🔍 Scan for Opportunities"):
    data = fetch_sport_odds()
    df = detect_arbitrage(data)

    if not df.empty:
        st.success(f"✅ {df['Match'].nunique()} Arbitrage Opportunities Found")
        st.dataframe(df.sort_values(by="Arbitrage Profit %", ascending=False), use_container_width=True)
    else:
        st.warning("No profitable arbitrage opportunities at this moment.")
else:
    st.info("Click the 'Scan for Opportunities' button to begin scanning odds.")
