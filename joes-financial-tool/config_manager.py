#!/usr/bin/env python3
"""
Configuration file management utilities.

This module provides functions for managing financial configuration files,
including creating dated backups, listing available configs, and interactive
selection.
"""

import shutil
from pathlib import Path
from datetime import date
from typing import Sequence, Optional


def get_dated_config_name(base_name: str = "financial_config") -> str:
    """
    Generate a dated config filename.

    Parameters
    ----------
    base_name : str, optional
        Base name for the configuration file (default: "financial_config")

    Returns
    -------
    str
        Configuration filename with ISO date suffix, e.g., "financial_config_2025-10-09.json"

    Examples
    --------
    >>> get_dated_config_name()
    'financial_config_2025-10-09.json'
    >>> get_dated_config_name("my_config")
    'my_config_2025-10-09.json'
    """
    today = date.today().isoformat()
    return f"{base_name}_{today}.json"


def get_default_config_name() -> str:
    """
    Get the default (current) config name.

    Returns
    -------
    str
        The default configuration filename "financial_config.json"
    """
    return "financial_config.json"


def get_most_recent_config(directory: str = ".") -> str:
    """
    Get the most recent configuration file by date in filename.

    Searches for dated configuration files in the specified directory and returns
    the most recent one. Falls back to the default config if no dated configs exist.

    Parameters
    ----------
    directory : str, optional
        Directory to search for config files (default: current directory)

    Returns
    -------
    str
        Most recent configuration filename, or 'financial_config.json' if no dated
        configs found

    Examples
    --------
    >>> get_most_recent_config()
    'financial_config_2025-10-09.json'
    """
    configs = list_config_files(directory)

    if not configs:
        return "financial_config.json"

    # Configs are already sorted newest first
    # Skip "financial_config.json" and get the first dated one
    for filename, _ in configs:
        if filename.startswith("financial_config_") and filename.endswith(".json"):
            return filename

    # Fall back to default
    return "financial_config.json"


def list_config_files(directory: str = ".") -> Sequence[tuple[str, str]]:
    """
    List all financial configuration files in directory.

    Searches for all files matching the pattern "financial_config*.json" and returns
    them sorted by filename (newest dated configs first).

    Parameters
    ----------
    directory : str, optional
        Directory to search for config files (default: current directory)

    Returns
    -------
    Sequence[tuple[str, str]]
        List of tuples containing (filename, display_name) pairs, sorted with
        newest configs first

    Examples
    --------
    >>> list_config_files()
    [('financial_config.json', 'Current config (financial_config.json)'),
     ('financial_config_2025-10-09.json', 'Config from 2025-10-09'),
     ('financial_config_2025-10-08.json', 'Config from 2025-10-08')]
    """
    config_dir = Path(directory)
    configs: list[tuple[str, str]] = []

    # Look for dated configs
    for file_path in config_dir.glob("financial_config_*.json"):
        filename = file_path.name
        # Extract date from filename
        try:
            date_str = filename.replace("financial_config_", "").replace(".json", "")
            configs.append((filename, f"Config from {date_str}"))
        except ValueError as e:
            # If date parsing fails, use filename as display name
            configs.append((filename, filename))

    # Check for default config
    default_config = config_dir / "financial_config.json"
    if default_config.exists():
        configs.insert(
            0, ("financial_config.json", "Current config (financial_config.json)")
        )

    # Sort by filename (newest first for dated configs)
    configs.sort(key=lambda x: x[0], reverse=True)

    return configs


def select_config_interactive(directory: str = ".") -> Optional[str]:
    """
    Interactive configuration file selection menu.

    Displays all available configuration files and prompts the user to select one.

    Parameters
    ----------
    directory : str, optional
        Directory to search for config files (default: current directory)

    Returns
    -------
    Optional[str]
        Selected filename, or None if cancelled or no configs found

    Notes
    -----
    This function handles KeyboardInterrupt and EOFError gracefully, returning None
    when the user cancels the selection.
    """
    configs = list_config_files(directory)

    if not configs:
        print("\n❌ No config files found in current directory.\n")
        return None

    print("\nAvailable Configuration Files:\n")
    for i, (filename, display_name) in enumerate(configs, 1):
        print(f"  {i}. {display_name}")
    print("  0. Cancel")

    while True:
        try:
            choice = input(f"\nSelect config file (0-{len(configs)}): ").strip()
            if not choice.isdigit():
                print("⚠️  Please enter a number")
                continue

            choice_num = int(choice)

            if choice_num == 0:
                return None

            if 1 <= choice_num <= len(configs):
                selected_file = configs[choice_num - 1][0]
                print(f"\n✓ Selected: {selected_file}\n")
                return selected_file

            print(f"⚠️  Please enter a number between 0 and {len(configs)}")
        except KeyboardInterrupt:
            print("\n")
            return None
        except EOFError:
            return None


def create_backup(config_path: str) -> bool:
    """
    Create a dated backup copy of a configuration file.

    Creates a backup with the current date appended to the filename. If the source
    file doesn't exist, no backup is created.

    Parameters
    ----------
    config_path : str
        Path to the configuration file to backup

    Returns
    -------
    bool
        True if backup was created successfully, False otherwise

    Notes
    -----
    The backup is created in the same directory as the source file. If a backup
    with the same date already exists, it will be overwritten.

    Examples
    --------
    >>> create_backup("financial_config.json")
    ✓ Backup created: financial_config_2025-10-09.json
    True
    """
    try:
        source = Path(config_path)
        if not source.exists():
            return False

        # Create backup filename
        backup_name = get_dated_config_name(source.stem)
        backup_path = source.parent / backup_name

        # Copy file
        shutil.copy2(source, backup_path)

        print(f"✓ Backup created: {backup_name}")
        return True
    except (IOError, OSError) as e:
        print(f"⚠️  Backup failed: {e}")
        return False
