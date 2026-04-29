"""
Decay & Emergence Detector
===========================
Rules (directly from HLD §4.3):
  - decay_flag   → demand_index declined >15% over 3 consecutive monthly snapshots
  - emerging_flag → growth_rate >25% MoM for 2 consecutive periods
              OR skill newly appears in market data
"""
from typing import List


def detect_decay(demand_history: List[float], threshold: float = 0.15) -> bool:
    """
    demand_history: ordered list of demand_index values (oldest → newest).
    Requires at least 3 data points.
    Returns True if last 3 points show a >15% sustained decline.
    """
    if len(demand_history) < 3:
        return False
    last3 = demand_history[-3:]
    # Decline in both consecutive pairs
    d1 = (last3[0] - last3[1]) / (last3[0] + 1e-9)
    d2 = (last3[1] - last3[2]) / (last3[1] + 1e-9)
    return d1 > threshold and d2 > threshold


def detect_emerging(growth_rate_history: List[float],
                    is_new: bool = False,
                    threshold: float = 0.25) -> bool:
    """
    growth_rate_history: ordered list of MoM growth percentages.
    Returns True if last 2 growth rates exceed threshold OR skill is newly added.
    """
    if is_new:
        return True
    if len(growth_rate_history) < 2:
        return False
    return growth_rate_history[-1] > threshold and growth_rate_history[-2] > threshold


def evaluate_skill_market(market_records: list) -> dict:
    """
    market_records: list of MarketSkillData.to_dict() ordered by captured_at asc.
    Returns dict with decay_flag, emerging_flag, latest_demand, growth_rate.
    """
    if not market_records:
        return {'decay_flag': False, 'emerging_flag': False, 'latest_demand': 0.0, 'growth_rate': 0.0}

    demand_series      = [r['demand_index']  for r in market_records]
    growth_rate_series = [r['growth_rate']   for r in market_records]
    is_new             = len(market_records) == 1

    return {
        'decay_flag':     detect_decay(demand_series),
        'emerging_flag':  detect_emerging(growth_rate_series, is_new=is_new),
        'latest_demand':  demand_series[-1],
        'growth_rate':    growth_rate_series[-1],
    }
