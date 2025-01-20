#!/usr/bin/env python3
import os
import sys
import json
import subprocess  # Importation pour les commandes shell

# ANSI color codes for styling
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"

# Utiliser le répertoire courant comme répertoire cible
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

def process_additional_files(additional_files, dest_dir, game_key):
    for extra_file in additional_files:
        file_path = os.path.join(INSTALL_DIR, extra_file.get("file"))
        if not os.path.isfile(file_path):
            print(f"{RED}Additional file {file_path} not found. Skipping.{RESET}")
            continue

        print(f"{CYAN}Processing additional file: {file_path}{RESET}")
        fs_type = extra_file.get("filesystem", "ext2")
        mount_cmd = f"mount -t {fs_type} \"{file_path}\" \"{MOUNT_POINT}\""

        result = run_command(mount_cmd)
        if result.returncode != 0:
            print(f"{RED}Error mounting {file_path}{RESET}")
            continue

        copy_dirs = extra_file.get("copy_dirs", [])
        dest_subfolder = extra_file.get("destination_subfolder", "")
        full_dest_dir = os.path.join(dest_dir, dest_subfolder) if dest_subfolder else dest_dir
        os.makedirs(full_dest_dir, exist_ok=True)

        if copy_dirs:
            for directory in copy_dirs:
                dir_path = os.path.join(MOUNT_POINT, directory)
                find_cmd = f"find \"{dir_path}\" -type f"
                result = run_command(find_cmd, capture_output=True)
                if result.returncode == 0:
                    files_to_copy = result.stdout.strip().splitlines()
                    for src_file in files_to_copy:
                        rel_path = os.path.relpath(src_file, MOUNT_POINT)
                        dest_file = os.path.join(full_dest_dir, rel_path)
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        run_command(f"dd if=\"{src_file}\" of=\"{dest_file}\" bs=4M status=none")
        else:
            # Copy all files from the mount point
            find_cmd = f"find \"{MOUNT_POINT}\" -type f"
            result = run_command(find_cmd, capture_output=True)
            if result.returncode == 0:
                files_to_copy = result.stdout.strip().splitlines()
                for src_file in files_to_copy:
                    rel_path = os.path.relpath(src_file, MOUNT_POINT)
                    dest_file = os.path.join(full_dest_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    run_command(f"dd if=\"{src_file}\" of=\"{dest_file}\" bs=4M status=none")

        print(f"{CYAN}Unmounting {file_path}...{RESET}")
        run_command(f"umount \"{MOUNT_POINT}\"")
        print(f"{GREEN}Done processing additional file: {file_path}{RESET}")

def process_multi_phase(game_key, config, installed_files):
        filenames = config.get("filename")
        if not filenames:
            print(f"{RED}No filename specified for multi-phase processing of {game_key}.{RESET}")
            return False
        
        dest_dir = os.path.join(INSTALL_DIR, game_key)
        if os.path.isdir(dest_dir):
            print(f"{RED}The destination directory {dest_dir} already exists. Exiting to prevent overwriting.{RESET}")
            return False
        os.makedirs(dest_dir, exist_ok=True)
        
        first_file = os.path.join(INSTALL_DIR, filenames)
        first_config = config.copy()
        process_file_standard(first_file, first_config, dest_dir, installed_files, game_key)
        
        data_file = config.get("data_file")
        if data_file:
            data_file_path = os.path.join(INSTALL_DIR, data_file)
            if not os.path.isfile(data_file_path):
                print(f"{RED}Data file {data_file_path} not found. Skipping data phase.{RESET}")
            else:
                print(f"{CYAN}Processing data file: {data_file_path}{RESET}")
                copy_data_path = config.get("copy_data_path", "")
                full_copy_data_path = os.path.join(dest_dir, copy_data_path) if copy_data_path else dest_dir
                process_file_standard(data_file_path, {}, dest_dir_override=full_copy_data_path, installed_files=installed_files, create_launcher=False)
        
        additional_files = config.get("additional_files", [])
        if additional_files:
            process_additional_files(additional_files, dest_dir, game_key)
        
        return True


def process_file_standard(selected_file, config, dest_dir_override=None, installed_files=None, game_key="", create_launcher=True):
    base_name = os.path.basename(selected_file)
    dest_dir = dest_dir_override if dest_dir_override else os.path.join(INSTALL_DIR, game_key)

    if not dest_dir_override and os.path.isdir(dest_dir):
        print(f"{RED}The destination directory {dest_dir} already exists. Exiting to prevent overwriting.{RESET}")
        return False

    print(f"{CYAN}Processing: {base_name}{RESET}")

    if not selected_file.endswith(".bin"):
        print(f"{RED}Unsupported file extension: {selected_file}{RESET}")
        return False

    fs_type = config.get("filesystem", "ext2")
    print(f"{CYAN}Mounting the image (bin) with filesystem {fs_type}...{RESET}")
    mount_cmd = f"mount -t {fs_type} \"{selected_file}\" \"{MOUNT_POINT}\""

    result = run_command(mount_cmd)
    if result.returncode != 0:
        print(f"{RED}Error mounting {selected_file}{RESET}")
        return False

    os.makedirs(dest_dir, exist_ok=True)

    print(f"{CYAN}Starting copy...{RESET}")
    dirs_to_copy = config.get("copy_dirs", [])
    all_files = []
    for directory in dirs_to_copy:
        dir_path = os.path.join(MOUNT_POINT, directory)
        find_cmd = f"find \"{dir_path}\" -type f"
        result = run_command(find_cmd, capture_output=True)
        if result.returncode == 0:
            all_files.extend(result.stdout.strip().splitlines())

    for src_file in all_files:
        rel_path = os.path.relpath(src_file, MOUNT_POINT)
        for directory in dirs_to_copy:
            if rel_path.startswith(directory + os.sep):
                rel_path = rel_path[len(directory + os.sep):]
                break

        dest_file = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)

        run_command(f"dd if=\"{src_file}\" of=\"{dest_file}\" bs=4M status=none")

    print(f"{CYAN}Copy operation for {base_name} completed.{RESET}")
    print(f"{CYAN}Unmounting the image...{RESET}")
    run_command(f"umount \"{MOUNT_POINT}\"")
    print(f"{GREEN}Done processing {base_name}.{RESET}")

    if installed_files is not None:
        installed_files.append(selected_file)

    if create_launcher:
        launcher_path = config.get("launcher_path")
        if launcher_path:
            full_launcher_dir = os.path.join(dest_dir, launcher_path)
        else:
            full_launcher_dir = dest_dir

        os.makedirs(full_launcher_dir, exist_ok=True)
        launcher_file = os.path.join(full_launcher_dir, f"{game_key}.game")
        with open(launcher_file, "w") as f:
            f.write(f"Game launcher for {game_key}")
        print(f"{GREEN}Launcher file created at {launcher_file}{RESET}")

    print(f"{CYAN}--------------------------------------------{RESET}")
    return True

