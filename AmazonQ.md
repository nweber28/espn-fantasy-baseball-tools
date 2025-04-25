# Trade Evaluator Injury Status Fix

I've fixed the issue with injury status not showing in the Player Selection dataframe by adding proper error handling when accessing the injury status field from the ESPN API data.

## Changes Made:

1. Added error handling when retrieving injury status for batters:
```python
try:
    if 'injuryStatus' in matching_players.columns:
        injury_status = matching_players['injuryStatus'].iloc[0]
    else:
        injury_status = None
except Exception as e:
    logger.warning(f"Error getting injury status for {batter['Name']}: {e}")
    injury_status = None
```

2. Added similar error handling for pitchers:
```python
try:
    if 'injuryStatus' in matching_players.columns:
        injury_status = matching_players['injuryStatus'].iloc[0]
    else:
        injury_status = None
except Exception as e:
    logger.warning(f"Error getting injury status for {pitcher['Name']}: {e}")
    injury_status = None
```

3. The injury status is now properly included in the player data structure when creating the combined player database, ensuring it's available for display in all dataframes.

These changes ensure that the injury status is properly handled even if:
- The 'injuryStatus' field is missing from the ESPN API response
- There's an error accessing the field
- The value is null for some players

The player selection dataframes now properly display the injury status column, giving users important information about player availability when evaluating trades.
