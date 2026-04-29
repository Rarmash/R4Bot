from __future__ import annotations

import sys

from core.module_manifest import ModuleManifest
from core.module_state import ModuleStateStore


class ModuleLoader:
    def __init__(self, bot, config_service):
        self.bot = bot
        self.config = config_service
        self.state_store = ModuleStateStore(self.config.paths.module_state_file)
        self.loaded_builtin_modules = []
        self.loaded_installed_modules = []
        self.failed_builtin_modules = []
        self.failed_installed_modules = []
        self._prepare_import_path()

    def _prepare_import_path(self):
        root_path = str(self.config.paths.root)
        if root_path not in sys.path:
            sys.path.insert(0, root_path)

    def load_enabled_modules(self):
        self.load_builtin_modules()
        self.load_installed_modules()
        self._print_summary()

    def load_builtin_modules(self):
        for module_name in self.config.get_builtin_modules():
            extension_path = self._resolve_builtin_extension(module_name)
            self._load_extension(extension_path, module_name, source="builtin")

    @staticmethod
    def _resolve_builtin_extension(module_name: str) -> str:
        return f"core.builtin_modules.{module_name}"

    def load_installed_modules(self):
        for module_id in self.state_store.get_enabled_module_ids():
            manifest_path = self.config.paths.installed_modules_dir / module_id / "module.json"
            if not manifest_path.exists():
                self._record_error(module_id, "installed", "Installed module is enabled but missing module.json")
                continue

            try:
                manifest = ModuleManifest.from_file(manifest_path)
                missing_dependencies = self._get_missing_required_dependencies(manifest)
                if missing_dependencies:
                    self._record_error(
                        module_id,
                        "installed",
                        f"Missing required enabled modules: {', '.join(missing_dependencies)}",
                    )
                    continue
                self._load_extension(manifest.to_import_path(), module_id, source="installed")
            except Exception as exc:
                self._record_error(module_id, "installed", f"Failed to load installed module: {exc}")

    def _load_extension(self, extension_path: str, module_name: str, source: str):
        try:
            self.bot.load_extension(extension_path)
            if source == "builtin":
                self.loaded_builtin_modules.append(module_name)
            else:
                self.loaded_installed_modules.append(module_name)
        except Exception as exc:
            self._record_error(module_name, source, str(exc))

    def _get_missing_required_dependencies(self, manifest: ModuleManifest) -> list[str]:
        installed = self.state_store.list_installed()
        builtin_modules = set(self.config.get_builtin_modules())
        missing = []
        for dependency_id in manifest.required_dependencies:
            if dependency_id in builtin_modules:
                continue
            dependency = installed.get(dependency_id)
            if not dependency or not dependency.get("enabled"):
                missing.append(dependency_id)
        return missing

    def _record_error(self, module_name: str, source: str, message: str):
        if source == "builtin" and module_name not in self.failed_builtin_modules:
            self.failed_builtin_modules.append(module_name)
        if source == "installed" and module_name not in self.failed_installed_modules:
            self.failed_installed_modules.append(module_name)

        print(f"Failed to load {source} module '{module_name}': {message}")
        services = getattr(self.bot, "r4_services", None)
        module_errors = getattr(services, "module_errors", None)
        if module_errors is not None:
            module_errors.record(module_name, source, message)

    def _print_summary(self):
        print(
            "Modules loaded:"
            f" builtin={len(self.loaded_builtin_modules)}"
            f", installed={len(self.loaded_installed_modules)}"
        )

        if self.failed_builtin_modules or self.failed_installed_modules:
            failed = self.failed_builtin_modules + self.failed_installed_modules
            print(f"Modules failed: {', '.join(failed)}")
