from __future__ import annotations

from dataclasses import dataclass

from domain.entities.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class Severity:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not normalized:
            raise DomainValidationError("severity must not be empty")
        object.__setattr__(self, "value", normalized)
