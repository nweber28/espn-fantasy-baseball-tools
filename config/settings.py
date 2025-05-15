"""
Application settings and configuration.
"""
import pytz
from typing import Dict, Any

# Timezone settings
EST = pytz.timezone('US/Eastern')

# Default league settings
DEFAULT_LEAGUE_ID = "1310196412"

cookies = {
    'SWID': '{F0D1A87D-25A0-4E55-91A8-7D25A0EE55B9}',
    'espn_s2': 'AEAqLe%2F3TkwypXIhOSYksPyhwFD8D9vJP1mOo9uoQ2J%2Bd9LuZpNb7Q0dlgBNVLZYuN%2Bkt0oOynvT4iWTdMjJuAgKiZyIBKkwy6yDqyeSoGL58M%2FgoaCjGels8M8yIyXwJkIFByblOs2N3q7ZXHlpkmgmQ3LrAWHHWnROF89KqYLpL%2FDp2Mayd5eXWTegXVMloXCReuPSq3gcHRf42tqDvlpSSyVraPIqAw%2BU4lWvnzV1YJvIINKKWF%2FrQxfHrstxIHYwhJ8kLRZqryrSvnYzIZww',
}
# Roster slot structure
DEFAULT_ROSTER_SLOTS = {
    "C": 1,
    "1B": 1,
    "2B": 1, 
    "3B": 1,
    "SS": 1,
    "OF": 3,
    "UTIL": 1,
    "P": 7,
    "BN": 3  # Explicitly define bench slots
}
