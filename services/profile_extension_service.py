from __future__ import annotations

import inspect


class ProfileExtensionService:
    def __init__(self):
        self._providers: dict[str, object] = {}

    def register_provider(self, module_id: str, provider):
        self._providers[module_id] = provider

    def unregister_provider(self, module_id: str):
        self._providers.pop(module_id, None)

    async def collect_fields(self, ctx, member, user_data: dict | None, server_data: dict | None) -> list[dict]:
        collected_fields: list[dict] = []

        for provider in self._providers.values():
            try:
                result = provider(ctx=ctx, member=member, user_data=user_data or {}, server_data=server_data or {})
                if inspect.isawaitable(result):
                    result = await result
            except Exception:
                continue

            if not result:
                continue

            if isinstance(result, dict):
                result = [result]

            for field in result:
                if not isinstance(field, dict):
                    continue
                if "name" not in field or "value" not in field:
                    continue
                collected_fields.append(field)

        return collected_fields
