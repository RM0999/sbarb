
import streamlit as st
import requests
import pandas as pd

# ----- CONFIG -----
API_KEY = "979c4f7d8b58f830230296daa778327f"
REGION = "au"  # Australian bookmakers
MARKET = "h2h"

st.set_page_config(page_title="Sports Arbitrage Scanner", layout="wide")
st.title("🏆 Live Sports Arbitrage Scanner")
st.caption("Scanning odds from SportsBet, TAB, Bet365, Ladbrokes, Dabble, Betfair (via TheOddsAPI)")

# ----- DATA FETCH -----
@st.cache_data(ttl=60)
def fetch_odds():
    url = f"https://api.the-odds-api.com/v4/sports/upcoming/odds?apiKey={API_KEY}&regions={REGION}&markets={MARKET}&oddsFormat=decimal"
    r = requests.get(url)
    if r.status_code != 200:
        st.error(f"Error fetching data: {r.status_code} - {r.text}")
        return []
    return r.json()

data = fetch_odds()

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
            if arb_margin > 0:
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

# ----- DISPLAY RESULTS -----
df = detect_arbitrage(data)

if not df.empty:
    st.success(f"✅ {df['Match'].nunique()} Arbitrage Opportunities Found")
    st.dataframe(df.sort_values(by="Arbitrage Profit %", ascending=False), use_container_width=True)
else:
    st.warning("No profitable arbitrage opportunities at this moment.")
