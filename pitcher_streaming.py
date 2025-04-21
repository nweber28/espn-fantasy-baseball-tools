import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os
import logging
from urllib.parse import urlencode, quote
from typing import Optional, Dict, Any, List, Union
import pytz
from nltk.stem import SnowballStemmer
import nltk
import unicodedata
from unidecode import unidecode

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Initialize stemmer
stemmer = SnowballStemmer('english')

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EST = pytz.timezone('US/Eastern')
EMPTY_DF = pd.DataFrame()
API_TIMEOUT = 30  # seconds

class APIError(Exception):
    """Custom exception for API-related errors"""
    pass

def handle_api_response(response: requests.Response, endpoint: str) -> Dict[str, Any]:
    """
    Standardized handling of API responses
    Returns the JSON response or raises an APIError
    """
    try:
        if response.status_code != 200:
            error_msg = f"API request failed for {endpoint}: HTTP {response.status_code}"
            logger.error(f"{error_msg}\nResponse text: {response.text}")
            raise APIError(error_msg)
        
        return response.json()
    except ValueError as e:
        error_msg = f"Invalid JSON response from {endpoint}: {str(e)}"
        logger.error(error_msg)
        raise APIError(error_msg)

def log_api_call(endpoint: str, params: Optional[Dict] = None) -> None:
    """Log API call details"""
    logger.info(f"Making API call to {endpoint}")
    if params:
        logger.debug(f"Parameters: {params}")

def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """
    Validate that a DataFrame contains required columns
    Returns True if valid, False otherwise
    """
    if df.empty:
        logger.warning("DataFrame is empty")
        return False
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"DataFrame missing required columns: {missing_columns}")
        return False
    
    return True

# Set page configuration
st.set_page_config(
    page_title="Fantasy Baseball Analysis",
    page_icon="⚾",
    layout="wide"
)

# App title and description
st.title("Fantasy Baseball Analysis")
st.markdown("""
This application helps you analyze pitchers for fantasy baseball.
It uses ATC Rest-Of-Season projections to evaluate player performance.
""")

