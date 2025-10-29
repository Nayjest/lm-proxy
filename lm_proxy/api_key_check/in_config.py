"""
API Key check implementation that validates against configured groups.

Checks if a provided API key exists within any of the defined groups.
For using this function,
set "api_key_check" configuration value to "lm_proxy.api_key_check.check_api_key_in_config".
"""
from typing import Optional
from ..bootstrap import env


def check_api_key_in_config(api_key: Optional[str]) -> Optional[str]:
    """
    Validates a Client API key against configured groups and returns the matching group name.

    Args:
        api_key (Optional[str]): The Virtual / Client API key to validate.
    Returns:
        Optional[str]: The group name if the API key is valid and found in a group,
        None otherwise.
    """
    for group_name, group in env.config.groups.items():
        if api_key in group.api_keys:
            return group_name
    return None
