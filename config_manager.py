import json
import os

# 1. Define the Standard Path
DEFAULT_PROFILE_PATH = os.path.join("profiles", "default.json")

DEFAULT_CONFIG = {
    "openai_key": "",
    "discord_webhook": "",
    "role": "Software Engineer",
    "location": "New York",
    "target": 3,
    "safety_limit": 50,
    "enable_discord": False,
    "hours_old": 72,
    "scrape_sites": ["linkedin"],
    "job_type": ["fulltime"],
    "is_remote": False,
    "distance": 50,
    "fetch_full_desc": True,
    "blacklist": ["Manager", "Senior", "Director"],
    # Google Settings
    "enable_google": False,
    "enable_drive": False,
    "use_email": False,
    "email_max_results": 10
}

def get_effective_config(profile_path):
    """
    Loads the profile JSON and overrides settings based on 
    environmental constraints (like missing API keys).
    """
    # 1. Load the raw user preferences
    if not os.path.exists(profile_path):
        return {}
        
    with open(profile_path, "r") as f:
        config = json.load(f)

    # 2. Check Environment / Dependencies
    has_google_creds = os.path.exists("credentials.json")

    # 3. Sanitize / Override
    # If credentials are missing, we force these features OFF, 
    # regardless of what the user saved in the JSON file.
    if not has_google_creds:
        config['enable_drive'] = False
        config['use_email'] = False
        config['enable_google'] = False
        # You could also log a warning here if you wanted

    return config

def load_config(file_path=None):
    """
    Loads a configuration file.
    If no path is provided, defaults to 'profiles/default.json'.
    """
    # 2. Redirect to profiles/default.json if None
    if file_path is None:
        file_path = DEFAULT_PROFILE_PATH
        
    if not os.path.exists(file_path):
        save_config(DEFAULT_CONFIG, file_path)
        return DEFAULT_CONFIG
    
    with open(file_path, "r") as f:
        data = json.load(f)
        for key, value in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = value
        return data

def save_config(new_config, file_path=None):
    """
    Saves a configuration file.
    If no path is provided, defaults to 'profiles/default.json'.
    """
    # 3. Redirect to profiles/default.json if None
    if file_path is None:
        file_path = DEFAULT_PROFILE_PATH
        
    folder = os.path.dirname(file_path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
        
    with open(file_path, "w") as f:
        json.dump(new_config, f, indent=4)
        
    if new_config.get("openai_key"):
        os.environ["OPENAI_API_KEY"] = new_config["openai_key"]