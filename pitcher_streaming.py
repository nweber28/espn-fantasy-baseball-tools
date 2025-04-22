import streamlit as st
import pandas as pd
import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz
from nltk.stem import SnowballStemmer
from unidecode import unidecode
import nltk

# --- Setup ---
nltk.download('punkt', quiet=True)
stemmer = SnowballStemmer('english')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants ---
EST = pytz.timezone('US/Eastern')
AVG_STARTER_IP = 5.5
AVG_PA_PER_INNING = 4.2
DEFAULT_PITCHER_PTS = 6.0
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json, text/plain, */*'
}
TEAM_MAP = {
    'CWS': 'CHW', 'SF': 'SFG', 'SD': 'SDP', 'WSH': 'WSN', 'WAS': 'WSN', 'TB': 'TBR',
    'KC': 'KCR', 'ANA': 'LAA', 'FLA': 'MIA', 'NYN': 'NYM', 'SLN': 'STL', 'LAN': 'LAD', 
    'SFN': 'SFG', 'AZ': 'ARI'
}
TEAM_IDS = {
    'LAA': 1, 'BAL': 2, 'BOS': 3, 'CHW': 4, 'CLE': 5, 'DET': 6, 'KCR': 7, 'MIN': 8,
    'NYY': 9, 'ATH': 10, 'SEA': 11, 'TBR': 12, 'TEX': 13, 'TOR': 14, 'ARI': 15,
    'ATL': 16, 'CHC': 17, 'CIN': 18, 'COL': 19, 'MIA': 20, 'HOU': 21, 'LAD': 22,
    'MIL': 23, 'WSN': 24, 'NYM': 25, 'PHI': 26, 'PIT': 27, 'STL': 28, 'SDP': 29,
    'SFG': 30
}

# --- Streamlit Config ---
st.set_page_config(page_title="Fantasy Baseball Analysis", page_icon="⚾", layout="wide")
st.title("Fantasy Baseball Analysis")
st.markdown("This application helps you analyze pitchers for fantasy baseball using ATC Rest-Of-Season projections.")
os.makedirs("data/cache", exist_ok=True)

# --- Utility Functions ---
def safe_get(url: str) -> Optional[Dict[str, Any]]:
    """Safe API request with error handling."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        if res.status_code != 200:
            logger.error(f"Request failed {res.status_code}: {url}")
            return None
        return res.json()
    except Exception as e:
        logger.error(f"Request exception: {e}")
        return None

def stem_name(name: str) -> str:
    """Standardize player name."""
    mappings = {'ben-williamson': 'benjamin-williamson', 'zach-dezenzo': 'zachary-dezenzo'}
    name = unidecode(name.lower().replace('.', '').replace(' ', '-'))
    return mappings.get(name, name)

def map_team_abbr(abbr: str) -> str:
    """Standardize team abbreviations."""
    return TEAM_MAP.get(abbr, abbr)

# --- Data Fetchers ---
@st.cache_data(ttl=3600)
def fetch_projections(player_type: str) -> pd.DataFrame:
    """Fetch and process projections."""
    urls = {
        'batter': "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=bat&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C1%2C0%2C0%2C0%2C0%2C0%2C0%2C1%2C2%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0",
        'pitcher': "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=pit&players=&proj=ratcdc&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    }
    data = safe_get(urls[player_type])
    if not data:
        return pd.DataFrame()

    records = []
    for player in data.get('data', []):
        if player_type == 'pitcher' and player.get("POS") not in ["SP", "RP"]:
            continue
        name = player.get("PlayerName", "")
        proj_pts = float(player.get("rPTS", 0))
        record = {
            "Name": name,
            "StemmedName": stem_name(name),
            "Team": player.get("Team", ""),
            "Pos": player.get("POS", ""),
            "ProjPts": proj_pts
        }
        if player_type == 'batter':
            pa = float(player.get("PA", 0))
            record.update({"PA": pa, "PtsPerPA": proj_pts / pa if pa else 0})
        else:
            ip = float(player.get("IP", 0))
            record.update({"IP": ip, "PtsPerIP": proj_pts / ip if ip else 0})
        records.append(record)
    return pd.DataFrame(records)

@st.cache_data(ttl=3600)
def fetch_schedule(date: str) -> Optional[Dict[str, Any]]:
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&leagueId=103,104&hydrate=team,linescore,flags,liveLookin,review&useLatestGames=false&language=en"
    return safe_get(url)

@st.cache_data(ttl=3600)
def fetch_game_feed(game_id: int) -> Optional[Dict[str, Any]]:
    return safe_get(f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live")

@st.cache_data(ttl=3600)
def fetch_team_lineup(team_id: int) -> Optional[List[Dict[str, Any]]]:
    url = f"https://www.fangraphs.com/api/depth-charts/past-lineups?teamid={team_id}&loaddate={int(datetime.now().timestamp())}"
    return safe_get(url)

# --- Data Processing ---
def analyze_team_batting(batters: pd.DataFrame) -> pd.DataFrame:
    if batters.empty:
        return pd.DataFrame()

    results = []
    for team, team_id in TEAM_IDS.items():
        lineups = fetch_team_lineup(team_id)
        if not lineups:
            continue

        pts, count = 0, 0
        player_stats = {}
        
        for game in lineups:
            players = [p for p in game.get('dataPlayers', []) 
                      if p.get('playerName') and p.get('valueOverride') not in ['INJ', 'AAA']]
            
            for p in players:
                name = p['playerName']
                stemmed_name = stem_name(name)
                match = batters[batters['StemmedName'] == stemmed_name]
                if not match.empty:
                    pts_per_pa = match['PtsPerPA'].iloc[0]
                    pts += pts_per_pa
                    count += 1
                    
                    if name not in player_stats:
                        player_stats[name] = {
                            'pos': match['Pos'].iloc[0],
                            'pts_per_pa': pts_per_pa,
                            'appearances': 0
                        }
                    player_stats[name]['appearances'] += 1
                else:
                    logger.warning(f"No player found with stemmed name '{stemmed_name}' for player '{name}'")

        if count > 0:
            avg_pts_pa = pts / count
            exp_pts = avg_pts_pa * AVG_STARTER_IP * AVG_PA_PER_INNING
            
            # Format player list
            player_list = []
            for name, stats in sorted(player_stats.items(), key=lambda x: x[1]['appearances'], reverse=True):
                player_list.append(
                    f"{name} ({stats['pos']}) [{stats['appearances']}] - {stats['pts_per_pa']:.3f} pts/PA"
                )
            
            results.append({
                "Team": map_team_abbr(team),
                "AvgPtsPerPA": avg_pts_pa,
                "ExpectedPts": exp_pts,
                "Players": '\n'.join(player_list)
            })

    return pd.DataFrame(results)

def process_schedule(schedule: Dict[str, Any], pitchers: pd.DataFrame, batting: pd.DataFrame) -> pd.DataFrame:
    if not schedule:
        return pd.DataFrame()

    games = []
    for day in schedule.get('dates', []):
        for game in day.get('games', []):
            gid = game['gamePk']
            feed = fetch_game_feed(gid)
            
            game_data = feed.get('gameData', {}) if feed else {}
            prob_pitchers = game_data.get('probablePitchers', {})
            away_pitcher = prob_pitchers.get('away', {}).get('fullName', 'TBD')
            home_pitcher = prob_pitchers.get('home', {}).get('fullName', 'TBD')
            
            away_abbr = map_team_abbr(game['teams']['away']['team']['abbreviation'])
            home_abbr = map_team_abbr(game['teams']['home']['team']['abbreviation'])

            def proj_pitcher(name):
                if name == 'TBD':
                    return DEFAULT_PITCHER_PTS
                match = pitchers[pitchers['Name'] == name]
                return (match['PtsPerIP'].iloc[0] * AVG_STARTER_IP) if not match.empty else DEFAULT_PITCHER_PTS

            def batting_pts(team):
                if team in batting.index:
                    return batting.loc[team, 'ExpectedPts']
                return 0

            games.extend([
                {
                    "Pitcher": away_pitcher,
                    "Matchup": f"{away_abbr} @ {home_abbr}",
                    "PitcherProjPts": proj_pitcher(away_pitcher),
                    "OppBattingAvg": batting_pts(home_abbr)
                },
                {
                    "Pitcher": home_pitcher,
                    "Matchup": f"{home_abbr} vs {away_abbr}",
                    "PitcherProjPts": proj_pitcher(home_pitcher),
                    "OppBattingAvg": batting_pts(away_abbr)
                }
            ])
            
    df = pd.DataFrame(games)
    df['StrengthDiff'] = df['PitcherProjPts'] - df['OppBattingAvg']
    return df

# --- Main Streamlit App ---
def main():
    with st.spinner('Loading pitcher projections...'):
        pitcher_df = fetch_projections('pitcher')
    
    with st.spinner('Loading batter projections...'):
        batter_df = fetch_projections('batter')
    
    with st.spinner('Analyzing team batting...'):
        team_batting = analyze_team_batting(batter_df).set_index('Team')

    est_now = datetime.now(EST)
    monday = est_now - timedelta(days=est_now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    st.header("🎯 Top Streaming Picks This Week")
    all_games = []

    with st.spinner('Processing schedule data...'):
        for date in dates:
            sched = fetch_schedule(date)
            games = process_schedule(sched, pitcher_df, team_batting)
            if not games.empty:
                games['Date'] = date
                all_games.append(games)

    if all_games:
        weekly = pd.concat(all_games)
        weekly = weekly[weekly['Pitcher'] != 'TBD']
        weekly['Team'] = weekly['Matchup'].apply(lambda x: x.split()[0])
        weekly['Opponent'] = weekly['Matchup'].apply(lambda x: x.split()[-1])
        
        summary = weekly[['Date', 'Pitcher', 'Team', 'Opponent', 'StrengthDiff']]
        summary = summary.sort_values('StrengthDiff', ascending=False)
        
        positive_matchups = summary[summary['StrengthDiff'] > 0]
        
        st.dataframe(
            positive_matchups,
            use_container_width=True,
            column_config={
                "Date": st.column_config.TextColumn("Date"),
                "Pitcher": st.column_config.TextColumn("Pitcher"),
                "Team": st.column_config.TextColumn("Team"),
                "Opponent": st.column_config.TextColumn("Opponent"),
                "StrengthDiff": st.column_config.NumberColumn("Strength Difference", format="%.1f")
            }
        )
        st.markdown(f"*Found {len(positive_matchups)} matchups with positive strength difference*")
    
    st.header("Pitcher Matchups")
    tabs = st.tabs(dates)
    for tab, date in zip(tabs, dates):
        with tab:
            with st.spinner(f'Loading matchups for {date}...'):
                sched = fetch_schedule(date)
                games = process_schedule(sched, pitcher_df, team_batting)
                if not games.empty:
                    st.dataframe(
                        games.sort_values('StrengthDiff', ascending=False),
                        use_container_width=True,
                        column_config={
                            "Pitcher": st.column_config.TextColumn("Pitcher"),
                            "Matchup": st.column_config.TextColumn("Matchup"),
                            "PitcherProjPts": st.column_config.NumberColumn("Pitcher Projected Points", format="%.1f"),
                            "OppBattingAvg": st.column_config.NumberColumn("Opponent Team Batting Avg", format="%.1f"),
                            "StrengthDiff": st.column_config.NumberColumn("Strength Difference", format="%.1f")
                        }
                    )
                else:
                    st.info(f"No games scheduled for {date}")

    st.header("Team Batting Analysis")
    if not team_batting.empty:
        st.dataframe(
            team_batting,
            use_container_width=True,
            column_config={
                "Team": st.column_config.TextColumn("Team"),
                "AvgPtsPerPA": st.column_config.NumberColumn("Average Points per PA", format="%.3f"),
                "ExpectedPts": st.column_config.NumberColumn("Expected Points vs Starter", format="%.1f"),
                "Players": st.column_config.TextColumn("Recent Lineup Players (Position) [Appearances]")
            }
        )
    else:
        st.error("Unable to analyze team batting projections")

    st.header("Batter Projections")
    if not batter_df.empty:
        st.dataframe(
            batter_df.sort_values("ProjPts", ascending=False),
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Name"),
                "Team": st.column_config.TextColumn("Team"),
                "Pos": st.column_config.TextColumn("Position"),
                "ProjPts": st.column_config.NumberColumn("Projected Points", format="%.1f"),
                "PA": st.column_config.NumberColumn("Projected PA", format="%.0f"),
                "PtsPerPA": st.column_config.NumberColumn("Points per PA", format="%.3f")
            }
        )
    else:
        st.error("Unable to load batter projections")
        
    st.header("Pitcher Projections")
    if not pitcher_df.empty:
        st.dataframe(
            pitcher_df.sort_values("ProjPts", ascending=False),
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Name"),
                "Team": st.column_config.TextColumn("Team"),
                "Pos": st.column_config.TextColumn("Position"),
                "ProjPts": st.column_config.NumberColumn("Projected Points", format="%.1f"),
                "IP": st.column_config.NumberColumn("Projected IP", format="%.1f"),
                "PtsPerIP": st.column_config.NumberColumn("Points per IP", format="%.3f")
            }
        )
    else:
        st.error("Unable to load pitcher projections")

if __name__ == "__main__":
    main()
