"""
Unit tests for waiver wire utilities.
"""
import unittest
import pandas as pd
import numpy as np
from utils.waiver_utils import find_waiver_replacements_vectorized, find_waiver_replacements, analyze_post_trade_waiver_options

class TestFindWaiverReplacements(unittest.TestCase):
    def setUp(self):
        # Create sample rosters and free agents for testing
        
        # Original roster with starters and bench players
        self.original_roster = {
            'C': [{'name': 'Catcher 1', 'projected_points': 50}],
            '1B': [{'name': 'First Base 1', 'projected_points': 60}],
            'OF': [
                {'name': 'Outfielder 1', 'projected_points': 70},
                {'name': 'Outfielder 2', 'projected_points': 65},
                {'name': 'Outfielder 3', 'projected_points': 55}
            ],
            'SP': [{'name': 'Starter 1', 'projected_points': 80}],
            'BN': [
                {'name': 'Bench Hitter', 'projected_points': 45},
                {'name': 'Bench Pitcher', 'projected_points': 40}
            ],
            'IL': []
        }
        
        # Combined roster with free agents replacing some players
        self.combined_roster = {
            'C': [{'name': 'Catcher 1', 'projected_points': 50}],
            '1B': [{'name': 'Better First Base', 'projected_points': 75}],  # Free agent replacement
            'OF': [
                {'name': 'Outfielder 1', 'projected_points': 70},
                {'name': 'Better Outfielder', 'projected_points': 85},  # Free agent replacement
                {'name': 'Outfielder 3', 'projected_points': 55}
            ],
            'SP': [{'name': 'Starter 1', 'projected_points': 80}],
            'BN': [
                {'name': 'Better Bench Hitter', 'projected_points': 65},  # Free agent replacement
                {'name': 'First Base 1', 'projected_points': 60}  # Moved to bench
            ],
            'IL': []
        }
        
        # Processed roster players
        self.processed_roster = [
            {
                'name': 'Catcher 1',
                'positions': ['C'],
                'projected_points': 50,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'First Base 1',
                'positions': ['1B'],
                'projected_points': 60,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Outfielder 1',
                'positions': ['OF'],
                'projected_points': 70,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Outfielder 2',
                'positions': ['OF'],
                'projected_points': 65,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Outfielder 3',
                'positions': ['OF'],
                'projected_points': 55,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Starter 1',
                'positions': ['SP'],
                'projected_points': 80,
                'is_pitcher': True,
                'is_hitter': False,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Bench Hitter',
                'positions': ['1B', 'OF'],
                'projected_points': 45,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Bench Pitcher',
                'positions': ['RP'],
                'projected_points': 40,
                'is_pitcher': True,
                'is_hitter': False,
                'injury_status': 'ACTIVE'
            }
        ]
        
        # Processed free agents
        self.processed_free_agents = [
            {
                'name': 'Better First Base',
                'positions': ['1B'],
                'projected_points': 75,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 15.5,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Better Outfielder',
                'positions': ['OF'],
                'projected_points': 85,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 25.3,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Better Bench Hitter',
                'positions': ['2B', 'SS'],
                'projected_points': 65,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 10.2,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Worse Free Agent',
                'positions': ['C'],
                'projected_points': 30,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 5.1,
                'injury_status': 'ACTIVE'
            }
        ]

    def test_find_waiver_replacements_identifies_starter_upgrades(self):
        """Test that find_waiver_replacements correctly identifies starter upgrades."""
        recommendations = find_waiver_replacements_vectorized(
            self.original_roster,
            self.combined_roster,
            self.processed_roster,
            self.processed_free_agents
        )
        
        # Check that we have recommendations
        self.assertTrue(len(recommendations) > 0, "Should have at least one recommendation")
        
        # Check that the recommendations include the expected starter upgrades
        starter_upgrades = [r for r in recommendations if r['Position'] in ['1B', 'OF']]
        self.assertTrue(len(starter_upgrades) >= 2, "Should have at least 2 starter upgrades")
        
        # Check specific recommendations
        first_base_upgrade = next((r for r in recommendations if r['Add'] == 'Better First Base'), None)
        self.assertIsNotNone(first_base_upgrade, "Should recommend Better First Base")
        self.assertEqual(first_base_upgrade['Position'], '1B', "Position should be 1B")
        
        outfield_upgrade = next((r for r in recommendations if r['Add'] == 'Better Outfielder'), None)
        self.assertIsNotNone(outfield_upgrade, "Should recommend Better Outfielder")
        self.assertEqual(outfield_upgrade['Position'], 'OF', "Position should be OF")
    
    def test_find_waiver_replacements_identifies_bench_upgrades(self):
        """Test that find_waiver_replacements correctly identifies bench upgrades."""
        # Modify the combined roster to include a bench upgrade
        combined_roster_with_bench_upgrade = self.combined_roster.copy()
        
        recommendations = find_waiver_replacements_vectorized(
            self.original_roster,
            combined_roster_with_bench_upgrade,
            self.processed_roster,
            self.processed_free_agents
        )
        
        # Check for bench upgrades
        bench_upgrades = [r for r in recommendations if r['Position'] == 'Bench' or r['Position'] == 'P (Bench)']
        
        # This test might fail if the current implementation doesn't support bench upgrades
        # In that case, this test identifies the issue
        self.assertTrue(len(bench_upgrades) > 0, "Should have at least one bench upgrade recommendation")
        
        # If bench upgrades are supported, check the specific recommendation
        if len(bench_upgrades) > 0:
            bench_upgrade = next((r for r in recommendations if r['Add'] == 'Better Bench Hitter'), None)
            self.assertIsNotNone(bench_upgrade, "Should recommend Better Bench Hitter")
    
    def test_find_waiver_replacements_sorts_by_improvement(self):
        """Test that find_waiver_replacements sorts recommendations by improvement."""
        recommendations = find_waiver_replacements_vectorized(
            self.original_roster,
            self.combined_roster,
            self.processed_roster,
            self.processed_free_agents
        )
        
        # Check that recommendations are sorted by improvement (descending)
        if len(recommendations) >= 2:
            for i in range(len(recommendations) - 1):
                self.assertGreaterEqual(
                    recommendations[i]['Proj. Points Improvement'],
                    recommendations[i + 1]['Proj. Points Improvement'],
                    "Recommendations should be sorted by improvement (descending)"
                )
    
    def test_find_waiver_replacements_handles_empty_inputs(self):
        """Test that find_waiver_replacements handles empty inputs gracefully."""
        # Test with empty free agents
        recommendations = find_waiver_replacements_vectorized(
            self.original_roster,
            self.original_roster,  # No changes
            self.processed_roster,
            []  # Empty free agents
        )
        
        self.assertEqual(len(recommendations), 0, "Should have no recommendations with empty free agents")
        
        # Test with empty roster
        recommendations = find_waiver_replacements_vectorized(
            {},  # Empty original roster
            {},  # Empty combined roster
            [],  # Empty processed roster
            self.processed_free_agents
        )
        
        self.assertEqual(len(recommendations), 0, "Should have no recommendations with empty roster")


