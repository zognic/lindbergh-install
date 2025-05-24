#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
import re

# This script automates installation of Lindbergh arcade ROMs by mounting image files, extracting their contents with rsync showing a global progress bar, and creating launcher files.

# ANSI color codes for styling
COLOR = {
    "reset": "\033[0m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "red": "\033[31m",
}

INSTALL_DIR = os.getcwd()                # Working directory where the script is run
MOUNT_PREFIX = "/tmp/lindbergh_mount"    # Prefix for temporary mount points
EXCLUDES = ["drv", "drv.old", "lost+found", "System Volume Information"]
BAR_LENGTH = 30                          # Length of the progress bar

# Execute a shell command and return the CompletedProcess
def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

# Unmount all mount points in the provided list
def safe_unmount_all(mount_points):
    for mnt in mount_points:
        if os.path.ismount(mnt):
            subprocess.run(f"umount -l '{mnt}'", shell=True)

# Mount each disk image listed in 'steps' to its own directory; return list of mount dirs
def mount_all_images(steps):
    mounts = []
    for idx, step in enumerate(steps, start=1):
        image_path = os.path.join(INSTALL_DIR, step["file"])
        mnt_dir = f"{MOUNT_PREFIX}_{idx}"
        os.makedirs(mnt_dir, exist_ok=True)
        fs_type = step.get("filesystem", "ext2")
        result = run(f"mount -t {fs_type} -o loop '{image_path}' '{mnt_dir}'")
        if result.returncode != 0:
            print(f"{COLOR['red']}Failed to mount: {image_path}{COLOR['reset']}")
            safe_unmount_all(mounts)
            sys.exit(1)
        mounts.append(mnt_dir)
    return mounts

# Run rsync for each (src, dst) showing a single overall progress bar
def run_rsync_overall(tasks):
    if not tasks:
        return True
    total = len(tasks)
    last_pct = -1
    proc = None
    for idx, (src, dst) in enumerate(tasks, start=1):
        os.makedirs(dst, exist_ok=True)
        cmd = [
            "rsync", "-a", "--info=progress2", "--omit-dir-times",
            "--no-compress", "--ignore-missing-args"
        ] + [f"--exclude={e}" for e in EXCLUDES] + [f"{src}/", f"{dst}/"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            m = re.search(r"(\d+)%", line)
            if m:
                part = int(m.group(1))
                overall = int(((idx - 1 + part / 100) / total) * 100)
                if overall != last_pct:
                    done = int(overall * BAR_LENGTH / 100)
                    bar = f"{COLOR['green']}{'#'*done}{COLOR['reset']}{'-'*(BAR_LENGTH-done)}"
                    print(f"\r[{bar}] {overall}%", end="", flush=True)
                    last_pct = overall
        proc.wait()
    if last_pct < 100:
        full = "#" * BAR_LENGTH
        bar = f"{COLOR['green']}{full}{COLOR['reset']}"
        print(f"\r[{bar}] 100%", end="", flush=True)
    print()
    return proc is not None and proc.returncode == 0

# Copy directories from mount_dir into dest, showing step and filename
def process_step(step, dest, step_idx, total_steps, mount_dir):
    base_dst = (os.path.join(dest, step.get('destination_subfolder', '')) if step.get('destination_subfolder') else dest)
    tasks = []
    copy_dirs = step.get('copy_dirs', [])
    # If copy_dirs has items, copy specified folders
    if copy_dirs:
        for folder in copy_dirs:
            tasks.append((os.path.join(mount_dir, folder), base_dst))
    # If copy_dirs exists (even if empty) or has destination_subfolder, copy all content
    elif 'copy_dirs' in step or step.get('destination_subfolder'):
        tasks.append((mount_dir, base_dst))
    for entry in step.get('extra_copy_dirs', []):
        src = os.path.join(mount_dir, entry['source'])
        dst = os.path.join(dest, entry.get('destination', ''))
        tasks.append((src, dst))
    print(f"{COLOR['yellow']}Step {step_idx}/{total_steps}: processing {os.path.basename(step['file'])}{COLOR['reset']}")
    if not run_rsync_overall(tasks):
        print(f"{COLOR['red']}Error copying files for {step['file']}{COLOR['reset']}")
        return False
    return True

# Create a .game launcher file under dest_dir so Batocera can detect the game
def create_launcher(game_key, config, dest_dir):
    launcher_path = config.get("launcher_path", "")
    target_dir = os.path.join(dest_dir, launcher_path) if launcher_path else dest_dir
    os.makedirs(target_dir, exist_ok=True)
    launcher_file = os.path.join(target_dir, f"{game_key}.game")
    if not os.path.exists(launcher_file):
        with open(launcher_file, "w") as f:
            f.write(f"# Launcher for {game_key}\n")
        print(f"{COLOR['green']}Launcher created: {launcher_file}{COLOR['reset']}")

# Load the games_config.yml file from INSTALL_DIR; exit on failure
def load_config():
    path = os.path.join(INSTALL_DIR, "games_config.yml")
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{COLOR['red']}Failed to load config: {e}{COLOR['reset']}")
        sys.exit(1)

# Install a single game: mount images, extract files, unmount, then create launcher
def install_game(key, config):
    dest = os.path.join(INSTALL_DIR, key)
    steps = config.get("steps", [])
    total = len(steps)
    if os.path.isdir(dest) and os.listdir(dest):
        if input(f"{COLOR['yellow']}{dest} exists. Overwrite? (y/n): {COLOR['reset']}").lower() != "y":
            print(f"{COLOR['yellow']}Skipped {key}{COLOR['reset']}")
            return
    # Temporarily exclude libs for Let's Go Jungle (allows Batocera's libs with shadow fix)
    orig_excludes = EXCLUDES.copy()
    if key == "letsgoju":
        EXCLUDES.extend(["libCg.so", "libCgGL.so"])
    mounts = mount_all_images(steps)
    try:
        for i, (step, mnt) in enumerate(zip(steps, mounts), start=1):
            if not process_step(step, dest, i, total, mnt):
                print(f"{COLOR['red']}Installation failed for {key}{COLOR['reset']}")
                return
    finally:
        safe_unmount_all(mounts)
        # Restore global EXCLUDES after extraction
        EXCLUDES[:] = orig_excludes
    create_launcher(key, config, dest)
    print(f"{COLOR['green']}Installed: {config.get('display_name', key)}{COLOR['reset']}")

# Display menu of games and handle user selection to install one or all
def main():
    if os.geteuid() != 0:
        print(f"{COLOR['red']}This script must be run as root.{COLOR['reset']}")
        return

    config = load_config()
    games = list(config.items())
    if not games:
        print(f"{COLOR['red']}No games defined in configuration.{COLOR['reset']}")
        return

    while True:
        print(f"\n{COLOR['cyan']}Lindbergh ROM Installer{COLOR['reset']}")
        for i, (key, val) in enumerate(games, 1):
            print(f"{i}) {val.get('display_name', key)}")
        print("all) Install all games")
        print("q) Quit")
        choice = input("Select: ").strip().lower()

        if choice == "q":
            break
        elif choice == "all":
            for idx, (key, val) in enumerate(games, 1):
                print(f"\n{COLOR['yellow']}Installing ({idx}/{len(games)}): {val.get('display_name', key)}{COLOR['reset']}")
                install_game(key, val)
            input("Press Enter to return to menu…")
        elif choice.isdigit() and 1 <= int(choice) <= len(games):
            key, val = games[int(choice) - 1]
            install_game(key, val)
            input("Press Enter to return to menu…")
        else:
            print(f"{COLOR['red']}Invalid choice. Try again.{COLOR['reset']}")

# Entry point
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{COLOR['yellow']}Aborted by user{COLOR['reset']}")
