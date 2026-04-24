from __future__ import annotations

import json
from dataclasses import dataclass
from os import environ
from pathlib import Path

from dotenv import load_dotenv

from options import version


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    temp_dir: Path
    env_file: Path
    firebase_config: Path
    servers_config: Path
    module_configs_dir: Path
    installed_modules_dir: Path
    module_state_file: Path

    @classmethod
    def discover(cls, root: Path | None = None) -> "ProjectPaths":
        project_root = root or Path(__file__).resolve().parent.parent
        return cls(
            root=project_root,
            temp_dir=project_root / ".tmp",
            env_file=project_root / ".env",
            firebase_config=project_root / "firebaseConfig.json",
            servers_config=project_root / "servers.json",
            module_configs_dir=project_root / "config" / "modules",
            installed_modules_dir=project_root / "installed_modules",
            module_state_file=project_root / "data" / "module_state.json",
        )


class ConfigService:
    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or ProjectPaths.discover()
        load_dotenv(self.paths.env_file)

        self.version = version
        self.token = environ.get("TOKEN")
        self.application_id = environ.get("APPLICATIONID")
        self.fortnite_api = environ.get("FORTNITEAPI")
        self.xbox_api = environ.get("XBOXAPI")
        self.steam_api = environ.get("STEAMAPI")
        self.debug_mode = environ.get("DEBUGMODE") == "ON"

        self.firebase_project_id = self._read_firebase_project_id()
        self.servers_data, self.builtin_modules = self._read_servers_config()

    def _read_firebase_project_id(self) -> str | None:
        if not self.paths.firebase_config.exists():
            return None

        with self.paths.firebase_config.open("r", encoding="utf8") as file:
            return json.load(file).get("project_id")

    def _read_servers_config(self) -> tuple[dict, list[str]]:
        if not self.paths.servers_config.exists():
            return {}, []

        with self.paths.servers_config.open("r", encoding="utf8") as file:
            payload = json.load(file)

        builtins = list(payload.get("cogs", []))
        servers = {key: value for key, value in payload.items() if key != "cogs"}
        return servers, builtins

    def get_builtin_modules(self) -> list[str]:
        return list(self.builtin_modules)

    def get_servers_data(self) -> dict:
        return dict(self.servers_data)
