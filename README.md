# Lindbergh Game Installer Script

This Python script automates the installation of games for Lindbergh systems by mounting `.bin` images, extracting their content, and placing them in the correct directories. It also supports additional post-processing, such as moving specific files or folders and creating `.game` launcher files for each installed game.

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

| Game                          | Key     | Files                           |
|-------------------------------|---------|---------------------------------|
| Virtua Fighter 5 R            | `vf5r`  | `vf5r.bin`, `vf5r_rom.bin`      |
| Virtua Fighter 5 Final Showdown | `vf5fs` | `vf5fs.bin`, `vf5fs_ext.bin`    |
| Harley Davidson King of the Road | `hdkotr` | `harley.bin`, `harley_fs.bin`, `harley_fs2.bin` |
| After Burner Climax           | `abclimax` | `abc.bin`                      |

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
