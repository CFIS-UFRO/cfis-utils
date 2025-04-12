# Standard libraries
from pathlib import Path
# Local imports
from .LoggerUtils import LoggerUtils
from .GitUtils import GitUtils
from .VersionUtils import VersionUtils


class PublishUtils():

    @staticmethod
    def publish_new_python_package_version(toml_file_path: str, readme_file_path: str, repository_path: str) -> None:
        """
        Publishes a new version of a Python package.

        This function automates the process of updating the package version, committing the changes,
        creating a tag, and pushing everything to the remote repository.

        Assumptions:
        - The package version is stored in a `pyproject.toml` file, in a line starting with `version = `.
        - The README file is in Markdown format and contains a line starting with `**Latest stable tag**: `.
        - The package is managed using Git.
        - The version follows the format `vyyyy.mm.dd.xx` where `yyyy` is the year, `mm` is the month,
          `dd` is the day, and `xx` is a two-digit number representing the daily increment.

        Args:
            toml_file_path (str): The path to the pyproject.toml file.
            readme_file_path (str): The path to the README.md file.
            repository_path (str): The path to the Git repository.

        Raises:
            FileNotFoundError: If the pyproject.toml file is not found.
            RuntimeError: If the Git repository is not in a clean state.
        """
        # Get logger
        logger = LoggerUtils.get_logger(__name__)
        # Toml file path
        toml_file_path = Path("pyproject.toml")
        # Readme file path
        readme_file_path = Path("README.md")
        if not toml_file_path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {toml_file_path}")
        # Check git status
        is_clean, final_status = GitUtils.check_sync_status(repository_path)
        if not is_clean:
            raise RuntimeError(f"Git status check failed: {final_status}")
        # Get current version
        current_version = VersionUtils.get_version(toml_file_path)
        logger.info(f"Current version: {current_version}")
        # Increment version
        new_version = VersionUtils.increment_version(current_version)
        logger.info(f"New version: {new_version}")
        # Update version in toml and readme files
        logger.info(f"Updating version in {toml_file_path} and {readme_file_path}")
        VersionUtils.save_version(toml_file_path, "version = ", new_version, True)
        VersionUtils.save_version(readme_file_path, "**Latest stable tag**: ", new_version, False)
        # Commit and push changes
        logger.info("Committing changes")
        GitUtils.commit_all(repository_path, f"Update version to {new_version}")
        GitUtils.push(repository_path)
        # Generate and push a new tag
        logger.info(f"Generating and pushing tag {new_version}")
        GitUtils.create_tag(new_version, repository_path)
        GitUtils.push_tag(new_version, repository_path)
        # Final message
        logger.info(f"Version {new_version} has been successfully published.")