"""Well design data class and constructor.

For use and import into inputs.py
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Purification:
    purification_factor: float


def construct_purification(
    purification_factor: float
) -> Purification:

    return Purification(purification_factor=purification_factor)