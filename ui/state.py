from dataclasses import dataclass
from typing import List


@dataclass
class SidebarInputs:
    new_openai: str
    new_discord: str
    enable_discord: bool
    new_role: str
    new_location: str
    job_type: List[str]
    selected_sites: List[str]
    is_remote: bool
    distance: int
    hours_old: int
    fetch_full_desc: bool
    new_target: int
    new_limit: int
    blacklist_list: List[str]
    enable_google: bool
    enable_drive: bool
    use_email: bool
    email_limit: int


@dataclass
class SidebarState:
    config: dict
    selected_profile: str
    current_profile_path: str
    inputs: SidebarInputs
