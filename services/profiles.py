import os
from config_manager import load_config, save_config

def get_profile_list():
    """Returns a list of .json files in profiles/ directory."""
    if not os.path.exists("profiles"):
        os.makedirs("profiles")
    
    files = [f for f in os.listdir("profiles") if f.endswith(".json")]
    if not files:
        # Create default if missing
        save_config(load_config(), "profiles/default.json")
        return ["default.json"]
    return files

def create_new_profile(name):
    """Creates a new profile file derived from default.json."""
    if not name.strip():
        return False, "Name cannot be empty"

    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    safe_name = safe_name.replace(" ", "_")
    filename = f"{safe_name}.json"
    new_path = os.path.join("profiles", filename)

    if os.path.exists(new_path):
        return False, "Name already in use!"

    base_config = load_config("profiles/default.json")
    base_config["role"] = safe_name
    save_config(base_config, new_path)
    
    return True, filename