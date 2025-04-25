"""
Pitcher Streaming Analysis Page.

This page helps users analyze pitcher matchups and find the best streaming options.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import nltk
from typing import Dict, Any, Optional, List

# Import from our modules
from utils.logging_utils import setup_logging
from utils.data_processing import map_team_abbr, convert_positions, process_team_rosters, process_fangraphs_data
from utils.name_utils import stem_name
from services.espn_service import ESPNService
from services.fangraphs_service import FanGraphsService
from services.mlb_service import MLBService
from config.constants import AVG_STARTER_IP, AVG_PA_PER_INNING, DEFAULT_PITCHER_PTS, TEAM_IDS
from config.settings import EST, DEFAULT_LEAGUE_ID

# Setup logging
logger = setup_logging()

# No need to initialize service instances as we're using static methods

# --- Streamlit Configuration ---
st.set_page_config(
    page_title="Pitcher Streaming",
    page_icon="🚰",
    layout="wide"
)

# --- Setup ---
nltk.download('punkt', quiet=True)

# --- Main Functions ---
@st.cache_data(ttl=3600)
def analyze_team_batting(batters: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze team batting statistics based on recent lineups.
    
    Args:
        batters: DataFrame of batter projections
        
    Returns:
        DataFrame of team batting analysis
    """
    if batters.empty:
        return pd.DataFrame()

    results = []
    for team, team_id in TEAM_IDS.items():
        lineups = MLBService.fetch_team_lineup(team_id)
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

def process_schedule(schedule: Dict[str, Any], pitchers: pd.DataFrame, batting: pd.DataFrame, rostered_pitcher_names=None) -> pd.DataFrame:
    """
    Process MLB schedule data to analyze pitcher matchups.
    
    Args:
        schedule: MLB schedule data
        pitchers: DataFrame of pitcher projections
        batting: DataFrame of team batting analysis
        rostered_pitcher_names: List of rostered pitcher names
        
    Returns:
        DataFrame of pitcher matchups
    """
    if not schedule:
        return pd.DataFrame()

    games = []
    for day in schedule.get('dates', []):
        for game in day.get('games', []):
            gid = game['gamePk']
            feed = MLBService.fetch_game_feed(gid)
            
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

            # Check if pitcher is available (not on any roster)
            def is_free_agent(name):
                if rostered_pitcher_names is None:
                    return True
                return name not in rostered_pitcher_names

            games.extend([
                {
                    "Pitcher": away_pitcher,
                    "Matchup": f"{away_abbr} @ {home_abbr}",
                    "PitcherProjPts": proj_pitcher(away_pitcher),
                    "OppBattingAvg": batting_pts(home_abbr),
                    "IsFreeAgent": is_free_agent(away_pitcher)
                },
                {
                    "Pitcher": home_pitcher,
                    "Matchup": f"{home_abbr} vs {away_abbr}",
                    "PitcherProjPts": proj_pitcher(home_pitcher),
                    "OppBattingAvg": batting_pts(away_abbr),
                    "IsFreeAgent": is_free_agent(home_pitcher)
                }
            ])
            
    df = pd.DataFrame(games)
    if not df.empty:
        df['StrengthDiff'] = df['PitcherProjPts'] - df['OppBattingAvg']
    return df

# --- Main Page Content ---
st.title("Pitcher Streaming Analysis")
st.markdown("This page helps you analyze pitchers for fantasy baseball using ATC Rest-Of-Season projections.")

# Add league ID input in the sidebar
with st.sidebar:
    st.header("ESPN Fantasy Settings")
    league_id = st.text_input("League ID", value=DEFAULT_LEAGUE_ID, help="Enter your ESPN Fantasy Baseball League ID")
    show_all = st.checkbox("Show All Pitchers", value=False, help="Show all pitchers including those on rosters")
    
    if league_id:
        with st.spinner("Loading league data..."):
            # First fetch ESPN player data
            espn_data = ESPNService.fetch_player_data()
            rostered_pitcher_names = []
            
            if espn_data:
                espn_df = pd.DataFrame(espn_data)
                logger.info(f"Created ESPN dataframe with {len(espn_df)} rows")
                
                # Add stemmed names to ESPN data for matching
                espn_df['stemmed_name'] = espn_df['fullName'].apply(stem_name)
                
                # Get teams and rosters
                teams_data = ESPNService.fetch_teams_data(league_id)
                roster_data = ESPNService.fetch_team_rosters(league_id)
                
                if teams_data and roster_data:
                    team_rosters, player_team_map = process_team_rosters(roster_data, teams_data, espn_df)
                    
                    if team_rosters:
                        # Get all rostered pitchers across all teams
                        for team_id, team_data in team_rosters.items():
                            for player in team_data['players']:
                                if "SP" in player.get('positions', "") or "RP" in player.get('positions', ""):
                                    rostered_pitcher_names.append(player['name'])
                        
                        st.write(f"Found {len(rostered_pitcher_names)} pitchers on rosters")
                    else:
                        st.error("Failed to process team rosters. Check your league ID.")
                else:
                    st.error("Failed to fetch team data. Check your league ID.")
            else:
                st.error("Failed to fetch ESPN player data.")

