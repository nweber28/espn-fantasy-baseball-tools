"""
Utilities for standardizing and processing player names.
"""
from unidecode import unidecode
from typing import Dict, Any, Optional

def stem_name(name: str) -> str:
    """
    Standardize player name for matching.
    
    Args:
        name: The player name to standardize
        
    Returns:
        Standardized name for matching across different data sources
    """
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
