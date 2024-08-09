import os
import shutil
import sys
import time


def update_and_restart():
    update_dir = f"update"
    try:
        curr_path = os.getcwd()

        for root, dirs, files in os.walk(update_dir):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, update_dir)
                dest_path = os.path.join(curr_path, rel_path)

                print(f"Перемещение: {src_path} -> {dest_path}")

                if os.path.exists(dest_path):
                    os.remove(dest_path)

                shutil.move(src_path, dest_path)

        shutil.rmtree(update_dir)

        print("Обновление завершено. Перезапуск бота...")
        os.execv(sys.executable, [sys.executable] + [os.path.join(os.getcwd(), 'main.py')])

    except Exception as e:
        print(f"Ошибка при обновлении: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    time.sleep(2)
    update_and_restart()