with st.spinner('Loading pitcher projections...'):
    pitcher_data = FanGraphsService.fetch_projections('pitcher')
    pitcher_df = process_fangraphs_data(pitcher_data, 'pitcher')

with st.spinner('Loading batter projections...'):
    # Use the streamer-specific point setup for batters when analyzing pitcher matchups
    batter_data = FanGraphsService.fetch_projections('batter', for_streamer_analysis=True)
    batter_df = process_fangraphs_data(batter_data, 'batter')

with st.spinner('Analyzing team batting...'):
    team_batting = analyze_team_batting(batter_df).set_index('Team')

est_now = datetime.now(EST)
monday = est_now - timedelta(days=est_now.weekday())
monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
dates = [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

st.header("🎯 Top Streaming Picks This Week")
all_games = []

# Get roster pitchers if available
if 'rostered_pitcher_names' not in locals() or rostered_pitcher_names is None:
    rostered_pitcher_names = []
st.write(f"Found {len(rostered_pitcher_names)} rostered pitchers. Showing only free agents by default.")

with st.spinner('Processing schedule data...'):
    for date in dates:
        sched = MLBService.fetch_schedule(date)
        games = process_schedule(sched, pitcher_df, team_batting, rostered_pitcher_names)
        if not games.empty:
            games['Date'] = date
            all_games.append(games)

if all_games:
    weekly = pd.concat(all_games)
    weekly = weekly[weekly['Pitcher'] != 'TBD']
    weekly['Team'] = weekly['Matchup'].apply(lambda x: x.split()[0])
    weekly['Opponent'] = weekly['Matchup'].apply(lambda x: x.split()[-1])
    
    summary = weekly[['Date', 'Pitcher', 'Team', 'Opponent', 'StrengthDiff', 'IsFreeAgent']]
    summary = summary.sort_values('StrengthDiff', ascending=False)
    
    # Filter to show only positive matchups
    positive_matchups = summary[summary['StrengthDiff'] > 0]
    
    # If show_all is false, filter to only show free agents
    if not show_all:
        filtered_summary = positive_matchups[positive_matchups['IsFreeAgent']]
        st.write("Showing only free agent pitchers with positive matchups")
    else:
        filtered_summary = positive_matchups
        st.write("Showing all pitchers with positive matchups")
    
    st.dataframe(
        filtered_summary,
        use_container_width=True,
        column_config={
            "Date": st.column_config.TextColumn("Date"),
            "Pitcher": st.column_config.TextColumn("Pitcher"),
            "Team": st.column_config.TextColumn("Team"),
            "Opponent": st.column_config.TextColumn("Opponent"),
            "StrengthDiff": st.column_config.NumberColumn("Strength Difference", format="%.2f"),
            "IsFreeAgent": st.column_config.CheckboxColumn("Free Agent")
        }
    )
    st.markdown(f"*Found {len(filtered_summary)} available streaming options with positive strength difference*")

st.header("Pitcher Matchups")
tabs = st.tabs(dates)
for tab, date in zip(tabs, dates):
    with tab:
        with st.spinner(f'Loading matchups for {date}...'):
            sched = MLBService.fetch_schedule(date)
            games = process_schedule(sched, pitcher_df, team_batting, rostered_pitcher_names)
            
            if not games.empty:
                # Always show all pitchers in the daily tables
                games_to_show = games
                
                st.dataframe(
                    games_to_show.sort_values('StrengthDiff', ascending=False),
                    use_container_width=True,
                    column_config={
                        "Pitcher": st.column_config.TextColumn("Pitcher"),
                        "Matchup": st.column_config.TextColumn("Matchup"),
                        "PitcherProjPts": st.column_config.NumberColumn("Pitcher Projected Points", format="%.2f"),
                        "OppBattingAvg": st.column_config.NumberColumn("Opponent Team Batting Avg", format="%.2f"),
                        "StrengthDiff": st.column_config.NumberColumn("Strength Difference", format="%.2f"),
                        "IsFreeAgent": st.column_config.CheckboxColumn("Free Agent")
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
