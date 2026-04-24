from __future__ import annotations

from dataclasses import dataclass

from services.config_service import ConfigService
from services.firebase_service import FirebaseService
from services.module_config_service import ModuleConfigService
from services.module_resource_service import ModuleResourceService
from services.secret_service import SecretService


@dataclass(frozen=True)
class RuntimeServices:
    config: ConfigService
    firebase: FirebaseService
    module_config: ModuleConfigService
    resources: ModuleResourceService
    secrets: SecretService


@dataclass(frozen=True)
class RuntimeContext:
    services: RuntimeServices
