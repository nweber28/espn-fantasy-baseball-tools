"""
Utilities for processing and transforming data.
"""
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple
from config.constants import POSITION_MAP, TEAM_MAP
from utils.name_utils import stem_name

logger = logging.getLogger(__name__)

def convert_positions(positions_list: List[int]) -> str:
    """
    Convert position IDs to position names, showing only key positions.
    
    Args:
        positions_list: List of position IDs
        
    Returns:
        Comma-separated string of position names
    """
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

def map_team_abbr(abbr: str) -> str:
    """
    Standardize team abbreviations.
    
    Args:
        abbr: Team abbreviation
        
    Returns:
        Standardized team abbreviation
    """
    return TEAM_MAP.get(abbr, abbr)

def process_fangraphs_data(data: Dict[str, Any], player_type: str) -> pd.DataFrame:
    """
    Process FanGraphs data into a standardized DataFrame.
    
    Args:
        data: Raw FanGraphs data
        player_type: Type of player ('batter' or 'pitcher')
        
    Returns:
        Processed DataFrame
    """
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
        
        # Add specific stats based on player type
        if player_type == 'batter':
            try:
                pa = float(player.get("PA", 0))
                record.update({"PA": pa, "PtsPerPA": proj_pts / pa if pa else 0})
            except (ValueError, TypeError):
                record.update({"PA": 0, "PtsPerPA": 0})
        else:
            try:
                ip = float(player.get("IP", 0))
                record.update({"IP": ip, "PtsPerIP": proj_pts / ip if ip else 0})
            except (ValueError, TypeError):
                record.update({"IP": 0, "PtsPerIP": 0})
                
        records.append(record)
    
    logger.info(f"Processed {len(records)} {player_type} records")    
    return pd.DataFrame(records)

def process_team_rosters(roster_data: Dict[str, Any], teams_data: Dict[str, Any], 
                        espn_df: pd.DataFrame) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """
    Process team roster data from ESPN API.
    
    Args:
        roster_data: Raw roster data from ESPN API
        teams_data: Raw teams data from ESPN API
        espn_df: DataFrame of ESPN player data
        
    Returns:
        Tuple of (team_rosters, player_team_map)
    """
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