def main():
    print(f"{CYAN}Searching for installation game files in {INSTALL_DIR}...{RESET}")

    game_files = []
    mapping = []  # Stocker tuples (file_path, key)
    installed_files = []  # Liste des fichiers installés

    for key, cfg in games_config.items():
        filenames = cfg.get("filename")
        selected_file = None
        if isinstance(filenames, str):
            file_path = os.path.join(INSTALL_DIR, filenames)
            if os.path.isfile(file_path):
                selected_file = file_path

        if selected_file:
            game_files.append(selected_file)
            mapping.append((selected_file, key))

    if not game_files:
        print(f"{RED}No valid game files found based on the JSON configuration. Exiting.{RESET}")
        sys.exit(1)

    print(f"{CYAN}Found games to install:{RESET}")
    for idx, (file, key) in enumerate(mapping, start=1):
        config_entry = games_config.get(key, {})
        display_name = config_entry.get("display_name", key)
        print(f"{YELLOW}{idx}) {display_name}{RESET}")

    print(f"{YELLOW}all) Install all games sequentially{RESET}")
    print(f"{YELLOW}q) Exit menu{RESET}")

    while True:
        user_input = input(f"{CYAN}Enter the number of the game to install, 'all' for all games, or 'q' to exit: {RESET}").strip().lower()

        if user_input.isdigit():
            choice = int(user_input)
            if 1 <= choice <= len(mapping):
                selected_file, key = mapping[choice-1]
                config = games_config.get(key, {})

                if "additional_files" in config and "filename" in config:
                    process_multi_phase(key, config, installed_files)
                else:
                    dest_override = os.path.join(INSTALL_DIR, key)
                    process_file_standard(selected_file, config, dest_dir_override=dest_override, installed_files=installed_files, game_key=key)
                print(f"{GREEN}Installation completed for selected game.{RESET}")
                break
            else:
                print(f"{RED}Invalid choice. Please try again.{RESET}")

        elif user_input == "all":
            for idx, (file, key) in enumerate(mapping, start=1):
                config = games_config.get(key, {})
                if "additional_files" in config and "filename" in config:
                    process_multi_phase(key, config, installed_files)
                else:
                    dest_override = os.path.join(INSTALL_DIR, key)
                    process_file_standard(file, config, dest_dir_override=dest_override, installed_files=installed_files, game_key=key)
            print(f"{GREEN}All selected installations completed.{RESET}")
            break

        elif user_input == "q":
            print(f"{YELLOW}Exiting menu. No installations performed.{RESET}")
            sys.exit(0)

        else:
            print(f"{RED}Invalid input. Please try again.{RESET}")

    # Proposer de supprimer les fichiers installés
    if installed_files:
        print(f"{CYAN}The following files were used for installation:{RESET}")
        for file in installed_files:
            print(f"  {YELLOW}{file}{RESET}")

        delete_choice = input(f"{CYAN}Do you want to delete these files? (Y/N): {RESET}").strip().lower()
        if delete_choice == "y":
            for file in installed_files:
                try:
                    os.remove(file)
                    print(f"{GREEN}Deleted {file}{RESET}")
                except Exception as e:
                    print(f"{RED}Failed to delete {file}: {e}{RESET}")
        else:
            print(f"{YELLOW}No files were deleted.{RESET}")

if __name__ == "__main__":
    # Charger la configuration
    CONFIG_FILE = "games_config.json"
    try:
        with open(CONFIG_FILE, 'r') as f:
            games_config = json.load(f)
    except Exception as e:
        print(f"{RED}Error loading configuration file: {e}{RESET}")
        sys.exit(1)

    main()
