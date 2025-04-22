"""
Application settings and configuration.
"""
import pytz
from typing import Dict, Any

# Timezone settings
EST = pytz.timezone('US/Eastern')

# Default league settings
DEFAULT_LEAGUE_ID = "339466431"

# Roster slot structure
DEFAULT_ROSTER_SLOTS = {
    "C": 1,
    "1B": 1,
    "2B": 1, 
    "3B": 1,
    "SS": 1,
    "OF": 3,
    "UTIL": 1,
    "P": 7
}
