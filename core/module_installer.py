from __future__ import annotations

import os
import stat
import shutil
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zipfile import ZipFile

from core.module_manifest import ModuleManifest
from core.module_state import ModuleStateStore


class ModuleInstallerError(Exception):
    """Raised when a module cannot be installed or managed."""


class ModuleInstaller:
    def __init__(self, config_service):
        self.config = config_service
        self.state_store = ModuleStateStore(self.config.paths.module_state_file)
        self.install_dir = self.config.paths.installed_modules_dir
        self.install_dir.mkdir(parents=True, exist_ok=True)

    def list_installed_modules(self) -> dict[str, dict]:
        return self.state_store.list_installed()

    def install(self, module_ref: str, ref: str | None = None, enable: bool = False) -> ModuleManifest:
        if module_ref.startswith("path:"):
            source_path = Path(module_ref.removeprefix("path:")).expanduser()
            if not source_path.is_absolute():
                source_path = self.config.paths.root / source_path
            return self._install_from_directory(source_path.resolve(), enable, source=f"path:{source_path}")

        repo = None
        requested_module_id = None
        resolved_ref = ref or "main"

        if module_ref.startswith("github:"):
            repo_spec = module_ref.removeprefix("github:")
            if "@" in repo_spec:
                repo, resolved_ref = repo_spec.split("@", 1)
            else:
                repo = repo_spec
        else:
            raise ModuleInstallerError("Use github:owner/repo[@ref] or path:module_dir for module installation.")

        return self._install_from_github(repo, resolved_ref, enable, requested_module_id)

    def enable(self, module_id: str):
        if module_id not in self.state_store.list_installed():
            raise ModuleInstallerError(f"Module '{module_id}' is not installed.")
        self.state_store.set_enabled(module_id, True)

    def disable(self, module_id: str):
        if module_id not in self.state_store.list_installed():
            raise ModuleInstallerError(f"Module '{module_id}' is not installed.")
        self.state_store.set_enabled(module_id, False)

    def remove(self, module_id: str):
        if module_id not in self.state_store.list_installed():
            raise ModuleInstallerError(f"Module '{module_id}' is not installed.")
        target_dir = self.install_dir / module_id
        if target_dir.exists():
            shutil.rmtree(target_dir, onexc=self._handle_remove_readonly)
        self.state_store.remove_module(module_id)

    def update(self, module_id: str, ref: str | None = None) -> ModuleManifest:
        installed = self.state_store.list_installed()
        module_data = installed.get(module_id)
        if module_data is None:
            raise ModuleInstallerError(f"Module '{module_id}' is not installed.")

        enabled = bool(module_data.get("enabled"))
        source = module_data.get("source")

        if source == "github":
            repo = module_data.get("repo")
            if not repo:
                raise ModuleInstallerError(f"Module '{module_id}' does not have a stored GitHub repository.")
            resolved_ref = ref or module_data.get("ref") or "main"
            return self._install_from_github(repo, resolved_ref, enabled, requested_module_id=module_id)

        if source == "path":
            source_path = module_data.get("path")
            if not source_path:
                raise ModuleInstallerError(f"Module '{module_id}' does not have a stored source path.")
            return self._install_from_directory(Path(source_path), enabled, source=f"path:{source_path}")

        raise ModuleInstallerError(
            f"Module '{module_id}' has unsupported update source '{source}'. Reinstall it manually."
        )

    def update_all(self, ref: str | None = None) -> tuple[list[tuple[str, ModuleManifest]], dict[str, str]]:
        updated: list[tuple[str, ModuleManifest]] = []
        failed: dict[str, str] = {}

        for module_id in self.state_store.list_installed():
            try:
                manifest = self.update(module_id, ref=ref)
            except (ModuleInstallerError, KeyError) as exc:
                failed[module_id] = str(exc)
                continue

            updated.append((module_id, manifest))

        return updated, failed

    def _install_from_github(
        self,
        repo: str,
        ref: str,
        enable: bool,
        requested_module_id: str | None,
    ) -> ModuleManifest:
        self.config.paths.temp_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = self.config.paths.temp_dir / f"r4bot-module-{uuid.uuid4().hex}"
        archive_path = temp_dir / "module.zip"
        extracted_dir = temp_dir / "extracted"

        try:
            extracted_dir.mkdir(parents=True, exist_ok=True)

            self._download_archive(repo, ref, archive_path)

            with ZipFile(archive_path, "r") as zip_file:
                zip_file.extractall(extracted_dir)

            manifest_path = self._find_manifest(extracted_dir)
            return self._install_from_manifest(
                manifest_path=manifest_path,
                enable=enable,
                metadata={
                    "source": "github",
                    "repo": repo,
                    "ref": ref,
                },
                requested_module_id=requested_module_id,
            )
        finally:
            self._cleanup_directory(temp_dir)

    def _install_from_directory(self, source_dir: Path, enable: bool, source: str) -> ModuleManifest:
        if not source_dir.exists():
            raise ModuleInstallerError(f"Module source path does not exist: {source_dir}")
        if not source_dir.is_dir():
            raise ModuleInstallerError(f"Module source path is not a directory: {source_dir}")

        manifest_path = source_dir / "module.json"
        if not manifest_path.exists():
            raise ModuleInstallerError(f"Module source path does not contain module.json: {source_dir}")

        return self._install_from_manifest(
            manifest_path=manifest_path,
            enable=enable,
            metadata={
                "source": "path",
                "path": str(source_dir),
            },
        )

    def _install_from_manifest(
        self,
        manifest_path: Path,
        enable: bool,
        metadata: dict,
        requested_module_id: str | None = None,
    ) -> ModuleManifest:
        manifest = ModuleManifest.from_file(manifest_path)

        if requested_module_id and requested_module_id != manifest.module_id:
            raise ModuleInstallerError(
                f"Installed module id mismatch: expected '{requested_module_id}', got '{manifest.module_id}'."
            )

        source_root = manifest_path.parent
        target_dir = self.install_dir / manifest.module_id
        if target_dir.exists():
            shutil.rmtree(target_dir, onexc=self._handle_remove_readonly)

        shutil.copytree(source_root, target_dir, ignore=shutil.ignore_patterns(".git", ".idea", "__pycache__"))
        self._ensure_module_config(target_dir, manifest.module_id)
        self._ensure_module_secrets(target_dir, manifest.module_id)
        self.state_store.set_module(
            manifest.module_id,
            {
                "enabled": enable,
                "version": manifest.version,
                "name": manifest.name,
                "description": manifest.description,
                **metadata,
            },
        )
        return manifest

    def _ensure_module_config(self, source_root: Path, module_id: str):
        config_dir = self.config.paths.module_configs_dir
        config_dir.mkdir(parents=True, exist_ok=True)

        target_config_path = config_dir / f"{module_id}.json"
        if target_config_path.exists():
            return

        candidate_names = [
            f"{module_id}.example.json",
            "config.example.json",
            "module.example.json",
        ]

        for candidate_name in candidate_names:
            example_path = source_root / candidate_name
            if not example_path.exists():
                continue

            shutil.copyfile(example_path, target_config_path)
            return

    def _ensure_module_secrets(self, source_root: Path, module_id: str):
        secrets_dir = self.config.paths.secrets_dir
        secrets_dir.mkdir(parents=True, exist_ok=True)

        target_secret_path = secrets_dir / f"{module_id}.json"
        if target_secret_path.exists():
            return

        candidate_names = [
            f"{module_id}.secrets.example.json",
            "secrets.example.json",
        ]

        for candidate_name in candidate_names:
            example_path = source_root / candidate_name
            if not example_path.exists():
                continue

            shutil.copyfile(example_path, target_secret_path)
            return

    def _download_archive(self, repo: str, ref: str, destination: Path):
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

        raise ModuleInstallerError(f"Failed to download module archive for {repo}@{ref}: {last_error}")

    def _find_manifest(self, extracted_dir: Path) -> Path:
        manifests = list(extracted_dir.rglob("module.json"))
        if not manifests:
            raise ModuleInstallerError("Downloaded module does not contain module.json")
        manifests.sort(key=lambda path: len(path.parts))
        return manifests[0]

    def _cleanup_directory(self, path: Path):
        if path.exists():
            shutil.rmtree(path, onexc=self._handle_remove_readonly)

    @staticmethod
    def _handle_remove_readonly(func, path, excinfo):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            raise excinfo[1]
