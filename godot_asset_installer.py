import os
import sys
import json
import zipfile
import shutil
import requests
from io import BytesIO

# Godot Asset Library API Base
BASE_URL = "https://godotengine.org/asset-library/api"

def get_asset_info(asset_query):
    """Search for an asset by name or ID."""
    print(f"[*] Searching for '{asset_query}'...")
    if str(asset_query).isdigit():
        url = f"{BASE_URL}/asset/{asset_query}"
    else:
        # filter by query and ensure it's for Godot 4.x
        url = f"{BASE_URL}/asset?filter={asset_query}&godot_version=4.x"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if str(asset_query).isdigit():
            return data
        else:
            if not data.get('result'):
                print(f"[-] Asset '{asset_query}' not found for Godot 4.x")
                return None
            # Return the first match
            return data['result'][0]
    except Exception as e:
        print(f"[-] Error searching for {asset_query}: {e}")
        return None

def download_and_install(asset, target_root="godot"):
    asset_id = asset['asset_id']
    title = asset['title']
    
    # Get full details to get the download URL
    try:
        details = requests.get(f"{BASE_URL}/asset/{asset_id}").json()
        download_url = details.get('download_url')
        
        if not download_url:
            print(f"[-] No download URL found for {title}")
            return

        print(f"[*] Downloading {title} from {download_url}...")
        r = requests.get(download_url)
        r.raise_for_status()
        
        with zipfile.ZipFile(BytesIO(r.content)) as z:
            print(f"[*] Installing {title}...")
            
            # Heuristic: Find where the actual content is.
            # Some zips have a root folder like 'plugin-main/', others don't.
            # We look for 'addons/' folder primarily.
            
            members = z.namelist()
            has_addons = any("/addons/" in m or m.startswith("addons/") for m in members)
            
            for member in members:
                # If the zip contains an 'addons' folder, we extract its contents into godot/addons/
                if "/addons/" in member or member.startswith("addons/"):
                    # Get path relative to 'addons/'
                    if "/addons/" in member:
                        rel_path = member.split("/addons/", 1)[1]
                    else:
                        rel_path = member.split("addons/", 1)[1]
                    
                    if not rel_path: continue
                    
                    target_path = os.path.join(target_root, "addons", rel_path)
                else:
                    # If no 'addons' folder, we might want to put it in a specific folder under addons/
                    # but for now let's just extract to a folder named after the asset if it's not a standard plugin
                    sanitized_title = title.replace(" ", "_").lower()
                    target_path = os.path.join(target_root, "addons", sanitized_title, member)

                if member.endswith('/'):
                    os.makedirs(target_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with z.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                        
        print(f"[+] Successfully installed {title}")
    except Exception as e:
        print(f"[-] Error installing {title}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python godot_asset_installer.py <asset_name_or_id> [asset2] ...")
        sys.exit(1)

    assets_to_install = sys.argv[1:]
    
    # Ensure we are in the project root (where 'godot/' folder exists)
    if not os.path.exists("godot/project.godot"):
        print("[-] Error: Run this script from the project root (above the 'godot' directory).")
        sys.exit(1)

    for query in assets_to_install:
        asset = get_asset_info(query)
        if asset:
            download_and_install(asset)

if __name__ == "__main__":
    main()
