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

def copy_content(src_dir, dest_dir):
	"""Copy the contents of src_dir into dest_dir."""
	find_cmd = f"find \"{src_dir}\" -type f"
	result = run_command(find_cmd, capture_output=True)
	if result.returncode == 0:
		files_to_copy = result.stdout.strip().splitlines()
		for src_file in files_to_copy:
			rel_path = os.path.relpath(src_file, src_dir)
			dest_file = os.path.join(dest_dir, rel_path)
			os.makedirs(os.path.dirname(dest_file), exist_ok=True)
			run_command(f"dd if=\"{src_file}\" of=\"{dest_file}\" bs=4M status=none")

def process_step(step, dest_dir):
	file_path = os.path.join(INSTALL_DIR, step.get("file"))
	if not os.path.isfile(file_path):
		print(f"{RED}File {file_path} not found. Skipping step.{RESET}")
		return False

	print(f"{CYAN}Processing file: {file_path}{RESET}")
	fs_type = step.get("filesystem", "ext2")
	mount_cmd = f"mount -t {fs_type} \"{file_path}\" \"{MOUNT_POINT}\""

	result = run_command(mount_cmd)
	if result.returncode != 0:
		print(f"{RED}Error mounting {file_path}{RESET}")
		return False

	os.makedirs(dest_dir, exist_ok=True)

	# Copy specified directories
	copy_dirs = step.get("copy_dirs", [])
	for directory in copy_dirs:
		dir_path = os.path.join(MOUNT_POINT, directory)
		copy_content(dir_path, dest_dir)

	# Handle destination subfolder for all contents
	destination_subfolder = step.get("destination_subfolder")
	if destination_subfolder:
		dest_subfolder_path = os.path.join(dest_dir, destination_subfolder)
		os.makedirs(dest_subfolder_path, exist_ok=True)
		copy_content(MOUNT_POINT, dest_subfolder_path)

	# Handle extra copy directories
	extra_copy_dirs = step.get("extra_copy_dirs", [])
	for extra in extra_copy_dirs:
		source = os.path.join(MOUNT_POINT, extra.get("source"))
		destination = os.path.join(dest_dir, extra.get("destination"))
		os.makedirs(destination, exist_ok=True)
		copy_content(source, destination)

	print(f"{CYAN}Unmounting {file_path}...{RESET}")
	run_command(f"umount \"{MOUNT_POINT}\"")
	print(f"{GREEN}Done processing file: {file_path}{RESET}")
	return True

def process_final_move(final_moves, dest_dir):
	"""Handle the final move operations after all other steps are completed."""
	for move in final_moves:
		source = os.path.join(dest_dir, move.get("source"))
		destination = os.path.join(dest_dir, move.get("destination"))
	
		if not os.path.exists(source):
			print(f"{RED}Source directory {source} does not exist. Skipping move.{RESET}")
			continue
	
		# Ensure the destination directory exists
		os.makedirs(destination, exist_ok=True)
		print(f"{CYAN}Moving content from {source} to {destination}{RESET}")
	
		# Move all contents of source into destination
		for item in os.listdir(source):
			item_path = os.path.join(source, item)
			destination_path = os.path.join(destination, item)
	
			# Move file or directory
			try:
				if os.path.isdir(item_path):
					os.rename(item_path, destination_path)
				else:
					os.replace(item_path, destination_path)
			except Exception as e:
				print(f"{RED}Error moving {item_path} to {destination_path}: {e}{RESET}")
	
		# Remove the empty source directory
		try:
			os.rmdir(source)
			print(f"{GREEN}Successfully moved contents from {source} to {destination} and cleaned up.{RESET}")
		except OSError as e:
			print(f"{RED}Could not remove directory {source}: {e}{RESET}")

def create_launcher(game_key, game_config, dest_dir):
	"""Create the .game launcher file in the specified path."""
	launcher_path = game_config.get("launcher_path", "")
	launcher_dir = os.path.join(dest_dir, launcher_path) if launcher_path else dest_dir
	os.makedirs(launcher_dir, exist_ok=True)

	launcher_file = os.path.join(launcher_dir, f"{game_key}.game")
	try:
		with open(launcher_file, "w") as f:
			f.write(f"# Launcher file for {game_key}\n")
		print(f"{GREEN}Launcher file created at {launcher_file}{RESET}")
	except Exception as e:
		print(f"{RED}Failed to create launcher file: {e}{RESET}")

def process_game(game_key, game_config):
	dest_dir = os.path.join(INSTALL_DIR, game_key)
	if os.path.isdir(dest_dir):
		print(f"{RED}The destination directory {dest_dir} already exists. Skipping game.{RESET}")
		return

	os.makedirs(dest_dir, exist_ok=True)
	steps = game_config.get("steps", [])
	for step in steps:
		process_step(step, dest_dir)

	# Handle final move operations
	final_moves = game_config.get("final_move", [])
	if final_moves:
		process_final_move(final_moves, dest_dir)

	# Create the launcher file
	create_launcher(game_key, game_config, dest_dir)

	print(f"{GREEN}Installation completed for {game_config.get('display_name', game_key)}{RESET}")

def main():
	CONFIG_FILE = "games_config.yml"
	try:
		with open(CONFIG_FILE, "r") as f:
			games_config = yaml.safe_load(f)
	except Exception as e:
		print(f"{RED}Error loading configuration file: {e}{RESET}")
		sys.exit(1)

	print(f"{CYAN}Searching for games to install in {INSTALL_DIR}...{RESET}")

	available_games = [(key, config) for key, config in games_config.items()]

	if not available_games:
		print(f"{RED}No games found in configuration file. Exiting.{RESET}")
		sys.exit(1)

	print(f"{CYAN}Found games to install:{RESET}")
	for idx, (key, config) in enumerate(available_games, start=1):
		print(f"{idx}) {config.get('display_name', key)}")

	print(f"all) Install all games sequentially")
	print(f"q) Exit menu")

	while True:
		user_input = input(f"{CYAN}Enter the number of the game to install, 'all' for all games, or 'q' to exit: {RESET}").strip().lower()

		if user_input.isdigit():
			choice = int(user_input)
			if 1 <= choice <= len(available_games):
				key, config = available_games[choice - 1]
				process_game(key, config)
				break
			else:
				print(f"{RED}Invalid choice. Please try again.{RESET}")

		elif user_input == "all":
			for key, config in available_games:
				process_game(key, config)
			break

		elif user_input == "q":
			print(f"{YELLOW}Exiting. No installations performed.{RESET}")
			sys.exit(0)

		else:
			print(f"{RED}Invalid input. Please try again.{RESET}")

if __name__ == "__main__":
	main()
