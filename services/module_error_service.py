from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ModuleErrorRecord:
    module_id: str
    source: str
    message: str
    created_at: datetime


class ModuleErrorService:
    def __init__(self):
        self._errors: list[ModuleErrorRecord] = []

    def record(self, module_id: str, source: str, message: str):
        self._errors.append(
            ModuleErrorRecord(
                module_id=module_id,
                source=source,
                message=message,
                created_at=datetime.utcnow(),
            )
        )

    def clear(self, module_id: str | None = None):
        if module_id is None:
            self._errors.clear()
            return

        self._errors = [error for error in self._errors if error.module_id != module_id]

    def list(self) -> list[ModuleErrorRecord]:
        return list(self._errors)
