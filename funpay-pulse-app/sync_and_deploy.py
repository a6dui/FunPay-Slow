import os
import re
import shutil
import subprocess

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_MAIN = os.path.join(BASE_DIR, "backend", "main.py")
DESKTOP_SCRIPT = os.path.join(BASE_DIR, "desktop", "frontend", "script.js")
DESKTOP_FOLDER = os.path.join(BASE_DIR, "desktop", "frontend")
WEB_FOLDER = os.path.join(BASE_DIR, "frontend")

def update_version(new_version):
    print(f">>> Updating project to version {new_version}...")
    
    # 1. Update backend/main.py
    if os.path.exists(BACKEND_MAIN):
        with open(BACKEND_MAIN, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = re.sub(r'\"version\": \"[0-9.]+\"', f'\"version\": \"{new_version}\"', content)
        
        with open(BACKEND_MAIN, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ Updated {BACKEND_MAIN}")

    # 2. Update desktop/frontend/script.js
    if os.path.exists(DESKTOP_SCRIPT):
        with open(DESKTOP_SCRIPT, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = re.sub(r'const localVersion = \"[0-9.]+\"', f'const localVersion = \"{new_version}\"', content)
        
        with open(DESKTOP_SCRIPT, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ Updated {DESKTOP_SCRIPT}")

def sync_folders():
    if os.path.exists(DESKTOP_FOLDER) and os.path.exists(WEB_FOLDER):
        print(f">>> Syncing {DESKTOP_FOLDER} to {WEB_FOLDER}...")
        # Clean web folder
        for item in os.listdir(WEB_FOLDER):
            item_path = os.path.join(WEB_FOLDER, item)
            if item != ".git" and item != ".DS_Store":
                if os.path.isfile(item_path): os.remove(item_path)
                elif os.path.isdir(item_path): shutil.rmtree(item_path)
        
        # Copy desktop files to web
        for item in os.listdir(DESKTOP_FOLDER):
            if item == ".DS_Store": continue
            s = os.path.join(DESKTOP_FOLDER, item)
            d = os.path.join(WEB_FOLDER, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        print("✓ Frontend synchronization complete.")

def git_push(version):
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Release v.{version}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✓ Successfully pushed to GitHub!")
    except Exception as e:
        print(f"! Git error: {e}")

if __name__ == "__main__":
    current_version = "2.2.2" # Default starting point
    version = input(f"Enter new version (current is {current_version}): ").strip()
    
    if not version:
        print("Version cannot be empty.")
    else:
        update_version(version)
        sync_folders()
        
        do_push = input("Do you want to push to GitHub? (y/n): ").lower()
        if do_push == 'y':
            git_push(version)
        
        print("\n🚀 All updates completed! Deployment initiated.")
