"""HyStories APEX equations.

This module contains atomic HyStories-derived ABEX components.
Functions return EUR unless stated otherwise.
"""

def subsurface_contingency_cost_eur(
    epc_cost_eur: float,
    abex_fraction: float = 0.20, #hystories default
) -> float:
    """HyStories abex cost.

    Returns EUR.
    """

    return abex_fraction*epc_cost_eur
