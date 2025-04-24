"""
Utilities for waiver wire analysis.
"""
import pandas as pd
from typing import Dict, Any, List, Tuple, Set

def find_waiver_replacements(
    original_roster: Dict[str, List[Dict[str, Any]]],
    combined_roster: Dict[str, List[Dict[str, Any]]],
    processed_roster: List[Dict[str, Any]],
    processed_free_agents: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find waiver wire replacements that improve the roster.
    
    Args:
        original_roster: Original optimized roster
        combined_roster: Optimized roster including free agents
        processed_roster: List of processed roster players
        processed_free_agents: List of processed free agents
        
    Returns:
        List of recommended pickups
    """
    # Save original optimal lineup for comparison
    original_starters = set()
    for position, players in original_roster.items():
        if position != "BN" and position != "IL":  # Exclude bench and IL
            for player in players:
                original_starters.add(player['name'])
    
    # Get new starters
    new_starters = set()
    new_starter_details = {}
    for position, players in combined_roster.items():
        if position != "BN" and position != "IL":  # Exclude bench and IL
            for player in players:
                new_starters.add(player['name'])
                new_starter_details[player['name']] = {
                    'position': position,
                    'projected_points': player['projected_points'],
                    'injury_status': player.get('injury_status')
                }
    
    # Find free agents who made it into starting lineup
    free_agent_names = {player['name'] for player in processed_free_agents}
    recommended_free_agents = new_starters.intersection(free_agent_names)
    
    # Create recommendations with details
    recommended_pickups = []
    for fa_name in recommended_free_agents:
        # Find the free agent in the processed free agents list
        fa = next((p for p in processed_free_agents if p['name'] == fa_name), None)
        
        if fa:
            # Find position they'd play
            position = new_starter_details[fa_name]['position']
            
            # Find who they replace (player at same position not in new lineup)
            potential_replacements = []
            for original_player in processed_roster:
                # Skip players who are IL-eligible as they shouldn't be dropped for healthy players
                if original_player.get('injury_status') in ["TEN_DAY_DL", "SUSPENSION", "SIXTY_DAY_DL", "OUT", "FIFTEEN_DAY_DL"]:
                    continue
                    
                # Check if the player is not in the new starters
                if original_player['name'] not in new_starters:
                    # Check if they can play the same position
                    if position in original_player['positions'] or \
                       (position == "UTIL" and original_player['is_hitter']) or \
                       (position == "P" and original_player['is_pitcher']):
                        potential_replacements.append({
                            'name': original_player['name'],
                            'projected_points': original_player['projected_points']
                        })
            
            # Sort by projected points to find the most likely replacement
            if potential_replacements:
                potential_replacements.sort(key=lambda p: p['projected_points'], reverse=True)
                replaced_player = potential_replacements[0]
                
                # Calculate projected points improvement
                improvement = fa['projected_points'] - replaced_player['projected_points']
                
                if improvement > 0:
                    recommended_pickups.append({
                        'Add': fa_name,
                        'Position': position,
                        'Drop': replaced_player['name'],
                        'Proj. Points Improvement': improvement,
                        'FA Percent Owned': fa.get('percent_owned', 0),
                        'Injury Status': fa.get('injury_status', '')
                    })
    
    # Sort recommendations by projected points improvement
    recommended_pickups.sort(key=lambda r: r['Proj. Points Improvement'], reverse=True)
    
    return recommended_pickups

def analyze_post_trade_waiver_options(
    team_players: List[Dict[str, Any]],
    free_agents: List[Dict[str, Any]],
    roster_slots: Dict[str, int]
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], float]:
    """
    Analyze waiver options after a trade.
    
    Args:
        team_players: List of team players after trade
        free_agents: List of available free agents
        roster_slots: Dictionary of roster slots and counts
        
    Returns:
        Tuple of (optimized roster with free agents, recommended pickups, new roster strength)
    """
    from utils.roster_utils import optimize_roster
    
    # Optimize roster without free agents
    original_roster, original_strength = optimize_roster(team_players, roster_slots)
    
    # Calculate total roster size (including bench)
    total_roster_size = sum(roster_slots.values()) + roster_slots.get("BN", 3)  # Default to 3 bench spots if not specified
    
    # Sort free agents by projected points (highest first)
    sorted_free_agents = sorted(free_agents, key=lambda p: p['projected_points'], reverse=True)
    
    # Limit the number of free agents to consider to prevent excessive computation
    # and ensure we don't exceed roster limits
    top_free_agents = sorted_free_agents[:50]  # Consider only top 50 free agents
    
    # Combine team roster with free agents
    combined_players = team_players + top_free_agents
    
    # Optimize combined roster
    combined_roster, combined_strength = optimize_roster(combined_players, roster_slots)
    
    # Find recommended pickups
    recommended_pickups = find_waiver_replacements(
        original_roster,
        combined_roster,
        team_players,
        top_free_agents
    )
    
    # Limit recommendations to a reasonable number (max 3 bench spots)
    max_recommendations = 3
    if len(recommended_pickups) > max_recommendations:
        recommended_pickups = recommended_pickups[:max_recommendations]
    
    # Create a new optimized roster with only the recommended pickups
    if recommended_pickups:
        # Get names of recommended free agents
        recommended_names = [pickup['Add'] for pickup in recommended_pickups]
        
        # Filter free agents to only include recommendations
        recommended_free_agents = [fa for fa in top_free_agents if fa['name'] in recommended_names]
        
        # Combine team roster with only recommended free agents
        limited_combined_players = team_players + recommended_free_agents
        
        # Optimize this limited roster
        limited_roster, limited_strength = optimize_roster(limited_combined_players, roster_slots)
        
        return limited_roster, recommended_pickups, limited_strength
    else:
        return original_roster, [], original_strength
