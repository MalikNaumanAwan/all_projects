import shutil
from pathlib import Path

# Root directory to clean
ROOT_DIR = Path("/temp")

# Folder names you want to delete
FOLDERS_TO_DELETE = {"summaries", "articles"}


def delete_selected_folders(root_dir: Path, targets: set[str]):
    for folder in root_dir.rglob("*"):
        if folder.is_dir() and folder.name in targets:
            try:
                shutil.rmtree(folder)
                print(f"[✓] Deleted: {folder}")
            except Exception as e:
                print(f"[!] Failed to delete {folder}: {e}")


if __name__ == "__main__":
    delete_selected_folders(ROOT_DIR, FOLDERS_TO_DELETE)
