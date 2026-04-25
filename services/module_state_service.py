from __future__ import annotations

from core.module_state import ModuleStateStore
from services.config_service import ConfigService


class ModuleStateService:
    def __init__(self, config_service: ConfigService):
        self.config = config_service
        self.store = ModuleStateStore(self.config.paths.module_state_file)

    def list_installed(self) -> dict[str, dict]:
        return self.store.list_installed()

    def is_builtin_enabled(self, module_id: str) -> bool:
        return module_id in self.config.get_builtin_modules()

    def is_installed_enabled(self, module_id: str) -> bool:
        return bool(self.store.list_installed().get(module_id, {}).get("enabled"))

    def is_module_enabled(self, module_id: str) -> bool:
        return self.is_builtin_enabled(module_id) or self.is_installed_enabled(module_id)
