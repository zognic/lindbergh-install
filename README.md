# Lindbergh Game Installer Script

This Python script automates the installation of games for Lindbergh systems on [Batocera](https://batocera.org/) by mounting `.bin` images, extracting their content, and placing them in the correct directories. It also supports additional post-processing, such as moving specific files or folders and creating `.game` launcher files for each installed game.

## Features
- Mount `.bin` files using Linux file systems (`ext2`, `ext3`).
- Extract specified directories (e.g., `disk0`, `disk1`) and copy their content to the target folder.
- Handle multiple `.bin` files per game, supporting additional data files.
- Automate folder organization and file structure adjustments based on YAML configuration.
- Create `.game` launcher files in the appropriate directories.
- Log progress and provide clear feedback for each step of the process.

## Requirements
- Python 3.x
- YAML configuration file (`games_config.yml`) defining the games and their associated files.

## Supported Games

| Game                            | Key        | Files                             | Launcher Path     | Filesystem |
|---------------------------------|------------|-----------------------------------|-------------------|------------|
| 2 Spicy                         | 2spicy     | 2spicy.bin                        | elf               | ext2       |
| After Burner Climax (SDX)       | abclisdx   | abc.bin (disk0, disk1)            |                   | ext2       |
| Ghost Squad Evolution           | ghostsev   | gsevo.bin (disk0, disk1)          | vsg_l             | ext2       |
| Harley Davidson King of the Road | hdkotr    | harley.bin, harley_fs.bin, harley_fs2.bin | elf       | ext2       |
| The House of the Dead 4 (Rev A) | hotd4      | hotd4.bin                         | elf               | ext2       |
| The House of the Dead 4 Special | hotd4sp    | hotd4sp.bin                       | elf               | ext2       |
| The House of the Dead EX        | hotdex     | hotd4ex.bin                       | elf               | ext2       |
| Hummer Extreme Edition          | hummerxt   | hummer.bin                        |                   | ext2       |
| Initial D Arcade Stage 4 (Rev B)| initiad4b  | id4.bin                           |                   | ext2       |
| Initial D 4 (Export) (Rev D)    | initiad4ex | id4exp.bin                        |                   | ext2       |
| Initial D 5 (Export) (2.0)      | initiad5exa| initiald5.bin, id5_data.bin       | data              | ext3       |
| Let's Go Jungle                 | letsgoju   | lgj.bin                           |                   | ext2       |
| Outrun 2 SP SDX Rev A           | outr2sdx   | or2.bin                           | Jennifer          | ext2       |
| Outrun 2 SP SDX (Bootleg)       | outr2sdxg  | or2g.bin                          | Jennifer          | ext2       |
| Primeval Hunt                   | primevah   | primevil.bin                      | prog              | ext2       |
| R-Tuned: Ultimate Street Racing | rtuned     | rtuned.bin                        |                   | ext2       |
| Rambo (Export)                  | rambo      | rambo.bin                         | elf               | ext2       |
| Sega Race-TV (Export)           | segartv    | segartv.bin                       |                   | ext2       |
| Virtua Fighter 5                | vf5        | vf5.bin (disk0, disk1)            |                   | ext2       |
| Virtua Fighter 5 Rev C          | vf5c       | vf5c.bin, vf5c_rom.bin            | rom               | ext2       |
| Virtua Fighter 5 Final Showdown | vf5fs      | vf5fs.bin, vf5fs_ext.bin          | rom               | ext2       |
| Virtua Fighter 5 R              | vf5r       | vf5r.bin, vf5r_rom.bin            | rom               | ext2       |

## Looking for the right files?
If you're looking for the correct files for installation, performing a quick search with the keyword **SEGA_Lindbergh_YELLOW-RomVault** on Archives  may help you locate the appropriate `.bin` files needed for this script.


## Configuration Example (YAML)
Here’s an example of how games are defined in the `games_config.yml` file:

```yaml
vf5fs:
  display_name: "Virtua Fighter 5 Final Showdown"
  launcher_path: ""
  filesystem: "ext2"
  steps:
    - file: "vf5fs.bin"
      copy_dirs:
        - "disk0"
        - "disk1"
    - file: "vf5fs_ext.bin"
      copy_dirs: "rom"
      destination: "rom"

hdkotr:
  display_name: "Harley Davidson King of the Road"
  filesystem: "ext2"
  steps:
    - file: "harley.bin"
      copy_dirs:
        - "disk0"
    - file: "harley_fs.bin"
      copy_dirs: []
      destination_subfolder: "fs"
    - file: "harley_fs2.bin"
      copy_dirs: []
      destination_subfolder: "fs"
```

## Usage
1. Place the `games_config.yml` file in the same directory as the script.
2. Ensure that the required `.bin` files are present in the working directory.
3. Run the script using the following command:
   ```bash
   python3 lindbergh_installer.py
   ```
4. Follow the on-screen instructions to select a game to install, install all games, or exit.

## Notes
- The script reads the game configurations from the games_config.yml file. Each game's configuration includes the required .bin files, directories to copy, and additional processing steps.
- For games with multiple .bin files, the script processes each file according to the specified steps, including post-processing actions like file moves.
- If the target directory for a game already exists, the script skips the installation to avoid overwriting existing data.
- Launcher files (.game) are automatically created at the specified launcher_path in the configuration file or in the root directory if no launcher_path is provided.


## Youtube Explanation
https://www.youtube.com/watch?v=qN5M_liIpx0

