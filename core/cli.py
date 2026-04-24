from __future__ import annotations

import argparse

from core.module_installer import ModuleInstaller, ModuleInstallerError
from services.config_service import ConfigService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="R4Bot module manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install a module from GitHub or local path")
    install_parser.add_argument("module_ref", help="github:owner/repo[@ref] or path:relative/module_dir")
    install_parser.add_argument("--ref", help="Override Git ref")
    install_parser.add_argument("--enable", action="store_true", help="Enable module immediately after install")

    remove_parser = subparsers.add_parser("remove", help="Remove an installed module")
    remove_parser.add_argument("module_id")

    update_parser = subparsers.add_parser("update", help="Update an installed module from its original source")
    update_parser.add_argument("module_id")
    update_parser.add_argument("--ref", help="Override Git ref for GitHub-based modules")

    enable_parser = subparsers.add_parser("enable", help="Enable an installed module")
    enable_parser.add_argument("module_id")

    disable_parser = subparsers.add_parser("disable", help="Disable an installed module")
    disable_parser.add_argument("module_id")

    subparsers.add_parser("list-installed", help="List installed modules")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = ConfigService()
    installer = ModuleInstaller(config)

    try:
        if args.command == "install":
            manifest = installer.install(args.module_ref, ref=args.ref, enable=args.enable)
            state = "enabled" if args.enable else "installed"
            print(f"Module '{manifest.name}' ({manifest.module_id} {manifest.version}) {state}.")
            return 0

        if args.command == "remove":
            installer.remove(args.module_id)
            print(f"Module '{args.module_id}' removed.")
            return 0

        if args.command == "update":
            manifest = installer.update(args.module_id, ref=args.ref)
            print(f"Module '{manifest.name}' ({manifest.module_id} {manifest.version}) updated.")
            return 0

        if args.command == "enable":
            installer.enable(args.module_id)
            print(f"Module '{args.module_id}' enabled.")
            return 0

        if args.command == "disable":
            installer.disable(args.module_id)
            print(f"Module '{args.module_id}' disabled.")
            return 0

        if args.command == "list-installed":
            installed = installer.list_installed_modules()
            if not installed:
                print("No modules installed.")
                return 0

            for module_id, module_data in installed.items():
                status = "enabled" if module_data.get("enabled") else "disabled"
                print(f"{module_id}: {module_data.get('version', '?')} [{status}]")
            return 0
    except (ModuleInstallerError, KeyError) as exc:
        print(f"Error: {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