# Create cache directory if it doesn't exist
os.makedirs("data/cache", exist_ok=True)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_fangraphs_data(url, player_type):
    """Fetch data from FanGraphs API"""
    headers = {
        'sec-ch-ua-platform': '"macOS"',
        'Referer': 'https://www.fangraphs.com/fantasy-tools/auction-calculator',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {player_type} data: HTTP {response.status_code}")
            logger.error(f"Response text: {response.text}")
            st.error(f"Failed to fetch {player_type} data: HTTP {response.status_code}")
            return pd.DataFrame()
            
        data = response.json()
        return data
        
    except Exception as e:
        logger.error(f"Error fetching {player_type} projections: {str(e)}")
        st.error(f"Error fetching {player_type} projections: {e}")
        return None

def stem_player_name(name):
    """Convert player name to a standardized format for matching"""
    if not name:
        return ""
    
    # Hard-coded name mappings for special cases
    name_mappings = {
        'ben-williamson': 'benjamin-williamson',
        'zach-dezenzo': 'zachary-dezenzo',
        # Add other special cases here
    }
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove periods
    name = name.replace('.', '')
    
    # Convert accented characters to ASCII
    name = unidecode(name)
    
    # Convert spaces to hyphens
    name = name.replace(' ', '-')
    
    # Check if this name needs to be remapped
    if name in name_mappings:
        return name_mappings[name]
    
    return name

def process_player_data(data, player_type):
    """Process player data from FanGraphs API response"""
    if not data:
        return pd.DataFrame()
        
    players = []
    for player in data.get('data', []):
        if player_type == 'pitcher' and player.get("POS") not in ["SP", "RP"]:
            continue
            
        player_name = player.get("PlayerName", "")
        player_data = {
            "Name": player_name,
            "StemmedName": stem_player_name(player_name),
            "Team": player.get("Team", ""),
            "Pos": player.get("POS", ""),
            "ProjPts": float(player.get("rPTS", 0))
        }
        
        # Add PA for batters
        if player_type == 'batter':
            player_data["PA"] = float(player.get("PA", 0))
            # Calculate points per PA
            player_data["PtsPerPA"] = player_data["ProjPts"] / player_data["PA"] if player_data["PA"] > 0 else 0
        else:
            # For pitchers, add IP and calculate points per inning
            player_data["IP"] = float(player.get("IP", 0))
            player_data["PtsPerIP"] = player_data["ProjPts"] / player_data["IP"] if player_data["IP"] > 0 else 0
            
        players.append(player_data)
                
    return pd.DataFrame(players)

# Function to get ATC Rest-Of-Season batter projections  
def get_batter_projections():
    """Get ATC Rest-Of-Season projections for batters from FanGraphs API"""
    url = "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=bat&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    data = fetch_fangraphs_data(url, 'batter')
    return process_player_data(data, 'batter')

# Function to get ATC Rest-Of-Season pitcher projections  
def get_pitcher_projections():
    """Get ATC Rest-Of-Season projections for pitchers from FanGraphs API"""
    url = "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=pit&players=&proj=ratcdc&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    data = fetch_fangraphs_data(url, 'pitcher')
    return process_player_data(data, 'pitcher')

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_schedule_data(date):
    """Get MLB schedule data for a specific date"""
    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&leagueId=103,104&hydrate=team,linescore,flags,liveLookin,review&useLatestGames=false&language=en"
        
        headers = {
            'sec-ch-ua-platform': '"macOS"',
            'Referer': f'https://www.mlb.com/probable-pitchers/{date}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch schedule data: HTTP {response.status_code}")
            logger.error(f"Response text: {response.text}")
            st.error(f"Failed to fetch schedule data: HTTP {response.status_code}")
            return None
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error fetching schedule data: {str(e)}")
        st.error(f"Error fetching schedule data: {e}")
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_game_feed(game_id):
    """Get detailed game information including probable pitchers"""
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
        
        headers = {
            'sec-ch-ua-platform': '"macOS"',
            'Referer': 'https://www.mlb.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch game feed: HTTP {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return None
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error fetching game feed: {str(e)}")
        return None

def get_team_abbreviation(team_abbr):
    """Map team abbreviations to standard format"""
    team_map = {
        # Common alternate abbreviations
        'CWS': 'CHW',  # Chicago White Sox
        'SF': 'SFG',   # San Francisco Giants
        'SD': 'SDP',   # San Diego Padres
        'WSH': 'WSN',  # Washington Nationals
        'WAS': 'WSN',  # Washington Nationals
        'TB': 'TBR',   # Tampa Bay Rays
        'KC': 'KCR',   # Kansas City Royals
        'ANA': 'LAA',  # Los Angeles Angels
        'FLA': 'MIA',  # Miami Marlins
        'NYN': 'NYM',  # New York Mets
        'SLN': 'STL',  # St. Louis Cardinals
        'LAN': 'LAD',  # Los Angeles Dodgers
        'SFN': 'SFG',  # San Francisco Giants
        'AZ': 'ARI',   # Arizona Diamondbacks
    }
    
    # If no remapping needed, return original
    if team_abbr not in team_map:
        return team_abbr
    
    return team_map[team_abbr]

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_team_lineup(team_id):
    """Fetch team lineup data from FanGraphs API"""
    try:
        url = f"https://www.fangraphs.com/api/depth-charts/past-lineups?teamid={team_id}&loaddate={int(datetime.now().timestamp())}"
        
        headers = {
            'sec-ch-ua-platform': '"macOS"',
            'Referer': f'https://www.fangraphs.com/roster-resource/depth-charts/{team_id}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch lineup data for team {team_id}: HTTP {response.status_code}")
            return None
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error fetching lineup data for team {team_id}: {str(e)}")
        return None

def analyze_team_batting(batter_df):
    """Analyze team batting strength based on actual lineups"""
    if batter_df.empty:
        return pd.DataFrame()
        
    # Get team ID mapping
    team_map = {
        'LAA': 1, 'BAL': 2, 'BOS': 3, 'CHW': 4, 'CLE': 5, 'DET': 6, 'KCR': 7, 'MIN': 8,
        'NYY': 9, 'ATH': 10, 'SEA': 11, 'TBR': 12, 'TEX': 13, 'TOR': 14, 'ARI': 15,
        'ATL': 16, 'CHC': 17, 'CIN': 18, 'COL': 19, 'MIA': 20, 'HOU': 21, 'LAD': 22,
        'MIL': 23, 'WSN': 24, 'NYM': 25, 'PHI': 26, 'PIT': 27, 'STL': 28, 'SDP': 29,
        'SFG': 30
    }
    
    # Constants
    AVG_PA_PER_INNING = 4.2  # Average plate appearances per inning
    AVG_STARTER_IP = 5.5     # Average innings pitched by starter
    
    team_analysis = []
    
    for team_abbr, team_id in team_map.items():
        try:
            # Validate team abbreviation
            validated_abbr = get_team_abbreviation(team_abbr)
            
            lineup_data = get_team_lineup(team_id)
            if not lineup_data:
                logger.warning(f"No lineup data available for team {validated_abbr} (ID: {team_id})")
                continue
                
            # Track player appearances and their points per PA
            player_appearances = {}  # {player_name: count}
            total_points_per_pa = 0
            total_appearances = 0
            
            # Process all recent lineups
            for lineup in lineup_data:
                players = lineup.get('dataPlayers', [])
                
                # Filter out players who are injured, in AAA, or have no name
                active_players = [
                    p for p in players 
                    if p.get('playerName') and 
                    not p.get('valueOverride') in ['INJ', 'AAA']
                ]
                
                for player in active_players:
                    player_name = player['playerName']
                    stemmed_name = stem_player_name(player_name)
                    
                    # Try to find matching player using stemmed name
                    matching_players = batter_df[batter_df['StemmedName'] == stemmed_name]
                    
                    if not matching_players.empty:
                        pts_per_pa = matching_players['PtsPerPA'].iloc[0]
                        player_appearances[player_name] = player_appearances.get(player_name, 0) + 1
                        total_points_per_pa += pts_per_pa
                        total_appearances += 1
                    else:
                        logger.error(f"Could not find projections for player: {player_name}")
            
            if total_appearances == 0:
                logger.warning(f"No active players found for team {validated_abbr}")
                continue
                
            # Calculate weighted average points per PA for the team
            avg_points_per_pa = total_points_per_pa / total_appearances
            
            # Calculate expected points against a starter
            expected_pa = AVG_STARTER_IP * AVG_PA_PER_INNING
            expected_points = avg_points_per_pa * expected_pa
            
            # Get all players and their appearance counts, sorted by frequency
            all_players = sorted(
                [(name, count) for name, count in player_appearances.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Format player list with positions, appearance counts, and points per PA
            player_list = []
            for name, count in all_players:
                stemmed_name = stem_player_name(name)
                matching_players = batter_df[batter_df['StemmedName'] == stemmed_name]
                if not matching_players.empty:
                    pos = matching_players['Pos'].iloc[0]
                    pts_per_pa = matching_players['PtsPerPA'].iloc[0]
                    player_list.append(f"{name} ({pos}) [{count}] - {pts_per_pa:.3f} pts/PA")
                else:
                    player_list.append(f"{name} [?] [{count}] - !")
            
            team_analysis.append({
                'Team': validated_abbr,
                'AvgPtsPerPA': avg_points_per_pa,
                'ExpectedPts': expected_points,
                'Players': '\n'.join(player_list)  # Use newline for better readability
            })
            
        except Exception as e:
            logger.error(f"Error processing team {team_abbr}: {str(e)}")
            continue
    
    if not team_analysis:
        raise ValueError("No valid team data could be processed. Check the logs for details.")
        
    return pd.DataFrame(team_analysis).sort_values('ExpectedPts', ascending=False)

def process_schedule_data(data, pitcher_projections, team_batting_avgs):
    """Process schedule data into a DataFrame of games with pitcher projections and team batting averages"""
    if not data or 'dates' not in data or not data['dates']:
        return pd.DataFrame()
        
    # Constants for average game metrics
    AVG_STARTER_IP = 5.5  # Average innings pitched by a starter
    DEFAULT_PITCHER_PTS = 6.0  # Default points for pitchers without projections
        
    games = []
    for date_data in data['dates']:
        for game in date_data.get('games', []):
            # Get game feed for probable pitchers
            game_feed = get_game_feed(game['gamePk'])
            away_pitcher = 'TBD'
            home_pitcher = 'TBD'
            
            if game_feed and 'gameData' in game_feed:
                game_data = game_feed['gameData']
                if 'probablePitchers' in game_data:
                    away_pitcher = game_data['probablePitchers'].get('away', {}).get('fullName', 'TBD')
                    home_pitcher = game_data['probablePitchers'].get('home', {}).get('fullName', 'TBD')
            
            # Get pitcher projections
            def get_pitcher_proj(pitcher_name):
                if pitcher_name == 'TBD':
                    return None
                if pitcher_projections.empty:
                    return DEFAULT_PITCHER_PTS  # Default value when no projections available
                matching_pitchers = pitcher_projections[pitcher_projections['Name'] == pitcher_name]
                if not matching_pitchers.empty:
                    # Calculate projected points based on average innings pitched
                    pts_per_ip = matching_pitchers['PtsPerIP'].iloc[0]
                    return pts_per_ip * AVG_STARTER_IP
                return DEFAULT_PITCHER_PTS  # Default value when pitcher not found in projections
            
            # Get team batting averages
            def get_team_batting_avg(team_abbr):
                if team_batting_avgs.empty:
                    return None  # Return None when no batting averages available
                mapped_abbr = get_team_abbreviation(team_abbr)
                if mapped_abbr in team_batting_avgs.index:
                    # Team batting average is already in expected points against a starter
                    return team_batting_avgs.loc[mapped_abbr, 'ExpectedPts']
                return None  # Return None when team not found in batting averages
            
            away_pitcher_proj = get_pitcher_proj(away_pitcher)
            home_pitcher_proj = get_pitcher_proj(home_pitcher)
            
            away_team_abbr = get_team_abbreviation(game['teams']['away']['team']['abbreviation'])
            home_team_abbr = get_team_abbreviation(game['teams']['home']['team']['abbreviation'])
            
            away_team_batting = get_team_batting_avg(away_team_abbr)
            home_team_batting = get_team_batting_avg(home_team_abbr)
            
            # Add away pitcher game
            games.append({
                'Pitcher': away_pitcher,
                'Matchup': f"{away_team_abbr} @ {home_team_abbr}",
                'PitcherProjPts': away_pitcher_proj,
                'OppTeamBattingAvg': home_team_batting,
                'StrengthDiff': away_pitcher_proj - home_team_batting if away_pitcher_proj is not None else None
            })
            
            # Add home pitcher game
            games.append({
                'Pitcher': home_pitcher,
                'Matchup': f"{home_team_abbr} vs {away_team_abbr}",
                'PitcherProjPts': home_pitcher_proj,
                'OppTeamBattingAvg': away_team_batting,
                'StrengthDiff': home_pitcher_proj - away_team_batting if home_pitcher_proj is not None else None
            })
            
    return pd.DataFrame(games)

def main():
    # Get projections first
    pitcher_df = get_pitcher_projections()
    batter_df = get_batter_projections()
    
    # Get team batting analysis
    team_analysis = analyze_team_batting(batter_df)
    
    # Add summary panel at the top
    st.header("🎯 Top Streaming Picks This Week")
    
    # Get dates from Monday to Sunday of current week in EST
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    
    # Calculate Monday of current week
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate Sunday of current week
    sunday = monday + timedelta(days=6)
    
    # Generate dates from Monday to Sunday
    dates = []
    current = monday
    while current <= sunday:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    # Collect all games for the week
    all_games = []
    for date in dates:
        schedule_data = get_schedule_data(date)
        if schedule_data:
            games_df = process_schedule_data(schedule_data, pitcher_df, team_analysis.set_index('Team'))
            if not games_df.empty:
                games_df['Date'] = date
                all_games.append(games_df)
    
    if all_games:
        # Combine all games and sort by strength difference
        weekly_games = pd.concat(all_games)
        weekly_games = weekly_games[weekly_games['Pitcher'] != 'TBD']  # Remove TBD pitchers
        
        # Extract team and opponent from Matchup column
        weekly_games['Team'] = weekly_games['Matchup'].apply(lambda x: x.split()[0])
        weekly_games['Opponent'] = weekly_games['Matchup'].apply(lambda x: x.split()[-1])
        
        # Select and rename columns
        summary_df = weekly_games[['Date', 'Pitcher', 'Team', 'Opponent', 'StrengthDiff']]
        summary_df = summary_df.sort_values('StrengthDiff', ascending=False)
        
        # Filter for positive strength differences
        positive_matchups = summary_df[summary_df['StrengthDiff'] > 0]
        
        # Display all positive matchups in a single table
        st.dataframe(
            positive_matchups,
            use_container_width=True,
            column_config={
                "Date": st.column_config.TextColumn("Date"),
                "Pitcher": st.column_config.TextColumn("Pitcher"),
                "Team": st.column_config.TextColumn("Team"),
                "Opponent": st.column_config.TextColumn("Opponent"),
                "StrengthDiff": st.column_config.NumberColumn(
                    "Strength Difference",
                    format="%.1f"
                )
            }
        )
        
        # Show count of positive matchups
        st.markdown(f"*Found {len(positive_matchups)} matchups with positive strength difference*")
    
    # Add schedule section at the top
    st.header("Pitcher Matchups")
    
    # Create tabs for each date
    tabs = st.tabs([date for date in dates])
    
    for tab, date in zip(tabs, dates):
        with tab:
            schedule_data = get_schedule_data(date)
            if schedule_data:
                games_df = process_schedule_data(schedule_data, pitcher_df, team_analysis.set_index('Team'))
                if not games_df.empty:
                    # Format the display
                    st.dataframe(
                        games_df.sort_values('StrengthDiff', ascending=False),
                        use_container_width=True,
                        column_config={
                            "Pitcher": st.column_config.TextColumn("Pitcher"),
                            "Matchup": st.column_config.TextColumn("Matchup"),
                            "PitcherProjPts": st.column_config.NumberColumn(
                                "Pitcher Projected Points",
                                format="%.1f"
                            ),
                            "OppTeamBattingAvg": st.column_config.NumberColumn(
                                "Opponent Team Batting Avg",
                                format="%.1f"
                            ),
                            "StrengthDiff": st.column_config.NumberColumn(
                                "Strength Difference",
                                format="%.1f"
                            )
                        }
                    )
                else:
                    st.info(f"No games scheduled for {date}")
            else:
                st.error(f"Unable to load schedule for {date}")
    
    # Display team batting analysis
    st.header("Team Batting Analysis")
    if not team_analysis.empty:
        st.dataframe(
            team_analysis,
            use_container_width=True,
            column_config={
                "Team": st.column_config.TextColumn("Team"),
                "AvgPtsPerPA": st.column_config.NumberColumn(
                    "Average Points per PA",
                    format="%.3f"
                ),
                "ExpectedPts": st.column_config.NumberColumn(
                    "Expected Points vs Starter",
                    format="%.1f"
                ),
                "Players": st.column_config.TextColumn(
                    "Recent Lineup Players (Position) [Appearances]"
                )
            }
        )
    else:
        st.error("Unable to analyze team batting projections")
    
    # Display individual projections  
    st.header("Batter Projections")
    if not batter_df.empty:
        st.dataframe(
            batter_df.sort_values("ProjPts", ascending=False),
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Name"),
                "Team": st.column_config.TextColumn("Team"),
                "Pos": st.column_config.TextColumn("Position"),
                "ProjPts": st.column_config.NumberColumn(
                    "Projected Points",
                    format="%.1f"
                ),
                "PA": st.column_config.NumberColumn(
                    "Projected PA",
                    format="%.0f"
                ),
                "PtsPerPA": st.column_config.NumberColumn(
                    "Points per PA",
                    format="%.3f"
                )
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
                "ProjPts": st.column_config.NumberColumn(
                    "Projected Points",
                    format="%.1f"
                ),
                "IP": st.column_config.NumberColumn(
                    "Projected IP",
                    format="%.1f"
                ),
                "PtsPerIP": st.column_config.NumberColumn(
                    "Points per IP",
                    format="%.3f"
                )
            }
        )
    else:
        st.error("Unable to load pitcher projections")

# Run the app
if __name__ == "__main__":
    main()
