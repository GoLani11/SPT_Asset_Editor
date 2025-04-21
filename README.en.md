# SPT Tarkov Asset Editor

A tool to extract, preview, modify, and restore Texture2D images from `.assets` and `.bundle` files in the SPT Tarkov (Escape From Tarkov) game.

## Features

- Load and analyze Unity `.assets` and `.bundle` files.
- Automatically detect and list Texture2D textures within the file.
- Preview textures and view their properties.
- Extract and save original images (.png, .tga).
- Replace textures with custom images.
- Automatic resizing to match the original resolution.
- Automatic handling of transparency (alpha channel).
- Restore textures to their original state.
- Safe editing with automatic backup functionality.

## Installation and Execution

### Executable File (Recommended)

1. Download the latest version of the executable file from the [Releases page](https://github.com/yourusername/tarkov-asset-editor/releases).
2. Unzip the downloaded file.
3. Run the `SPTAssetEditor.exe` file.

### Running from Source Code (For Developers)

The following requirements are necessary to contribute to development or run the source code directly:

#### Requirements
- Python 3.7 or higher
- PyQt5
- Pillow (PIL Fork)
- UnityPy
- texture2ddecoder (for special texture format support)

#### Installation Steps
1. Clone this repository:
   ```
   git clone https://github.com/yourusername/tarkov-asset-editor.git
   cd tarkov-asset-editor
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Run the program:
   ```
   python src/main.py
   ```

## How to Use

### Opening Asset Files

1. Open an `.assets` or `.bundle` file using the "File → Open" menu or the Ctrl+O shortcut.
2. When opening a file for the first time, select a backup folder. Backups are created automatically.
3. All textures found within the file are displayed in the left sidebar.

### Modifying Textures

1. Select a texture from the list to preview it in the top panel.
2. Click the "Select Image..." button in the bottom panel to choose an image for replacement.
3. The selected image is automatically resized to match the resolution of the original texture.
4. Click the "Replace Image" button to replace the texture.
5. To save the modified asset file, use the "File → Save" menu or the Ctrl+S shortcut.

### Extracting and Saving Original Textures
1. Open an `.assets` or `.bundle` file using the "File → Open" menu or the Ctrl+O shortcut.
2. Select the image you want to extract in the Asset Browser area.
3. Click the "Save Original Texture" button below the "Loaded textures" text in the Asset Browser area.
4. Choose your desired image format (.png, .tga) and path, then save.
5. Activate the "Remove alpha channel when saving PNG" button to save the PNG file without transparency.

### Restoring Textures

1. Click the "Restore Original" button to revert the modified texture to its original state.
2. Restoration is done from the most recently saved backup file.

### Changing Post Item Images

1. Click the "Change Post Item Images" button at the top of the Asset Browser.
2. After confirming the information message, select the folder where your SPT game is installed.
3. The program automatically finds bundle files in the `EscapeFromTarkov_Data\StreamingAssets\Windows\assets\content\items\barter\item_barter_flyers` folder.
4. When the bundle file list appears, select the file you want to modify (e.g., `item_barter_flyers_letter*****`) and press 'OK'.
5. The textures within the selected bundle file will be displayed in the Asset Browser.
6. Proceed with the modification process as described in the standard "Modifying Textures" section.

## Precautions

- This tool is designed for use with the SPT (Single Player Tarkov) version.
- Modifying live server game files is not recommended and may result in an account ban by BattlEye anti-cheat.
- Always back up your original files before working on them.
- When modifying `.assets` files, the related `.resS` files must also be present.

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Credits

- [UnityPy](https://github.com/K0lb3/UnityPy) for Unity asset parsing.
- [texture2ddecoder](https://github.com/K0lb3/texture2ddecoder) for texture decoding.
- [Pillow (PIL Fork)](https://python-pillow.org/) for image processing.
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) UI framework.

## Reference Programs
- AssetStudio (https://github.com/Perfare/AssetStudio)
- UABEA (https://github.com/nesrak1/UABEA)

## AI Support
This project was developed with the assistance of Cursor AI. 