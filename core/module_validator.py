from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zipfile import ZipFile

from core.module_manifest import ModuleManifest
from core.runtime_context import RuntimeServices


class ModuleValidatorError(Exception):
    """Raised when a module scaffold is invalid."""


class ModuleValidator:
    def validate(self, module_ref: str, ref: str | None = None) -> tuple[ModuleManifest, list[str]]:
        if module_ref.startswith("path:"):
            source_path = Path(module_ref.removeprefix("path:")).expanduser().resolve()
            return self._validate_directory(source_path)

        if module_ref.startswith("github:"):
            repo_spec = module_ref.removeprefix("github:")
            repo = repo_spec
            resolved_ref = ref or "main"
            if "@" in repo_spec:
                repo, resolved_ref = repo_spec.split("@", 1)
            return self._validate_github(repo, resolved_ref)

        raise ModuleValidatorError("Use path:module_dir or github:owner/repo[@ref] for validation.")

    def _validate_directory(self, source_dir: Path) -> tuple[ModuleManifest, list[str]]:
        if not source_dir.exists():
            raise ModuleValidatorError(f"Module source path does not exist: {source_dir}")
        if not source_dir.is_dir():
            raise ModuleValidatorError(f"Module source path is not a directory: {source_dir}")

        manifest_path = source_dir / "module.json"
        if not manifest_path.exists():
            raise ModuleValidatorError(f"module.json was not found in: {source_dir}")

        manifest = ModuleManifest.from_file(manifest_path)
        warnings = self._collect_warnings(source_dir, manifest)
        return manifest, warnings

    def _validate_github(self, repo: str, ref: str) -> tuple[ModuleManifest, list[str]]:
        with tempfile.TemporaryDirectory(prefix="r4bot-module-validate-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            archive_path = temp_dir / "module.zip"
            extracted_dir = temp_dir / "extracted"
            extracted_dir.mkdir(parents=True, exist_ok=True)

            self._download_archive(repo, ref, archive_path)

            with ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(extracted_dir)

            manifest_path = self._find_manifest(extracted_dir)
            manifest = ModuleManifest.from_file(manifest_path)
            warnings = self._collect_warnings(manifest_path.parent, manifest)
            return manifest, warnings

    @staticmethod
    def _collect_warnings(source_dir: Path, manifest: ModuleManifest) -> list[str]:
        warnings: list[str] = []
        supported_services = set(RuntimeServices.__annotations__.keys())

        entrypoint_path = source_dir / f"{manifest.entrypoint}.py"
        if not entrypoint_path.exists():
            warnings.append(f"Entrypoint file was not found: {entrypoint_path.name}")

        requirements_path = source_dir / "requirements.txt"
        if not requirements_path.exists():
            warnings.append("requirements.txt is missing")

        readme_path = source_dir / "README.md"
        if not readme_path.exists():
            warnings.append("README.md is missing")

        if not manifest.required_services:
            warnings.append("required_services is empty in module.json")

        if not manifest.description:
            warnings.append("description is empty in module.json")

        unknown_services = [service for service in manifest.required_services if service not in supported_services]
        if unknown_services:
            warnings.append(f"Unknown required_services: {', '.join(unknown_services)}")

        if manifest.module_id in manifest.required_dependencies:
            warnings.append("required_dependencies contains the module itself")

        return warnings

    @staticmethod
    def _download_archive(repo: str, ref: str, destination: Path):
        candidate_urls = [
            f"https://github.com/{repo}/archive/refs/tags/{ref}.zip",
            f"https://github.com/{repo}/archive/refs/heads/{ref}.zip",
            f"https://github.com/{repo}/archive/{ref}.zip",
        ]

        last_error = None
        for url in candidate_urls:
            try:
                with urlopen(url) as response:
                    destination.write_bytes(response.read())
                    return
            except (HTTPError, URLError) as exc:
                last_error = exc

        raise ModuleValidatorError(f"Failed to download module archive for {repo}@{ref}: {last_error}")

    @staticmethod
    def _find_manifest(extracted_dir: Path) -> Path:
        manifests = list(extracted_dir.rglob("module.json"))
        if not manifests:
            raise ModuleValidatorError("Downloaded module does not contain module.json")
        manifests.sort(key=lambda path: len(path.parts))
        return manifests[0]
