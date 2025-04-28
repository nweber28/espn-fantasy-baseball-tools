"""
Unit test to verify waiver wire recommendations for bench players.
"""
import unittest
import pandas as pd
import numpy as np
from utils.waiver_utils import find_waiver_replacements_vectorized

class TestWaiverBenchRecommendations(unittest.TestCase):
    def test_bench_player_recommendations(self):
        """Test that waiver wire recommendations include bench player upgrades."""
        # Create original roster with starters and bench players
        original_roster = {
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
        
        # Create combined roster with a free agent replacing a bench player
        combined_roster = {
            'C': [{'name': 'Catcher 1', 'projected_points': 50}],
            '1B': [{'name': 'First Base 1', 'projected_points': 60}],
            'OF': [
                {'name': 'Outfielder 1', 'projected_points': 70},
                {'name': 'Outfielder 2', 'projected_points': 65},
                {'name': 'Outfielder 3', 'projected_points': 55}
            ],
            'SP': [{'name': 'Starter 1', 'projected_points': 80}],
            'BN': [
                {'name': 'Better Bench Hitter', 'projected_points': 65},  # Free agent replacement
                {'name': 'Bench Pitcher', 'projected_points': 40}
            ],
            'IL': []
        }
        
        # Create processed roster
        processed_roster = [
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
        
        # Create processed free agents
        processed_free_agents = [
            {
                'name': 'Better Bench Hitter',
                'positions': ['2B', 'SS'],
                'projected_points': 65,
                'is_pitcher': False,
                'is_hitter': True,
                'percent_owned': 10.2,
                'injury_status': 'ACTIVE'
            }
        ]
        
        # Get recommendations
        recommendations = find_waiver_replacements_vectorized(
            original_roster,
            combined_roster,
            processed_roster,
            processed_free_agents
        )
        
        # Print recommendations for debugging
        print("Waiver Wire Recommendations:")
        for rec in recommendations:
            print(f"Add: {rec['Add']}, Drop: {rec['Drop']}, Position: {rec['Position']}, Improvement: {rec['Proj. Points Improvement']}")
        
        # Check that we have recommendations
        self.assertTrue(len(recommendations) > 0, "Should have at least one recommendation")
        
        # Check for bench upgrade recommendation
        bench_upgrade = next((r for r in recommendations if r['Add'] == 'Better Bench Hitter'), None)
        self.assertIsNotNone(bench_upgrade, "Should recommend Better Bench Hitter")
        
        # Check that the bench upgrade is for the correct player
        self.assertEqual(bench_upgrade['Drop'], 'Bench Hitter', "Should recommend dropping Bench Hitter")
        
        # Check the improvement value
        self.assertEqual(bench_upgrade['Proj. Points Improvement'], 20.0, "Improvement should be 20.0 points")

if __name__ == '__main__':
    unittest.main()
