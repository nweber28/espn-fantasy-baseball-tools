"""
Service for interacting with ESPN Fantasy Baseball API.
"""
import requests
import logging
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
import streamlit as st

logger = logging.getLogger(__name__)

class ESPNService:
    """Service for interacting with ESPN Fantasy Baseball API."""
    
    BASE_URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb"
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_player_data(season_id: int = 2025) -> Optional[Dict[str, Any]]:
        """
        Fetch all player data from ESPN.
        
        Args:
            season_id: The season ID to fetch data for
            
        Returns:
            Dictionary of player data or None if request fails
        """
        url = f"{ESPNService.BASE_URL}/seasons/{season_id}/players?scoringPeriodId=0&view=players_wl"
        
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
            return None
    
    @staticmethod
    @st.cache_data(ttl=3600, show_spinner=False)
    def fetch_teams_data(league_id: str, season_id: int = 2025) -> Optional[Dict[str, Any]]:
        """
        Fetch teams data for a specific league.
        
        Args:
            league_id: The ESPN league ID
            season_id: The season ID to fetch data for
            
        Returns:
            Dictionary of teams data or None if request fails
        """
        url = f"{ESPNService.BASE_URL}/seasons/{season_id}/segments/0/leagues/{league_id}"
        
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
            return None
    
    @staticmethod
    @st.cache_data(ttl=3600, show_spinner=False)
    def fetch_team_rosters(league_id: str, season_id: int = 2025) -> Optional[Dict[str, Any]]:
        """
        Fetch team rosters for a specific league.
        
        Args:
            league_id: The ESPN league ID
            season_id: The season ID to fetch data for
            
        Returns:
            Dictionary of team rosters or None if request fails
        """
        url = f"{ESPNService.BASE_URL}/seasons/{season_id}/segments/0/leagues/{league_id}?view=mRoster"
        
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
            
            if 'teams' in data:
                logger.info(f"Successfully fetched roster data with {len(data['teams'])} teams")
            else:
                logger.warning(f"Roster data missing 'teams' key. Keys: {list(data.keys())}")
                
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ESPN team rosters: {e}")
            return None
