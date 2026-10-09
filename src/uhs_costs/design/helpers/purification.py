"""Purification design data class and constructor.

For use and import into inputs.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Purification:
    """Purification assumptions used by the design and cost models.

    Parameters
    ----------
    purification_factor:
        HyStories cost scalar used in the purification CAPEX/OPEX correlations.
    hydrogen_recovery:
        Fraction of gross withdrawn hydrogen delivered as usable hydrogen after
        purification. This is an operational/physical parameter, not a cost
        scalar.
    """

    purification_factor: float
    hydrogen_recovery: float


def construct_purification(
    purification_factor: float,
    hydrogen_recovery: float,
) -> Purification:
    """Construct purification assumptions and validate their physical range."""

    if purification_factor < 0:
        raise ValueError("purification_factor cannot be negative.")

    if not 0 < hydrogen_recovery <= 1:
        raise ValueError("hydrogen_recovery must be > 0 and <= 1.")

    return Purification(
        purification_factor=purification_factor,
        hydrogen_recovery=hydrogen_recovery,
    )


def gross_withdrawal_from_net(
    net_withdrawal: float,
    hydrogen_recovery: float,
) -> float:
    """Return gross pre-purification withdrawal for a net usable H2 flow.

    This helper is intentionally internal-facing. Public storage flows remain
    defined on the CEM/system-interface basis (usable post-purification H2).
    """

    if net_withdrawal < 0:
        raise ValueError("net_withdrawal cannot be negative.")

    if not 0 < hydrogen_recovery <= 1:
        raise ValueError("hydrogen_recovery must be > 0 and <= 1.")

    return net_withdrawal / hydrogen_recovery
