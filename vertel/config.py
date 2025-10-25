import os
import json
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "vertel" / "config.json"
DEFAULT_DB_PATH = Path.home() / "Library" / "Application Support" / "vertel" / "log_trace_index.db"


class ConfigDict(dict):
    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        if config_path.exists():
            with open(config_path, "r") as f:
                super().__init__(json.load(f))
        else:
            super().__init__()

    def save(self):
        """Save the configuration to the file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self, f, indent=4)

    def __delitem__(self, key):
        """Delete an item from the config and save."""
        if key in self:
            super().__delitem__(key)
            self.save()


def expand_user_path(path):
    """Expand ~ in paths to the full home directory path."""
    return str(Path(path).expanduser()) if path else None


def ensure_config_exists():
    """Ensure the configuration exists, creating default if needed."""
    config = ConfigDict()
    if not config.get("db_path"):
        db_path = DEFAULT_DB_PATH
        config["db_path"] = str(db_path)
        # Create application support folder if not existing
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # Save the configuration
        config.save()
    return config


def load_config():
    """Load the configuration and validate settings."""
    config = ensure_config_exists()

    db_path = config.get("db_path")
    if not db_path:
        db_path = str(DEFAULT_DB_PATH)
        config["db_path"] = db_path
        config.save()

    return config
