from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


class ModuleMigrationError(Exception):
    """Raised when a module migration fails."""


@dataclass(frozen=True)
class ModuleMigrationContext:
    module_id: str
    from_version: str
    to_version: str
    module_dir: Path
    config_service: object

    @property
    def module_config_path(self) -> Path:
        return self.config_service.paths.module_configs_dir / f"{self.module_id}.json"

    @property
    def module_secrets_path(self) -> Path:
        return self.config_service.paths.secrets_dir / f"{self.module_id}.json"


class ModuleMigrationRunner:
    def __init__(self, config_service):
        self.config = config_service

    def run(self, module_id: str, module_dir: Path, from_version: str, to_version: str) -> list[str]:
        migrations_dir = module_dir / "migrations"
        if not migrations_dir.exists():
            return []

        executed: list[str] = []
        context = ModuleMigrationContext(
            module_id=module_id,
            from_version=from_version,
            to_version=to_version,
            module_dir=module_dir,
            config_service=self.config,
        )

        for migration_path in sorted(migrations_dir.glob("*.py")):
            if migration_path.name.startswith("_"):
                continue
            self._run_migration_file(migration_path, context)
            executed.append(migration_path.name)

        return executed

    @staticmethod
    def _run_migration_file(path: Path, context: ModuleMigrationContext):
        spec = importlib.util.spec_from_file_location(f"r4bot_migration_{context.module_id}_{path.stem}", path)
        if spec is None or spec.loader is None:
            raise ModuleMigrationError(f"Cannot load migration file: {path}")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise ModuleMigrationError(f"Migration import failed for {path.name}: {exc}") from exc

        migrate = getattr(module, "migrate", None)
        if migrate is None:
            raise ModuleMigrationError(f"Migration file does not define migrate(context): {path.name}")

        try:
            migrate(context)
        except Exception as exc:
            raise ModuleMigrationError(f"Migration failed for {path.name}: {exc}") from exc