class TestAnalyzePostTradeWaiverOptions(unittest.TestCase):
    def test_analyze_post_trade_waiver_options(self):
        """Test that analyze_post_trade_waiver_options correctly identifies waiver options after a trade."""
        # Create sample team players after trade
        team_players = [
            {
                'name': 'Player 1',
                'positions': ['1B'],
                'projected_points': 60,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Player 2',
                'positions': ['OF'],
                'projected_points': 70,
                'is_pitcher': False,
                'is_hitter': True,
                'injury_status': 'ACTIVE'
            }
        ]
        
        # Create sample free agents
        free_agents = [
            {
                'name': 'Free Agent 1',
                'positions': ['1B'],
                'projected_points': 80,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 15.5,
                'injury_status': 'ACTIVE'
            },
            {
                'name': 'Free Agent 2',
                'positions': ['OF'],
                'projected_points': 50,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 5.3,
                'injury_status': 'ACTIVE'
            }
        ]
        
        # Define roster slots
        roster_slots = {
            '1B': 1,
            'OF': 1,
            'BN': 1
        }
        
        # Run the analysis
        optimized_roster, recommendations, strength = analyze_post_trade_waiver_options(
            team_players,
            free_agents,
            roster_slots
        )
        
        # Check that we have an optimized roster
        self.assertIsNotNone(optimized_roster, "Should have an optimized roster")
        
        # Check that we have recommendations
        self.assertTrue(len(recommendations) > 0, "Should have at least one recommendation")
        
        # Check that the recommendations include the expected upgrade
        upgrade = next((r for r in recommendations if r['Add'] == 'Free Agent 1'), None)
        self.assertIsNotNone(upgrade, "Should recommend Free Agent 1")
        
        # Check that the strength is calculated
        self.assertIsNotNone(strength, "Should calculate roster strength")


if __name__ == '__main__':
    unittest.main()
