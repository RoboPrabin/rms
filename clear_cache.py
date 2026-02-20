import os
import shutil

def clear_pycache(root_dir):
    deleted_count = 0
    print(f"Searching in: {root_dir}\n" + "-"*30)
    
    for root, dirs, files in os.walk(root_dir):
        # 1. Delete __pycache__ directories
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing: {pycache_path}")
            shutil.rmtree(pycache_path)
            dirs.remove('__pycache__') # Don't recurse into deleted dir
            deleted_count += 1
            
        # 2. Delete individual .pyc or .pyo files just in case
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"Removed file: {file_path}")

    print("-"*30)
    print(f"Cleanup complete. Removed {deleted_count} cache folders.")

if __name__ == "__main__":
    # Get the directory where this script is located
    project_path = os.path.dirname(os.path.abspath(__file__))
    clear_pycache(project_path)