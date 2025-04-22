import streamlit as st
import pandas as pd
import requests
from unidecode import unidecode
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Waiver Wire Analyzer",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("📈 Waiver Wire Analyzer")

# Position ID to name mapping
POSITION_MAP = {
    0: "C",
    1: "1B",
    2: "2B",
    3: "3B",
    4: "SS",
    5: "OF",
    6: "MI",
    7: "CI",
    8: "LF",
    9: "CF",
    10: "RF",
    11: "DH",
    12: "UTIL",
    13: "P",
    14: "SP",
    15: "RP",
    16: "BN",
    17: "IL",
    18: "NA",
    19: "IF"
}

# Utility functions
def stem_name(name: str) -> str:
    """Standardize player name for matching."""
    # Special case mappings for players with name discrepancies
    mappings = {
        'ben-williamson': 'benjamin-williamson', 
        'zach-dezenzo': 'zachary-dezenzo',
        'cj-abrams': 'c.j.-abrams',
        'jt-realmuto': 'j.t.-realmuto',
        'aj-pollock': 'a.j.-pollock'
    }
    # Clean and standardize the name
    clean_name = unidecode(name.lower().replace('.', '').replace(' ', '-'))
    return mappings.get(clean_name, clean_name)

def convert_positions(positions_list):
    """Convert position IDs to position names, showing only key positions."""
    if not isinstance(positions_list, list):
        return ""
    
    # Define the positions we want to display
    display_positions = {"C", "1B", "2B", "3B", "SS", "OF", "SP", "RP", "DH"}
    
    # Map position IDs to their names and filter for display positions
    positions = []
    
    for pos in positions_list:
        pos_name = POSITION_MAP.get(pos, str(pos))
        
        # Convert all outfield positions (LF, CF, RF) to just "OF"
        if pos_name in ["LF", "CF", "RF"]:
            pos_name = "OF"
            
        # Only include the position if it's in our display set
        if pos_name in display_positions and pos_name not in positions:
            positions.append(pos_name)
    
    return ", ".join(positions)

# Function to fetch player data from ESPN
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_espn_player_data():
    url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/players?scoringPeriodId=0&view=players_wl"
    
    headers = {
        "X-Fantasy-Filter": '{"filterActive":{"value":true}}',
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://fantasy.espn.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "X-Fantasy-Platform": "kona-PROD-ea1dac81fac83846270c371702992d3a2f69aa70",
        "sec-ch-ua-mobile": "?0",
        "X-Fantasy-Source": "kona",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info("Fetching ESPN player data")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched ESPN player data: {len(data)} players")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ESPN data: {e}")
        st.error(f"Error fetching ESPN data: {e}")
        return None

