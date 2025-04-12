# Standard libraries
from pathlib import Path
import os
# Third-party libraries
from src.cfis_utils.LoggerUtils import LoggerUtils
from src.cfis_utils.GitUtils import GitUtils
from src.cfis_utils.VersionUtils import VersionUtils

if __name__ == "__main__":
    # Get logger
    logger = LoggerUtils.get_logger(__name__)
    # Toml file path
    toml_file_path = Path("pyproject.toml")
    if not toml_file_path.is_file():
        raise FileNotFoundError(f"Configuration file not found at: {toml_file_path}")
    # Check git status
    is_clean, final_status = GitUtils.check_sync_status(os.getcwd())
    if not is_clean:
        raise RuntimeError(f"Git status check failed: {final_status}")
    # Get current version
    current_version = VersionUtils.get_version(toml_file_path)
    logger.info(f"Current version: {current_version}")
    # Increment version
    new_version = VersionUtils.increment_version(current_version)
    logger.info(f"New version: {new_version}")
    # Update version in toml file
    logger.info(f"Updating version in {toml_file_path}")
    VersionUtils.save_version(toml_file_path, new_version)
    # Commit changes
    logger.info("Committing changes")
    GitUtils.commit_all(os.getcwd(), f"Update version to {new_version}")
    # Generate and push a new tag
    logger.info(f"Generating and pushing tag {new_version}")
    GitUtils.create_tag(new_version, os.getcwd())
    GitUtils.push_tag(new_version, os.getcwd())
    # Final message
    logger.info(f"Version {new_version} has been successfully published.")
