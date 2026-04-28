from __future__ import annotations

import inspect


_HOOK_PROVIDERS_ATTR = "_r4_hook_providers"
_HOOK_LISTENERS_ATTR = "_r4_hook_listeners"


def _get_provider_store(bot, create: bool = False) -> dict[str, dict[str, object]]:
    store = getattr(bot, _HOOK_PROVIDERS_ATTR, None)
    if store is None and create:
        store = {}
        setattr(bot, _HOOK_PROVIDERS_ATTR, store)
    return store or {}


def _get_listener_store(bot, create: bool = False) -> dict[str, list]:
    store = getattr(bot, _HOOK_LISTENERS_ATTR, None)
    if store is None and create:
        store = {}
        setattr(bot, _HOOK_LISTENERS_ATTR, store)
    return store or {}


def register_hook_provider(bot, hook_name: str, module_id: str, provider):
    providers = _get_provider_store(bot, create=True).setdefault(hook_name, {})
    providers[module_id] = provider
    _notify_hook_listeners(bot, hook_name, "register", module_id, provider)


def unregister_hook_provider(bot, hook_name: str, module_id: str):
    hook_store = getattr(bot, _HOOK_PROVIDERS_ATTR, None)
    if hook_store is None:
        return

    providers = hook_store.get(hook_name)
    if not providers:
        return

    provider = providers.pop(module_id, None)
    if provider is None:
        return

    _notify_hook_listeners(bot, hook_name, "unregister", module_id, provider)

    if not providers:
        hook_store.pop(hook_name, None)


def list_hook_providers(bot, hook_name: str) -> dict[str, object]:
    return dict(_get_provider_store(bot).get(hook_name, {}) or {})


async def collect_hook_results(bot, hook_name: str, **payload) -> list[tuple[str, object]]:
    collected_results: list[tuple[str, object]] = []
    providers = _get_provider_store(bot).get(hook_name, {}) or {}

    for module_id, provider in providers.items():
        try:
            result = provider(**payload)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            continue

        if result is None:
            continue

        collected_results.append((module_id, result))

    return collected_results


def subscribe_hook_events(bot, hook_name: str, listener):
    listeners = _get_listener_store(bot, create=True).setdefault(hook_name, [])
    listeners.append(listener)


def unsubscribe_hook_events(bot, hook_name: str, listener):
    listener_store = getattr(bot, _HOOK_LISTENERS_ATTR, None)
    if listener_store is None:
        return

    listeners = listener_store.get(hook_name)
    if not listeners:
        return

    try:
        listeners.remove(listener)
    except ValueError:
        return

    if not listeners:
        listener_store.pop(hook_name, None)


def _notify_hook_listeners(bot, hook_name: str, event: str, module_id: str, provider):
    listeners = _get_listener_store(bot).get(hook_name, []) or []
    for listener in list(listeners):
        try:
            listener(event=event, module_id=module_id, provider=provider)
        except Exception:
            continue
