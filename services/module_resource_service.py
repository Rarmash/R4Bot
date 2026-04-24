from __future__ import annotations

from pathlib import Path

from services.config_service import ConfigService


class ModuleResourceService:
    def __init__(self, config_service: ConfigService):
        self.config = config_service

    def get_resource_path(self, module_id: str, *parts: str) -> Path:
        if module_id in self.config.get_builtin_modules():
            resource_path = self.config.paths.root / "resources" / module_id
        else:
            resource_path = self.config.paths.installed_modules_dir / module_id / "resources"
        for part in parts:
            resource_path /= part
        return resource_path
