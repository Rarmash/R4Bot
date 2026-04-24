from __future__ import annotations

import json
from pathlib import Path


class SecretService:
    def __init__(self, secrets_dir: Path | None = None):
        self.secrets_dir = secrets_dir or Path("config") / "secrets"

    def _get_secret_path(self, module_id: str) -> Path:
        return self.secrets_dir / f"{module_id}.json"

    def load(self, module_id: str) -> dict:
        secret_path = self._get_secret_path(module_id)
        if not secret_path.exists():
            return {}

        with secret_path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        return payload if isinstance(payload, dict) else {}

    def save(self, module_id: str, payload: dict):
        secret_path = self._get_secret_path(module_id)
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        with secret_path.open("w", encoding="utf8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def get(self, module_id: str, key: str, default=None):
        payload = self.load(module_id)
        return payload.get(key, default)
