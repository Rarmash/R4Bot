from __future__ import annotations

import argparse

from core.module_generator import ModuleGenerator, ModuleGeneratorError
from core.module_installer import ModuleInstaller, ModuleInstallerError
from core.module_validator import ModuleValidator, ModuleValidatorError
from services.config_service import ConfigService


def print_runtime_change_warning():
    print(
        "Warning: module install/update changes files and Python dependencies. "
        "It is safer to run these commands while the bot is stopped, then restart it."
    )


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
    update_parser.add_argument("module_id", nargs="?", help="Installed module id")
    update_parser.add_argument("--all", action="store_true", help="Update all installed modules")
    update_parser.add_argument("--ref", help="Override Git ref for GitHub-based modules")

    enable_parser = subparsers.add_parser("enable", help="Enable an installed module")
    enable_parser.add_argument("module_id")

    disable_parser = subparsers.add_parser("disable", help="Disable an installed module")
    disable_parser.add_argument("module_id")

    create_module_parser = subparsers.add_parser("create-module", help="Create a new module scaffold")
    create_module_parser.add_argument("module_id", help="New module id")
    create_module_parser.add_argument("--output", help="Target directory for the new module")
    create_module_parser.add_argument("--name", help="Human-readable module name")
    create_module_parser.add_argument("--author", default="", help="Module author")
    create_module_parser.add_argument("--description", default="", help="Module description")
    create_module_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty directory",
    )
    create_module_parser.add_argument(
        "--no-config-template",
        action="store_true",
        help="Do not generate <module>.example.json",
    )
    create_module_parser.add_argument(
        "--no-secrets-template",
        action="store_true",
        help="Do not generate <module>.secrets.example.json",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate a module scaffold")
    validate_parser.add_argument("module_ref", help="path:module_dir or github:owner/repo[@ref]")
    validate_parser.add_argument("--ref", help="Override Git ref for GitHub-based modules")

    subparsers.add_parser("list-installed", help="List installed modules")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = ConfigService()
    installer = ModuleInstaller(config)
    generator = ModuleGenerator()
    validator = ModuleValidator()

    try:
        if args.command == "install":
            print_runtime_change_warning()
            manifest = installer.install(args.module_ref, ref=args.ref, enable=args.enable)
            state = "enabled" if args.enable else "installed"
            print(f"Module '{manifest.name}' ({manifest.module_id} {manifest.version}) {state}.")
            return 0

        if args.command == "remove":
            installer.remove(args.module_id)
            print(f"Module '{args.module_id}' removed.")
            return 0

        if args.command == "update":
            print_runtime_change_warning()
            if args.all:
                updated, failed = installer.update_all(ref=args.ref)

                if updated:
                    print("Updated modules:")
                    for module_id, manifest in updated:
                        print(f"- {module_id}: {manifest.version}")

                if failed:
                    print("Failed modules:")
                    for module_id, error in failed.items():
                        print(f"- {module_id}: {error}")

                if not updated and not failed:
                    print("No modules installed.")
                    return 0

                return 0 if not failed else 1

            if not args.module_id:
                raise ModuleInstallerError("Specify a module id or use --all.")

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

        if args.command == "create-module":
            output_dir = config.paths.root / args.module_id if not args.output else config.paths.root / args.output
            if args.output:
                output_dir = output_dir.resolve()
            generated_path = generator.generate(
                args.module_id,
                output_dir,
                name=args.name,
                author=args.author,
                description=args.description,
                overwrite=args.overwrite,
                include_config_template=not args.no_config_template,
                include_secrets_template=not args.no_secrets_template,
            )
            print(f"Module scaffold created: {generated_path}")
            return 0

        if args.command == "validate":
            manifest, warnings = validator.validate(args.module_ref, ref=args.ref)
            print(f"Module '{manifest.name}' ({manifest.module_id} {manifest.version}) is valid.")
            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print(f"- {warning}")
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
    except (ModuleInstallerError, ModuleGeneratorError, ModuleValidatorError, KeyError) as exc:
        print(f"Error: {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
