from dataclasses import dataclass, field
from typing import List


@dataclass
class SidebarInputs:
    model_api_key: str
    model_provider: str
    model_name: str
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
    agent_models: dict = field(default_factory=dict)
    enable_notion: bool = False
    notion_api_key: str = ""
    notion_database_id: str = ""


@dataclass
class SidebarState:
    config: dict
    selected_profile: str
    current_profile_path: str
    inputs: SidebarInputs
