"""
Service for interacting with FanGraphs API.
"""
import requests
import logging
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional, List, Literal

logger = logging.getLogger(__name__)

class FanGraphsService:
    """Service for interacting with FanGraphs API."""
    
    BASE_URL = "https://www.fangraphs.com/api/fantasy/auction-calculator/data"
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_projections(player_type: Literal['batter', 'pitcher']) -> Optional[Dict[str, Any]]:
        """
        Fetch projections for batters or pitchers.
        
        Args:
            player_type: Type of player ('batter' or 'pitcher')
            
        Returns:
            Dictionary of projection data or None if request fails
        """
        # Different projection systems for batters vs pitchers
        proj_param = "rthebatx" if player_type == "batter" else "ratcdc"
        
        params = {
            "teams": 10,
            "lg": "MLB",
            "dollars": 260,
            "mb": 1,
            "mp": 12,
            "msp": 5,
            "mrp": 2,
            "type": "bat" if player_type == "batter" else "pit",
            "players": "",
            "proj": proj_param,
            "split": "",
            "points": "p|0,0,0,1,2,3,4,1,0,1,1,1,-1,0,0,0|3,2,-2,5,1,-2,0,-1,0,-1,2",
            "rep": 0,
            "drp": 0,
            "pp": "C,SS,2B,3B,OF,1B",
            "pos": "1,1,1,1,3,1,0,0,0,1,5,2,0,3,0",
            "sort": "",
            "view": 0
        }
        
        headers = {
            "sec-ch-ua-platform": "macOS",
            "Referer": "https://www.fangraphs.com/fantasy-tools/auction-calculator",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            "sec-ch-ua-mobile": "?0"
        }
        
        try:
            logger.info(f"Fetching FanGraphs {player_type} data")
            response = requests.get(FanGraphsService.BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data:
                logger.info(f"Successfully fetched FanGraphs {player_type} data: {len(data['data'])} players")
            else:
                logger.warning(f"FanGraphs {player_type} data missing 'data' key")
                
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching FanGraphs {player_type} data: {e}")
            return None
