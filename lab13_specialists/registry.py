"""Specialist registry for Lab 13."""

from __future__ import annotations

from typing import Dict, Type

from lab13_specialists.specialists import (
    DomainSpecialist,
    PlacementCoordinatorSpecialist,
    SchedulingCoordinatorSpecialist,
)


class SpecialistRegistry:
    """Pluggable registry matching the Chapter 3 pseudocode pattern."""

    def __init__(self):
        self._registry: Dict[str, DomainSpecialist] = {}

    def register(self, specialist: DomainSpecialist) -> DomainSpecialist:
        self._registry[specialist.domain] = specialist
        return specialist

    def get(self, domain: str) -> DomainSpecialist:
        if domain not in self._registry:
            raise KeyError(f"No specialist registered for domain '{domain}'")
        return self._registry[domain]

    def domains(self) -> list[str]:
        return sorted(self._registry.keys())


registry = SpecialistRegistry()
registry.register(PlacementCoordinatorSpecialist())
registry.register(SchedulingCoordinatorSpecialist())

__all__ = ["SpecialistRegistry", "registry"]
