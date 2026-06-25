import sys
import shutil
from pathlib import Path
import webview
import base64
import os # import os

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This is the folder where bundled files are extracted
        base_path = sys._MEIPASS
    except Exception:
        # If _MEIPASS is not available, assume we are running in development mode
        # In development, base_path is the directory of the current script
        base_path = os.path.abspath(".")

    # Join the base path with the relative path to get the full path
    return os.path.join(base_path, relative_path)

def get_app_dir_for_output():
    """ Determines the base directory for the application, used for output folder """
    if getattr(sys, "frozen", False):
        # If running as a bundled exe, the app directory is where the executable is
        return Path(sys.executable).resolve().parent
    else:
        # If running in development mode, use the directory of the current script
        return Path(__file__).resolve().parent

# --- Configuration ---
# Define the name of the UI folder relative to the base path
UI_FOLDER_NAME = "ui" 
# Construct the path to the HTML file using get_resource_path
# This ensures it works both in development and when bundled
HTML_FILE = get_resource_path(os.path.join(UI_FOLDER_NAME, "renamer.html"))
# Determine the output directory next to the executable (or script in dev mode)
OUTPUT_DIR = get_app_dir_for_output() / "output"

class Api:
    def choose_files(self):
        """ Opens a file dialog for the user to select files """
        window = webview.windows[0]
        # Open a file dialog allowing multiple selections
        paths = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True
        )
        if not paths:
            return [] # Return empty list if no files were selected
        # Return a list of dictionaries, each containing file name and path
        # Path(p).name extracts just the filename from the full path
        return [{"name": Path(p).name, "path": str(p)} for p in paths]

    def save_files(self, files):
        """ Saves the processed files to the output directory """
        try:
            # Create the output directory if it doesn't exist
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

            saved_count = 0 # Counter for successfully saved files

            for item in files:
                new_name = item.get("newName")
                # Skip if the item doesn't have a new name (e.g., unchanged file)
                if not new_name:
                    continue

                # Construct the target path for the file, ensuring uniqueness
                target_path = self.get_unique_path(OUTPUT_DIR / new_name)

                # Handle dropped files (which come as base64 data)
                if item.get("dropped") and item.get("data"):
                    file_data = base64.b64decode(item["data"])
                    with open(target_path, "wb") as output_file:
                        output_file.write(file_data)
                # Handle files chosen via file dialog (which have a source path)
                else:
                    source_path = item.get("path")
                    if not source_path:
                        continue # Skip if source path is missing

                    # Copy the file from its original location to the target path
                    shutil.copy2(source_path, target_path)

                saved_count += 1 # Increment saved count

            # Return success status, count of saved files, and output directory path
            return {
                "success": True,
                "count": saved_count,
                "output": str(OUTPUT_DIR)
            }

        except Exception as e:
            # Return error details if any exception occurs
            return {
                "success": False,
                "error": str(e)
            }

    def get_unique_path(self, path):
        """ Generates a unique path by appending a counter if the file already exists """
        # If the path doesn't exist, return it as is
        if not path.exists():
            return path
        
        # If the path exists, generate a new unique path
        counter = 1
        # Split the path into directory, stem (name without extension), and suffix (extension)
        parent, stem = os.path.dirname(path), os.path.splitext(os.path.basename(path))[0]
        suffix = os.path.splitext(os.path.basename(path))[1]

        while True:
            # Create a new path with a counter, e.g., "file_1.txt", "file_2.txt"
            new_path = os.path.join(parent, f"{stem}_{counter}{suffix}")
            if not os.path.exists(new_path):
                return new_path # Return the first unique path found
            counter += 1

if __name__ == "__main__":
    # Ensure the output directory exists when the application starts
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    api = Api() # Instantiate the API
    
    # Create the main window for the webview application
    window = webview.create_window(
        title="Rayvern Editor",
        url=str(HTML_FILE), # Use the correctly constructed HTML file path
        width=480,
        height=750,
        resizable=True,
        js_api=api # Pass the API object to JavaScript
    )
    # Start the webview application event loop
    webview.start()
