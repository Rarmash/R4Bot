import os
import shutil
import sys
import time
from pathlib import Path


def update_and_restart():
    update_dir = Path("update")

    try:
        current_dir = Path.cwd()

        for root, _, files in os.walk(update_dir):
            for file_name in files:
                src_path = Path(root) / file_name
                rel_path = src_path.relative_to(update_dir)
                dest_path = current_dir / rel_path

                print(f"Перемещение: {src_path} -> {dest_path}")

                if dest_path.exists():
                    os.remove(dest_path)

                shutil.move(str(src_path), str(dest_path))

        shutil.rmtree(update_dir)

        print("Обновление завершено. Перезапуск бота...")
        os.execv(sys.executable, [sys.executable, str(current_dir / "main.py")])
    except Exception as exc:
        print(f"Ошибка при обновлении: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    time.sleep(2)
    update_and_restart()
