#!/usr/bin/env python3
import os
import sys
import time
import yaml
import subprocess

# ANSI color codes for terminal styling
COLOR = {
    "reset": "\033[0m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "red": "\033[31m"
}

INSTALL_DIR = os.getcwd()
MOUNT_POINT = "/tmp/lindbergh_mount"
EXCLUDES = ["drv", "drv.old", "lost+found", "System Volume Information"]

# Run shell command with optional output suppression
def run(cmd, silent=True):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if not silent and result.returncode != 0:
            print(f"{COLOR['red']}Error: {cmd}{COLOR['reset']}")
            print(result.stderr.strip())
        return result
    except Exception as e:
        print(f"{COLOR['red']}Exception running command: {e}{COLOR['reset']}")
        return subprocess.CompletedProcess(cmd, 1)

# Unmounts MOUNT_POINT if currently mounted
def safe_unmount():
    if os.path.ismount(MOUNT_POINT):
        run(f"umount \"{MOUNT_POINT}\"", silent=False)

# Mounts and copies from a game image, then unmounts
def process_step(step, dest):
    image_path = os.path.join(INSTALL_DIR, step["file"])
    fs_type = step.get("filesystem", "ext2")
    subfolder = step.get("destination_subfolder")

    if not os.path.isfile(image_path):
        print(f"{COLOR['red']}Missing image file: {image_path}{COLOR['reset']}")
        return False

    safe_unmount()
    os.makedirs(MOUNT_POINT, exist_ok=True)
    if run(f"mount -t {fs_type} \"{image_path}\" \"{MOUNT_POINT}\"").returncode != 0:
        print(f"{COLOR['red']}Failed to mount {image_path}{COLOR['reset']}")
        return False

    time.sleep(0.5)
    os.makedirs(dest, exist_ok=True)

    tasks = []
    for folder in step.get("copy_dirs", []):
        src = os.path.join(MOUNT_POINT, folder)
        dst = dest
        if subfolder:
            dst = os.path.join(dest, subfolder)
            os.makedirs(dst, exist_ok=True)
        tasks.append((src, dst))

    if not step.get("copy_dirs") and subfolder:
        src = MOUNT_POINT
        dst = os.path.join(dest, subfolder)
        os.makedirs(dst, exist_ok=True)
        tasks.append((src, dst))

    for entry in step.get("extra_copy_dirs", []):
        src = os.path.join(MOUNT_POINT, entry["source"])
        dst = os.path.join(dest, entry["destination"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tasks.append((src, dst))

    def count_all_files():
        total = 0
        for src, _ in tasks:
            if not os.path.exists(src):
                continue
            for root, _, files in os.walk(src):
                if any(part in EXCLUDES for part in root.split(os.sep)):
                    continue
                total += len(files)
        return total

    total_files = count_all_files()
    if total_files == 0:
        print(f"{COLOR['yellow']}Nothing to copy from {image_path}{COLOR['reset']}")
        safe_unmount()
        return True

    print(f"{COLOR['cyan']}Processing {os.path.basename(image_path)} ({total_files} files){COLOR['reset']}")
    copied = 0
    update_step = max(1, total_files // 100)

    for src, dst in tasks:
        if not os.path.exists(src):
            print(f"{COLOR['yellow']}Warning: Source path does not exist: {src}{COLOR['reset']}")
            continue

        cmd = ["rsync", "-a", "--checksum", "--inplace", "--no-inc-recursive", "--out-format=%n"]
        cmd += [f"--exclude={e}" for e in EXCLUDES]
        cmd += [f"{src}/", f"{dst}/"]

        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as p:
                for _ in p.stdout:
                    copied += 1
                    if copied % update_step == 0 or copied == total_files:
                        pct = min(100, int((copied / total_files) * 100))
                        bar = "#" * (pct // 4) + "." * (25 - pct // 4)
                        print(f"\r[{bar}] {pct:3}%", end="", flush=True)
        except Exception as e:
            print(f"\n{COLOR['red']}Error during copy: {e}{COLOR['reset']}")

    print()
    safe_unmount()
    return True

# Create a .game file in destination folder
def create_launcher(game_key, config, dest_dir):
    launcher_path = config.get("launcher_path", "")
    target_dir = os.path.join(dest_dir, launcher_path) if launcher_path else dest_dir
    os.makedirs(target_dir, exist_ok=True)
    launcher_file = os.path.join(target_dir, f"{game_key}.game")
    if os.path.exists(launcher_file):
        print(f"{COLOR['yellow']}Launcher already exists: {launcher_file}{COLOR['reset']}")
    with open(launcher_file, "w") as f:
        f.write(f"# Launcher for {game_key}\n")
    print(f"{COLOR['green']}Launcher created: {launcher_file}{COLOR['reset']}")

# Loads and parses the games_config.yml file with validation.
def load_config():
    config_file = os.path.join(INSTALL_DIR, "games_config.yml")
    try:
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"{COLOR['red']}Configuration file not found: {config_file}{COLOR['reset']}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"{COLOR['red']}Error parsing YAML: {e}{COLOR['reset']}")
        sys.exit(1)

# Coordinates the full installation of a single game entry.
def install_game(game_key, config):
    dest_dir = os.path.join(INSTALL_DIR, game_key)
    if os.path.isdir(dest_dir) and os.listdir(dest_dir):
        confirm = input(f"{COLOR['yellow']}{dest_dir} exists. Overwrite? (y/n): {COLOR['reset']}").lower()
        if confirm != "y":
            print(f"{COLOR['yellow']}Skipped {game_key}{COLOR['reset']}")
            return
    success = True
    for step in config.get("steps", []):
        if not process_step(step, dest_dir):
            success = False
            print(f"{COLOR['red']}Error processing step for {game_key}{COLOR['reset']}")
            break
    if success:
        create_launcher(game_key, config, dest_dir)
        print(f"{COLOR['green']}Installed: {config.get('display_name', game_key)}{COLOR['reset']}")
    else:
        print(f"{COLOR['red']}Installation failed for {game_key}{COLOR['reset']}")

# Interactive menu
def main():
    if os.geteuid() != 0:
        print(f"{COLOR['red']}This script must be run as root.{COLOR['reset']}")
        return
    try:
        config = load_config()
        games = list(config.items())
        if not games:
            print(f"{COLOR['red']}No games defined in configuration.{COLOR['reset']}")
            return
        while True:
            print(f"\n{COLOR['cyan']}Lindbergh ROM Installer{COLOR['reset']}")
            for i, (key, val) in enumerate(games, 1):
                print(f"{i}) {val.get('display_name', key)}")
            print("all) Install all games\nq) Quit")
            choice = input("Select: ").strip().lower()
            if choice == "q":
                break
            elif choice == "all":
                start = time.time()
                for idx, (key, val) in enumerate(games, 1):
                    print(f"\n{COLOR['yellow']}Installing ({idx}/{len(games)}): {val.get('display_name', key)}{COLOR['reset']}")
                    install_game(key, val)
                print(f"{COLOR['green']}All installations completed in {time.time() - start:.1f} seconds.{COLOR['reset']}")
                input("Press Enter to return to menu...")
            elif choice.isdigit() and 1 <= int(choice) <= len(games):
                key, val = games[int(choice) - 1]
                install_game(key, val)
                input("Press Enter to return to menu...")
            else:
                print(f"{COLOR['red']}Invalid choice. Try again.{COLOR['reset']}")
    finally:
        safe_unmount()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_unmount()
        print(f"\n{COLOR['yellow']}Cancelled by user.{COLOR['reset']}")
