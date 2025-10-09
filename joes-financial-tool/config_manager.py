#!/usr/bin/env python3
"""
Configuration file management utilities.
"""

import os
from pathlib import Path
from datetime import date
from typing import List, Optional


def get_dated_config_name(base_name: str = "financial_config") -> str:
    """Generate a dated config filename."""
    today = date.today().isoformat()
    return f"{base_name}_{today}.json"


def get_default_config_name() -> str:
    """Get the default (current) config name."""
    return "financial_config.json"


def get_most_recent_config(directory: str = ".") -> Optional[str]:
    """
    Get the most recent config file (by date in filename).

    Returns:
        Most recent config filename or 'financial_config.json' if no dated configs found
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


def list_config_files(directory: str = ".") -> List[tuple[str, str]]:
    """
    List all financial config files in directory.

    Returns:
        List of tuples: (filename, display_name)
    """
    config_dir = Path(directory)
    configs = []

    # Look for dated configs
    for file_path in config_dir.glob("financial_config_*.json"):
        filename = file_path.name
        # Extract date from filename
        try:
            date_str = filename.replace("financial_config_", "").replace(".json", "")
            configs.append((filename, f"Config from {date_str}"))
        except:
            configs.append((filename, filename))

    # Check for default config
    default_config = config_dir / "financial_config.json"
    if default_config.exists():
        configs.insert(0, ("financial_config.json", "Current config (financial_config.json)"))

    # Sort by filename (newest first for dated configs)
    configs.sort(key=lambda x: x[0], reverse=True)

    return configs


def select_config_interactive(directory: str = ".") -> Optional[str]:
    """
    Interactive config file selection.

    Returns:
        Selected filename or None if cancelled
    """
    configs = list_config_files(directory)

    if not configs:
        print("\n❌ No config files found in current directory.\n")
        return None

    print("\nAvailable Configuration Files:\n")
    for i, (filename, display_name) in enumerate(configs, 1):
        print(f"  {i}. {display_name}")
    print(f"  0. Cancel")

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
    Create a backup of the current config with timestamp.

    Returns:
        True if backup created successfully
    """
    try:
        source = Path(config_path)
        if not source.exists():
            return False

        # Create backup filename
        backup_name = get_dated_config_name(source.stem)
        backup_path = source.parent / backup_name

        # Copy file
        import shutil
        shutil.copy2(source, backup_path)

        print(f"✓ Backup created: {backup_name}")
        return True
    except Exception as e:
        print(f"⚠️  Backup failed: {e}")
        return False
