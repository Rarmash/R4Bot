import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import aiohttp
from discord.ext import commands, tasks

from services.config_service import ConfigService


async def git_pull():
    try:
        result = subprocess.run(["git", "pull"], cwd=os.getcwd(), capture_output=True, text=True)
        print(result.stdout)
        return result.returncode == 0
    except Exception as exc:
        print(f"Ошибка при выполнении git pull: {exc}")
        return False


def restart_bot():
    try:
        main_file = os.path.join(os.getcwd(), "main.py")
        if platform.system() == "Windows":
            os.system(f'python "{main_file}"')
        else:
            os.execv(sys.executable, [sys.executable, main_file])
        print("Запущен новый процесс бота.")
    except Exception as exc:
        print(f"Ошибка при запуске нового процесса: {exc}")
    sys.exit(0)


class VersionChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, "r4_services", None).config if hasattr(bot, "r4_services") else ConfigService()
        self.current_version = self.config.version
        self.repo = "Rarmash/R4Bot"
        self.session = None
        self.check_version.start()

    def is_newer_version(self, remote_version):
        current_version_parts = list(map(int, self.current_version.split(".")))
        remote_version_parts = list(map(int, remote_version.split(".")))
        return remote_version_parts > current_version_parts

    async def download_and_update(self, session, url, new_version):
        async with session.get(url) as response:
            if response.status != 200:
                return

            zip_path = Path(f"update_{new_version}.zip")
            zip_path.write_bytes(await response.read())

            base_dir = Path(os.getcwd()) / "update"
            await self.extract_and_replace(zip_path, new_version, base_dir)
            print(f"Загружен и распакован {zip_path}.")

    async def extract_and_replace(self, zip_path: Path, new_version, base_dir: Path):
        try:
            extract_folder = Path(f"update_{new_version}")

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_folder)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                folder_name = next(name for name in zip_ref.namelist() if name.endswith("/")).strip("/")

            source_root = extract_folder / folder_name
            for root, _, files in os.walk(source_root):
                for file_name in files:
                    src_path = Path(root) / file_name
                    rel_path = src_path.relative_to(source_root)
                    dest_path = base_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src_path), str(dest_path))

            shutil.rmtree(extract_folder)
            zip_path.unlink(missing_ok=True)

            subprocess.Popen([sys.executable, "modules/update.py"])
        except Exception as exc:
            print(f"Ошибка при распаковке и обновлении: {exc}")

    @tasks.loop(minutes=10)
    async def check_version(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{self.repo}/releases/latest") as response:
                if response.status != 200:
                    return

                data = await response.json()
                remote_version = data["tag_name"]
                if not self.is_newer_version(remote_version.strip("v")):
                    return

                print(f"Доступна новая версия бота ({self.current_version} -> {remote_version}). Обновляем...")
                if await git_pull():
                    print("Обновление завершено. Перезапуск бота...")
                    restart_bot()
                    return

                await self.download_and_update(session, data["zipball_url"], remote_version)

    @check_version.before_loop
    async def before_check_version(self):
        await self.bot.wait_until_ready()
