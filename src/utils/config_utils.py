"""
Configuration utilities for environment variable expansion and validation.
"""

import os
import re
import json
from typing import Any, Dict, Union


def expand_environment_variables(config: Union[Dict, list, str, Any]) -> Any:
    """
    Recursively expand environment variables in configuration.
    
    Replaces placeholders like ${VAR_NAME} with actual environment variable values.
    
    Args:
        config: Configuration object (dict, list, string, or other)
        
    Returns:
        Configuration with environment variables expanded
    """
    if isinstance(config, dict):
        return {key: expand_environment_variables(value) for key, value in config.items()}
    
    elif isinstance(config, list):
        return [expand_environment_variables(item) for item in config]
    
    elif isinstance(config, str):
        return expand_string_variables(config)
    
    else:
        # Return other types unchanged (int, bool, None, etc.)
        return config


def expand_string_variables(text: str) -> str:
    """
    Expand environment variables in a string.
    
    Supports formats:
    - ${VAR_NAME} - Standard format
    - ${VAR_NAME:-default} - With default value (future enhancement)
    
    Args:
        text: String that may contain environment variable placeholders
        
    Returns:
        String with environment variables expanded
    """
    if not isinstance(text, str) or '${' not in text:
        return text
    
    # Pattern to match ${VAR_NAME}
    pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
    
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        
        if env_value is not None:
            return env_value
        else:
            # For now, raise an error if variable is not found
            # Could be enhanced to support default values
            raise ValueError(f"Environment variable '{var_name}' not found")
    
    try:
        return re.sub(pattern, replace_var, text)
    except ValueError as e:
        raise ValueError(f"Failed to expand environment variables in '{text}': {e}")


def load_config_with_env_expansion(config_file: str) -> Dict[str, Any]:
    """
    Load a JSON configuration file and expand environment variables.
    
    Args:
        config_file: Path to the JSON configuration file
        
    Returns:
        Configuration dictionary with environment variables expanded
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file has invalid JSON
        ValueError: If required environment variables are missing
    """
    with open(config_file, 'r') as f:
        raw_config = json.load(f)
    
    # Expand environment variables
    expanded_config = expand_environment_variables(raw_config)
    
    return expanded_config


def validate_required_env_vars(config: Dict[str, Any], required_vars: list = None) -> list:
    """
    Validate that required environment variables are set for a configuration.
    
    Args:
        config: Configuration dictionary
        required_vars: List of required environment variable names (optional)
        
    Returns:
        List of missing environment variable names
    """
    if required_vars is None:
        # Auto-detect required variables from SharePoint configs
        required_vars = []
        
        # Check common SharePoint variables
        sharepoint_vars = ['SHAREPOINT_TENANT_ID', 'SHAREPOINT_CLIENT_ID', 'SHAREPOINT_CLIENT_SECRET']
        for var in sharepoint_vars:
            if find_env_var_in_config(config, var):
                required_vars.append(var)
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars


def find_env_var_in_config(config: Any, var_name: str) -> bool:
    """
    Check if an environment variable is referenced in the configuration.
    
    Args:
        config: Configuration object to search
        var_name: Environment variable name to look for
        
    Returns:
        True if the variable is referenced, False otherwise
    """
    if isinstance(config, dict):
        return any(find_env_var_in_config(value, var_name) for value in config.values())
    
    elif isinstance(config, list):
        return any(find_env_var_in_config(item, var_name) for item in config)
    
    elif isinstance(config, str):
        return f'${{{var_name}}}' in config
    
    else:
        return False