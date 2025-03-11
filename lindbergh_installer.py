#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess

# ANSI color codes for styling
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"

INSTALL_DIR = os.getcwd()
MOUNT_POINT = "/tmp"


def run_command(command, capture_output=False):
    if capture_output:
        result = subprocess.run(command, shell=True, capture_output=True)
        try:
            result.stdout = result.stdout.decode("utf-8", errors="replace")
            result.stderr = result.stderr.decode("utf-8", errors="replace")
        except AttributeError:
            pass
        return result
    else:
        return subprocess.run(command, shell=True)


def ensure_unmounted():
    """Ensures the mount point is unmounted to avoid issues."""
    run_command(f"umount -l {MOUNT_POINT}")


def get_available_disk_space(directory):
    """Returns available disk space in bytes for a given directory."""
    statvfs = os.statvfs(directory)
    return statvfs.f_bavail * statvfs.f_frsize  # Available blocks * size per block


def check_required_space(required_space, directory):
    """Checks if there is enough space in the directory."""
    available_space = get_available_disk_space(directory)
    return available_space >= required_space


def get_total_size_of_files(files):
    """Returns the total size of a list of files."""
    total_size = 0
    for file in files:
        if os.path.exists(file):
            total_size += os.path.getsize(file)
    return total_size


def get_installable_games(config):
    """Filters and returns only games whose required .bin files exist."""
    installable_games = {}
    for game_key, game_config in config.items():
        all_files_present = all(os.path.isfile(os.path.join(INSTALL_DIR, step["file"]))
                                for step in game_config.get("steps", []))
        if all_files_present:
            installable_games[game_key] = game_config
    return installable_games


def process_game(game_key, game_config, force_overwrite=False):
    dest_dir = os.path.join(INSTALL_DIR, game_key)
    
    if os.path.isdir(dest_dir):
        if not force_overwrite:
            user_input = input(f"{YELLOW}The destination directory {dest_dir} already exists. Do you want to overwrite it? (yes/no): {RESET}").strip().lower()
            if user_input != "yes":
                print(f"{RED}Skipping game installation.{RESET}")
                return
        print(f"{YELLOW}Previous installation removed. Proceeding with installation.{RESET}")
        run_command(f"rm -rf \"{dest_dir}\"")
    
    required_space = get_total_size_of_files([os.path.join(INSTALL_DIR, step["file"]) for step in game_config.get("steps", [])])
    
    if not check_required_space(required_space, INSTALL_DIR):
        print(f"{RED}Error: Not enough disk space available to install {game_config.get('display_name', game_key)}!{RESET}")
        print(f"{RED}Please free up some space and try again.{RESET}")
        return
    
    os.makedirs(dest_dir, exist_ok=True)
    print(f"{CYAN}Installing {game_config.get('display_name', game_key)}...{RESET}")
    
    steps = game_config.get("steps", [])
    success = all(process_step(step, dest_dir) for step in steps)
    
    if success:
        create_game_file(dest_dir, game_key)
        print(f"{GREEN}Installation completed for {game_config.get('display_name', game_key)}{RESET}")
    else:
        print(f"{RED}Installation failed. Cleaning up...{RESET}")
        run_command(f"rm -rf \"{dest_dir}\"")


def main():
    CONFIG_FILE = "games_config.yml"
    ensure_unmounted()
    try:
        with open(CONFIG_FILE, "r") as f:
            games_config = yaml.safe_load(f)
    except Exception as e:
        print(f"{RED}Error loading configuration file: {e}{RESET}")
        sys.exit(1)

    print(f"{CYAN}Searching for installable games in {INSTALL_DIR}...{RESET}")
    
    installable_games = get_installable_games(games_config)

    if not installable_games:
        print(f"{RED}No valid games found (missing .bin files). Exiting.{RESET}")
        sys.exit(1)

    print(f"{CYAN}Found installable games:{RESET}")
    for idx, (key, config) in enumerate(installable_games.items(), start=1):
        print(f"{idx}) {config.get('display_name', key)}")
    
    print("all) Install all games sequentially")
    print("q) Exit menu")

    while True:
        user_input = input(f"{CYAN}Enter the number of the game to install, 'all' for all games, or 'q' to exit: {RESET}").strip().lower()

        if user_input.isdigit():
            choice = int(user_input)
            if 1 <= choice <= len(installable_games):
                key = list(installable_games.keys())[choice - 1]
                process_game(key, installable_games[key])
                break
            else:
                print(f"{RED}Invalid choice. Please try again.{RESET}")

        elif user_input == "all":
            existing_games = [key for key in installable_games if os.path.isdir(os.path.join(INSTALL_DIR, key))]
            force_overwrite = False
            
            if existing_games:
                user_input = input(f"{YELLOW}Some games are already installed. Do you want to overwrite all existing installations? (yes/no): {RESET}").strip().lower()
                force_overwrite = user_input == "yes"
            
            for key, config in installable_games.items():
                process_game(key, config, force_overwrite)
            break

        elif user_input == "q":
            print(f"{YELLOW}Exiting. No installations performed.{RESET}")
            sys.exit(0)

        else:
            print(f"{RED}Invalid input. Please try again.{RESET}")


if __name__ == "__main__":
    main()
