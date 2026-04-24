from __future__ import annotations

import sys

from core.module_manifest import ModuleManifest
from core.module_state import ModuleStateStore


class ModuleLoader:
    def __init__(self, bot, config_service):
        self.bot = bot
        self.config = config_service
        self.state_store = ModuleStateStore(self.config.paths.module_state_file)
        self._prepare_import_path()

    def _prepare_import_path(self):
        root_path = str(self.config.paths.root)
        if root_path not in sys.path:
            sys.path.insert(0, root_path)

    def load_enabled_modules(self):
        self.load_builtin_modules()
        self.load_installed_modules()

    def load_builtin_modules(self):
        for module_name in self.config.get_builtin_modules():
            self._load_extension(f"cogs.{module_name}", module_name, source="builtin")

    def load_installed_modules(self):
        for module_id in self.state_store.get_enabled_module_ids():
            manifest_path = self.config.paths.installed_modules_dir / module_id / "module.json"
            if not manifest_path.exists():
                print(f"Installed module '{module_id}' is enabled but missing module.json")
                continue

            try:
                manifest = ModuleManifest.from_file(manifest_path)
                self._load_extension(manifest.to_import_path(), module_id, source="installed")
            except Exception as exc:
                print(f"Failed to load installed module '{module_id}': {exc}")

    def _load_extension(self, extension_path: str, module_name: str, source: str):
        try:
            self.bot.load_extension(extension_path)
            print(f"Loaded {source} module '{module_name}'")
        except Exception as exc:
            print(f"Failed to load {source} module '{module_name}': {exc}")
