from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str
    entrypoint: str
    description: str = ""
    author: str = ""
    min_core_version: str = ""
    required_settings: list[str] = field(default_factory=list)
    required_services: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "ModuleManifest":
        with path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        return cls(
            module_id=payload["id"],
            name=payload.get("name", payload["id"]),
            version=payload["version"],
            entrypoint=payload.get("entrypoint", "cog"),
            description=payload.get("description", ""),
            author=payload.get("author", ""),
            min_core_version=payload.get("min_core_version", ""),
            required_settings=list(payload.get("required_settings", [])),
            required_services=list(payload.get("required_services", [])),
        )

    def to_import_path(self, package_root: str = "installed_modules") -> str:
        normalized_entrypoint = self.entrypoint.replace("/", ".").replace("\\", ".").strip(".")
        return f"{package_root}.{self.module_id}.{normalized_entrypoint}"
