import os
import platform
import shutil
import subprocess
import sys
import zipfile

import aiohttp
from discord.ext import commands, tasks

from options import version, servers_data


async def git_pull():
    try:
        result = subprocess.run(["git", "pull"], cwd=os.getcwd(), capture_output=True, text=True)
        print(result.stdout)
        return result.returncode == 0
    except Exception as e:
        print(f"Ошибка при выполнении git pull: {e}")
        return False


def restart_bot():
    try:
        if platform.system() == "Windows":
            os.system(f'python "{os.path.join(os.getcwd(), "main.py")}"')
        else:
            os.system(f'python3 "{os.path.join(os.getcwd(), "main.py")}"')
        print("Запущен новый процесс бота.")
    except Exception as e:
        print(f"Ошибка при запуске нового процесса: {e}")
    sys.exit(0)


class VersionChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_version = version
        self.repo = "Rarmash/R4Bot"
        self.servers_data = servers_data
        self.session = None
        self.check_version.start()

    @tasks.loop(minutes=10)
    async def check_version(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{self.repo}/releases/latest") as response:
                if response.status == 200:
                    data = await response.json()
                    remote_version = data["tag_name"]
                    if self.is_newer_version(remote_version.strip('v')):
                        print(f"Доступна новая версия бота ({self.current_version} -> {remote_version}). Обновляем...")
                        if await git_pull():
                            print("Обновление завершено. Перезапуск бота...")
                            restart_bot()
                        else:
                            await self.download_and_update(session, data["zipball_url"], remote_version)

    def is_newer_version(self, remote_version):
        current_version_parts = list(map(int, self.current_version.split('.')))
        remote_version_parts = list(map(int, remote_version.split('.')))
        return remote_version_parts > current_version_parts

    async def download_and_update(self, session, url, new_version):
        async with session.get(url) as response:
            if response.status == 200:
                zip_path = f"update_{new_version}.zip"
                with open(zip_path, "wb") as file:
                    file.write(await response.read())
                base_dir = os.path.join(os.getcwd(), "update")
                await self.extract_and_replace(zip_path, new_version, base_dir)
                print(f"Загружен и распакован {zip_path}.")

    async def extract_and_replace(self, zip_path, new_version, base_dir):
        try:
            extract_folder = f"update_{new_version}"

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                folder_name = next(name for name in zip_ref.namelist() if name.endswith('/')).strip('/')

            for root, dirs, files in os.walk(os.path.join(extract_folder, folder_name)):
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, os.path.join(extract_folder, folder_name))
                    dest_path = os.path.join(base_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.move(src_path, dest_path)

            shutil.rmtree(extract_folder)
            os.remove(zip_path)

            subprocess.Popen([sys.executable, "modules/update.py"])

        except Exception as e:
            print(f"Ошибка при распаковке и обновлении: {e}")

    @check_version.before_loop
    async def before_check_version(self):
        await self.bot.wait_until_ready()
