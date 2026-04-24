from __future__ import annotations

import json
from pathlib import Path


class ModuleStateStore:
    def __init__(self, state_file: Path):
        self.state_file = state_file

    def load(self) -> dict:
        if not self.state_file.exists():
            return {"installed_modules": {}}

        with self.state_file.open("r", encoding="utf8") as file:
            return json.load(file)

    def save(self, payload: dict):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def list_installed(self) -> dict[str, dict]:
        return dict(self.load().get("installed_modules", {}))

    def get_enabled_module_ids(self) -> list[str]:
        installed = self.list_installed()
        return [module_id for module_id, module_data in installed.items() if module_data.get("enabled")]

    def set_module(self, module_id: str, payload: dict):
        state = self.load()
        state.setdefault("installed_modules", {})[module_id] = payload
        self.save(state)

    def remove_module(self, module_id: str):
        state = self.load()
        state.setdefault("installed_modules", {}).pop(module_id, None)
        self.save(state)

    def set_enabled(self, module_id: str, enabled: bool):
        state = self.load()
        module_entry = state.setdefault("installed_modules", {}).get(module_id)
        if module_entry is None:
            raise KeyError(module_id)
        module_entry["enabled"] = enabled
        self.save(state)