# Function to fetch ESPN league teams data
@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def fetch_espn_teams_data(league_id, season_id=2025):
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/{season_id}/segments/0/leagues/{league_id}"
    
    headers = {
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://fantasy.espn.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "X-Fantasy-Platform": "kona-PROD-ea1dac81fac83846270c371702992d3a2f69aa70",
        "sec-ch-ua-mobile": "?0",
        "X-Fantasy-Source": "kona",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Fetching ESPN teams data for league {league_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched ESPN teams data: {len(data.get('teams', []))} teams")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ESPN teams data: {e}")
        st.error(f"Error fetching ESPN teams data: {e}")
        return None

# Function to fetch ESPN league team rosters
@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def fetch_espn_team_rosters(league_id, season_id=2025):
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/{season_id}/segments/0/leagues/{league_id}?view=mRoster"
    
    headers = {
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://fantasy.espn.com/",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "X-Fantasy-Platform": "kona-PROD-ea1dac81fac83846270c371702992d3a2f69aa70",
        "sec-ch-ua-mobile": "?0",
        "X-Fantasy-Source": "kona",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Fetching ESPN team rosters for league {league_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Debug logs for response structure
        if 'teams' in data:
            logger.info(f"Successfully fetched roster data with {len(data['teams'])} teams")
            for i, team in enumerate(data['teams']):
                roster_entries = team.get('roster', {}).get('entries', [])
                logger.info(f"Team {i+1}: {team.get('name')} - {len(roster_entries)} players")
        else:
            logger.warning(f"Roster data missing 'teams' key. Keys: {list(data.keys())}")
            
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ESPN team rosters: {e}")
        st.error(f"Error fetching ESPN team rosters: {e}")
        return None

# Function to fetch FanGraphs batter projections
@st.cache_data(ttl=3600)
def fetch_fangraphs_batters():
    url = "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=bat&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    
    headers = {
        "sec-ch-ua-platform": "macOS",
        "Referer": "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=bat&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0"
    }
    
    try:
        logger.info("Fetching FanGraphs batter data")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            logger.info(f"Successfully fetched FanGraphs batter data: {len(data['data'])} batters")
        else:
            logger.warning("FanGraphs batter data missing 'data' key")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching FanGraphs batter data: {e}")
        st.error(f"Error fetching FanGraphs batter data: {e}")
        return None

# Function to fetch FanGraphs pitcher projections
@st.cache_data(ttl=3600)
def fetch_fangraphs_pitchers():
    url = "https://www.fangraphs.com/api/fantasy/auction-calculator/data?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=pit&players=&proj=ratcdc&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0"
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "sec-ch-ua-platform": "macOS",
        "referer": "https://www.fangraphs.com/fantasy-tools/auction-calculator?teams=10&lg=MLB&dollars=260&mb=1&mp=12&msp=5&mrp=2&type=pit&players=&proj=rthebatx&split=&points=p%7C0%2C0%2C0%2C1%2C2%2C3%2C4%2C1%2C0%2C1%2C1%2C1%2C-1%2C0%2C0%2C0%7C3%2C2%2C-2%2C5%2C1%2C-2%2C0%2C-1%2C0%2C-1%2C2&rep=0&drp=0&pp=C%2CSS%2C2B%2C3B%2COF%2C1B&pos=1%2C1%2C1%2C1%2C3%2C1%2C0%2C0%2C0%2C1%2C5%2C2%2C0%2C3%2C0&sort=&view=0",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    
    try:
        logger.info("Fetching FanGraphs pitcher data")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data:
            logger.info(f"Successfully fetched FanGraphs pitcher data: {len(data['data'])} pitchers")
        else:
            logger.warning("FanGraphs pitcher data missing 'data' key")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching FanGraphs pitcher data: {e}")
        st.error(f"Error fetching FanGraphs pitcher data: {e}")
        return None

# Process FanGraphs data into a standardized format
def process_fangraphs_data(data, player_type):
    if not data or 'data' not in data:
        logger.warning(f"No valid data for {player_type}s processing")
        return pd.DataFrame()
        
    records = []
    for player in data.get('data', []):
        name = player.get("PlayerName", "")
        if not name:
            continue
            
        stemmed_name = stem_name(name)
        
        # Safely get projection points
        try:
            proj_pts = float(player.get("rPTS", 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid projection points for {name}: {player.get('rPTS')}")
            proj_pts = 0.0
        
        record = {
            "Name": name,
            "StemmedName": stemmed_name,
            "Team": player.get("Team", ""),
            "Pos": player.get("POS", ""),
            "ProjPts": proj_pts,
            "PlayerType": player_type
        }
        records.append(record)
    
    logger.info(f"Processed {len(records)} {player_type} records")    
    return pd.DataFrame(records)

# Process team roster data
def process_team_rosters(roster_data, teams_data, espn_df):
    if not roster_data or 'teams' not in roster_data:
        logger.warning("Invalid roster data structure")
        return {}, {}
    
    # Create a map of team ID to abbreviation
    team_abbrev_map = {}
    if teams_data and 'teams' in teams_data:
        for team in teams_data.get('teams', []):
            team_id = team.get('id')
            abbrev = team.get('abbrev', f'Team {team_id}')
            team_abbrev_map[team_id] = abbrev
            logger.info(f"Found team abbreviation: {abbrev} for team ID: {team_id}")
    
    team_rosters = {}
    player_team_map = {}
    
    for team in roster_data.get('teams', []):
        team_id = team.get('id')
        # Use abbreviation if available, otherwise fall back to name
        team_name = team.get('name', f'Team {team_id}')
        team_abbrev = team_abbrev_map.get(team_id, team_name)
        
        logger.info(f"Processing team: {team_abbrev} (ID: {team_id})")
        
        team_rosters[team_id] = {
            'name': team_name,
            'abbrev': team_abbrev,
            'players': []
        }
        
        # Get roster entries for this team
        roster_entries = team.get('roster', {}).get('entries', [])
        logger.info(f"Team {team_abbrev} has {len(roster_entries)} roster entries")
        
        for entry in roster_entries:
            player_id = entry.get('playerId')
            
            # Add player to team map
            player_team_map[player_id] = {
                'team_id': team_id, 
                'team_name': team_name,
                'team_abbrev': team_abbrev
            }
            
            # Find player in ESPN data
            player_data = espn_df[espn_df['id'] == player_id]
            
            if not player_data.empty:
                # Debug the player data
                player_name = player_data['fullName'].iloc[0]
                
                # Safely access projPts
                proj_pts = None
                if 'projPts' in player_data.columns:
                    try:
                        proj_pts = float(player_data['projPts'].iloc[0]) if not pd.isna(player_data['projPts'].iloc[0]) else None
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid projection points for {player_name}: {player_data['projPts'].iloc[0]}")
                
                player_info = {
                    'id': player_id,
                    'name': player_name,
                    'positions': convert_positions(player_data['eligibleSlots'].iloc[0]),
                    'projPts': proj_pts
                }
                team_rosters[team_id]['players'].append(player_info)
                logger.info(f"Added player: {player_name} to team {team_abbrev}")
            else:
                logger.warning(f"Player ID {player_id} not found in ESPN data")
    
    logger.info(f"Processed {len(player_team_map)} players across {len(team_rosters)} teams")
    return team_rosters, player_team_map

# Add league ID input in the sidebar
with st.sidebar:
    st.header("ESPN Fantasy Settings")
    league_id = st.text_input("League ID", value="339466431", help="Enter your ESPN Fantasy Baseball League ID")
    
    # Add debug toggle
    show_debug = st.checkbox("Show Debug Info", value=False, help="Show debug information in the UI")

# Fetch all data
with st.spinner("Fetching player data..."):
    espn_data = fetch_espn_player_data()
    fg_batters_data = fetch_fangraphs_batters()
    fg_pitchers_data = fetch_fangraphs_pitchers()

if espn_data:
    # Process ESPN data
    espn_df = pd.DataFrame(espn_data)
    logger.info(f"Created ESPN dataframe with {len(espn_df)} rows and {len(espn_df.columns)} columns")
    
    # Extract percentOwned from the ownership dictionary
    espn_df['percent_owned'] = espn_df['ownership'].apply(lambda x: x.get('percentOwned', 0) if isinstance(x, dict) else 0)
    espn_df = espn_df.drop('ownership', axis=1)
    
    # Add stemmed names to ESPN data for matching
    espn_df['stemmed_name'] = espn_df['fullName'].apply(stem_name)
    
    # Process FanGraphs data
    fg_pitchers_df = process_fangraphs_data(fg_pitchers_data, 'pitcher')
    fg_batters_df = process_fangraphs_data(fg_batters_data, 'batter')
    
    # Combine all FanGraphs data with pitcher priority
    fg_combined_df = pd.concat([fg_pitchers_df, fg_batters_df], ignore_index=True)
    logger.info(f"Combined FanGraphs data: {len(fg_combined_df)} players")
    
    # Create a mapping from stemmed name to projection points
    proj_pts_map = dict(zip(fg_combined_df['StemmedName'], fg_combined_df['ProjPts']))
    logger.info(f"Created projection points mapping for {len(proj_pts_map)} players")
    
    # Add projection points to ESPN data
    espn_df['projPts'] = espn_df['stemmed_name'].map(proj_pts_map)
    
    # Fetch team roster data if league ID is provided
    team_rosters = {}
    player_team_map = {}
    teams_data = None
    
    if league_id:
        with st.spinner("Fetching team rosters..."):
            # Log the league ID
            logger.info(f"Fetching rosters for league ID: {league_id}")
            
            # First fetch the teams data
            teams_data = fetch_espn_teams_data(league_id)
            if not teams_data:
                st.error("Failed to fetch teams data. Check your league ID and try again.")
                logger.error("Failed to fetch teams data")
            else:
                logger.info(f"Successfully fetched teams data with {len(teams_data.get('teams', []))} teams")
                
                # Then fetch the team rosters
                roster_data = fetch_espn_team_rosters(league_id)
                
                if roster_data:
                    # Log some info about the roster data for debugging
                    if 'teams' in roster_data:
                        logger.info(f"Roster data contains {len(roster_data['teams'])} teams")
                    else:
                        logger.warning(f"Roster data doesn't contain 'teams' key. Keys: {list(roster_data.keys())}")
                        # Show a sample of the response
                        sample_data = json.dumps(roster_data, indent=2)[:500] + "..."
                        logger.info(f"Sample roster data: {sample_data}")
                    
                    team_rosters, player_team_map = process_team_rosters(roster_data, teams_data, espn_df)
                    
                    if team_rosters:
                        st.success(f"Successfully loaded {len(team_rosters)} teams from your league")
                        logger.info(f"Successfully processed {len(team_rosters)} teams with {len(player_team_map)} players")
                    else:
                        st.error("Failed to process team rosters. Check your league ID and try again.")
                        logger.error("Failed to process team rosters")
                else:
                    st.error("Failed to fetch team rosters. Check your league ID and try again.")
                    logger.error("Failed to fetch team rosters")
    
    # Add team information to ESPN data
    espn_df['team_id'] = espn_df['id'].map(lambda x: player_team_map.get(x, {}).get('team_id', None))
    espn_df['team_name'] = espn_df['id'].map(lambda x: player_team_map.get(x, {}).get('team_abbrev', None))
    
    # Log team mapping results
    mapped_players = espn_df[espn_df['team_name'].notnull()].shape[0]
    logger.info(f"Mapped {mapped_players} players to teams out of {len(espn_df)} total players")
    
    # Filter out players with ownership less than 0.05%
    filtered_espn_df = espn_df[espn_df['percent_owned'] >= 0.05]
    logger.info(f"Filtered to {len(filtered_espn_df)} players with at least 0.05% ownership")
    
    # Calculate percentage of players with matched projections
    matched_players = filtered_espn_df['projPts'].notna().sum()
    total_players = len(filtered_espn_df)
    match_percentage = (matched_players / total_players) * 100 if total_players > 0 else 0
    logger.info(f"Matched projections for {matched_players}/{total_players} players ({match_percentage:.1f}%)")
    
    # Create simplified DataFrame with only the essential columns
    simplified_df = pd.DataFrame({
        'Name': filtered_espn_df['fullName'],
        'Percent Owned': filtered_espn_df['percent_owned'],
        'Eligible Positions': filtered_espn_df['eligibleSlots'].apply(convert_positions),
        'Projected Points': filtered_espn_df['projPts'].apply(lambda x: float(x) if pd.notnull(x) else None),
        'Team': filtered_espn_df['team_name']
    })
    
    # Sort by Projected Points (descending)
    simplified_df = simplified_df.sort_values('Projected Points', ascending=False, na_position='last').reset_index(drop=True)
    logger.info(f"Final dataframe has {len(simplified_df)} rows")
    
    # Display the simplified DataFrame
    st.title("Player Analysis")
    
    # Show debug info if requested
    if show_debug:
        st.subheader("Debug Information")
        st.write(f"League ID: {league_id}")
        st.write(f"Total ESPN Players: {len(espn_df)}")
        st.write(f"FanGraphs Batters: {len(fg_batters_df)}")
        st.write(f"FanGraphs Pitchers: {len(fg_pitchers_df)}")
        st.write(f"Players Matched to Teams: {mapped_players}")
        st.write(f"Players with Projections: {matched_players}/{total_players} ({match_percentage:.1f}%)")
        
        if team_rosters:
            st.write(f"Teams Found: {len(team_rosters)}")
            for team_id, team_data in team_rosters.items():
                st.write(f"- {team_data['name']}: {len(team_data['players'])} players")
    
    # Display the dataframe
    try:
        st.dataframe(
            simplified_df, 
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Name"),
                "Percent Owned": st.column_config.NumberColumn("% Owned", format="%.2f"),
                "Eligible Positions": st.column_config.TextColumn("Positions"),
                "Projected Points": st.column_config.NumberColumn("Proj. Points", format="%.1f"),
                "Team": st.column_config.TextColumn("Team")
            }
        )
    except Exception as e:
        logger.error(f"Error displaying dataframe: {e}")
        st.error(f"Error displaying player data: {e}")
        
        # Display dataframe column info for debugging
        st.warning("Debug: Dataframe Column Types")
        st.write(simplified_df.dtypes)
        
        # Try alternative display method
        st.warning("Attempting alternative display method")
        st.write(simplified_df)
    
    st.write(f"*\*Showing players with at least 0.05% ownership*")
else:
    st.error("Failed to fetch player data. Please try again later.")
