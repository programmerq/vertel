import os
import json
from pathlib import Path
from git import Repo, InvalidGitRepositoryError, GitCommandError

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


def validate_repo_path(repo_path):
    """Validate the git repository path."""
    if not repo_path:
        return  # Skip validation if the path is None.

    repo_path = expand_user_path(repo_path)
    if not os.path.isdir(repo_path):
        raise ValueError(f"Error: Git repository path {repo_path} does not exist.")

    try:
        repo = Repo(repo_path)
        if repo.is_dirty(untracked_files=False):
            raise ValueError(
                "Error: Working directory has uncommitted changes. Please stash or commit them."
            )
    except InvalidGitRepositoryError:
        raise ValueError(f"Error: {repo_path} is not a valid git repository.")
    except GitCommandError as e:
        raise ValueError(f"Error: Git operation failed: {e}")


def ensure_config_exists():
    """Ensure the configuration exists, prompting the user if needed."""
    config = ConfigDict()
    if not config.get("repo_path"):
        print("Configuration `repo_path` not found.")
        repo_path = input("Enter the path to your git repository checkout: ").strip()
        config["repo_path"] = expand_user_path(repo_path)
    if not config.get("db_path"):
        db_path = DEFAULT_DB_PATH
        config["db_path"] = str(db_path)
        # Create application support folder if not existing
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Save the configuration
    config.save()
    # print(f"Configuration saved to {config.config_path}")
    return config


def load_config():
    """Load the configuration and validate settings."""
    config = ensure_config_exists()

    try:
        repo_path = config.get("repo_path")
        if repo_path:  # Validate only if the repo path exists
            validate_repo_path(repo_path)

        db_path = config.get("db_path")
        if not db_path:
            db_path = str(DEFAULT_DB_PATH)
            config["db_path"] = db_path
            config.save()

    except ValueError as e:
        print(e)
        if "repo_path" in config:
            del config["repo_path"]
        load_config()  # Rerun setup process

    return config
