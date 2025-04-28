"""
Utilities for waiver wire analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Set

def find_waiver_replacements_vectorized(
    original_roster: Dict[str, List[Dict[str, Any]]],
    combined_roster: Dict[str, List[Dict[str, Any]]],
    processed_roster: List[Dict[str, Any]],
    processed_free_agents: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find waiver wire replacements that improve the roster using vectorized operations.
    
    Args:
        original_roster: Original optimized roster
        combined_roster: Optimized roster including free agents
        processed_roster: List of processed roster players
        processed_free_agents: List of processed free agents
        
    Returns:
        List of recommended pickups for both starters and bench players
    """
    # Convert to dataframes for vectorized operations
    original_df = pd.DataFrame([
        {'name': player['name'], 'position': pos, 'projected_points': player.get('projected_points', 0), 
         'injury_status': player.get('injury_status', ''), 'is_bench_or_il': pos in ["BN", "IL"]}
        for pos, players in original_roster.items()
        for player in players
    ])
    
    combined_df = pd.DataFrame([
        {'name': player['name'], 'position': pos, 'projected_points': player.get('projected_points', 0), 
         'injury_status': player.get('injury_status', ''), 'is_bench_or_il': pos in ["BN", "IL"]}
        for pos, players in combined_roster.items()
        for player in players
    ])
    
    # Create free agent dataframe
    fa_df = pd.DataFrame(processed_free_agents)
    
    # Create a roster dataframe for easier processing
    roster_df = pd.DataFrame(processed_roster)
    
    # Get original and new starters using dataframe operations
    original_starters = set(original_df[~original_df['is_bench_or_il']]['name'])
    new_starters = set(combined_df[~combined_df['is_bench_or_il']]['name'])
    
    # Get original and new bench players
    original_bench = set(original_df[original_df['position'] == 'BN']['name'])
    new_bench = set(combined_df[combined_df['position'] == 'BN']['name'])
    
    # Create lookups for player details
    new_starter_details = combined_df[~combined_df['is_bench_or_il']].set_index('name').to_dict('index')
    new_bench_details = combined_df[combined_df['position'] == 'BN'].set_index('name').to_dict('index') if not combined_df[combined_df['position'] == 'BN'].empty else {}
    
    # Find free agents who made it into starting lineup or bench
    fa_names = set(fa_df['name'])
    recommended_starter_fas = list(new_starters.intersection(fa_names))
    recommended_bench_fas = list(new_bench.intersection(fa_names))
    
    # Create recommendations with details
    recommended_pickups = []
    
    # Process starter recommendations
    for fa_name in recommended_starter_fas:
        # Find the free agent in the processed free agents list
        fa = fa_df[fa_df['name'] == fa_name].iloc[0].to_dict() if not fa_df[fa_df['name'] == fa_name].empty else None
        
        if fa:
            # Find position they'd play
            position = new_starter_details[fa_name]['position']
            
            # Create a mask for potential replacements
            # Skip players who are IL-eligible
            il_eligible_mask = ~roster_df['injury_status'].isin(["TEN_DAY_DL", "SUSPENSION", "SIXTY_DAY_DL", "OUT", "FIFTEEN_DAY_DL"])
            # Players not in new starters
            not_in_new_starters = ~roster_df['name'].isin(new_starters)
            
            # Position eligibility check
            if position == "UTIL":
                position_eligible = roster_df['is_hitter']
            elif position == "P":
                position_eligible = roster_df['is_pitcher']
            else:
                # Check if position is in the positions list
                position_eligible = roster_df['positions'].apply(lambda x: position in x)
            
            # Combine all conditions
            potential_replacements_mask = il_eligible_mask & not_in_new_starters & position_eligible
            potential_replacements = roster_df[potential_replacements_mask].sort_values('projected_points', ascending=False)
            
            # If we found potential replacements
            if not potential_replacements.empty:
                replaced_player = potential_replacements.iloc[0]
                
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
    
    # Process bench recommendations
    for fa_name in recommended_bench_fas:
        # Skip if this FA is already recommended as a starter
        if fa_name in recommended_starter_fas:
            continue
            
        # Find the free agent in the processed free agents list
        fa = fa_df[fa_df['name'] == fa_name].iloc[0].to_dict() if not fa_df[fa_df['name'] == fa_name].empty else None
        
        if fa:
            # Create a mask for potential bench replacements
            # Skip players who are IL-eligible
            il_eligible_mask = ~roster_df['injury_status'].isin(["TEN_DAY_DL", "SUSPENSION", "SIXTY_DAY_DL", "OUT", "FIFTEEN_DAY_DL"])
            # Players not in new starters or new bench (except the ones we're replacing)
            not_in_new_roster = ~roster_df['name'].isin(new_starters.union(new_bench))
            
            # Combine conditions
            potential_replacements_mask = il_eligible_mask & not_in_new_roster
            potential_replacements = roster_df[potential_replacements_mask].sort_values('projected_points', ascending=False)
            
            # If we found potential replacements
            if not potential_replacements.empty:
                replaced_player = potential_replacements.iloc[0]
                
                # Calculate projected points improvement
                improvement = fa['projected_points'] - replaced_player['projected_points']
                
                if improvement > 0:
                    # Determine position based on player type
                    if fa.get('is_pitcher', False):
                        position = "P (Bench)"
                    else:
                        position = "Bench"
                        
                    recommended_pickups.append({
                        'Add': fa_name,
                        'Position': position,
                        'Drop': replaced_player['name'],
                        'Proj. Points Improvement': improvement,
                        'FA Percent Owned': fa.get('percent_owned', 0),
                        'Injury Status': fa.get('injury_status', '')
                    })
    
    # Sort recommendations by projected points improvement
    recommended_pickups = sorted(recommended_pickups, key=lambda r: r['Proj. Points Improvement'], reverse=True)
    
    return recommended_pickups

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
    return find_waiver_replacements_vectorized(
        original_roster,
        combined_roster,
        processed_roster,
        processed_free_agents
    )

def analyze_post_trade_waiver_options(
    team_players: List[Dict[str, Any]],
    free_agents: List[Dict[str, Any]],
    roster_slots: Dict[str, int]
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], float]:
    """
    Analyze waiver options after a trade using vectorized operations.
    
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
    
    # Convert to DataFrame for faster sorting
    fa_df = pd.DataFrame(free_agents) if free_agents else pd.DataFrame()
    if not fa_df.empty:
        # Sort free agents by projected points (highest first)
        fa_df = fa_df.sort_values('projected_points', ascending=False)
        
        # Limit the number of free agents to consider to prevent excessive computation
        top_free_agents = fa_df.head(50).to_dict('records')  # Consider only top 50 free agents
        
        # Combine team roster with free agents
        combined_players = team_players + top_free_agents
        
        # Optimize combined roster
        combined_roster, combined_strength = optimize_roster(combined_players, roster_slots)
        
        try:
            # Find recommended pickups
            recommended_pickups = find_waiver_replacements_vectorized(
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
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error finding waiver replacements: {str(e)}")
            # Continue without recommendations if there's an error
    
    return original_roster, [], original_strength
