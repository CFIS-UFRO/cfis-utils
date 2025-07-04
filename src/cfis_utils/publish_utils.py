# Standard libraries
from pathlib import Path
import logging
# Local imports
from . import LoggerUtils, GitUtils, VersionUtils, FieldUtils

class PublishUtils():

    @staticmethod
    def _sync_requirements_to_toml(requirements_path: str, toml_file_path: str, logger: logging.Logger = None) -> None:
        """
        Synchronizes dependencies from requirements.txt to pyproject.toml.
        
        Args:
            requirements_path (str): Path to the requirements.txt file.
            toml_file_path (str): Path to the pyproject.toml file.
            logger (logging.Logger, optional): Logger instance to use.
        
        Raises:
            FileNotFoundError: If requirements.txt or pyproject.toml is not found.
        """
        logger = logger or LoggerUtils.get_logger()
        
        requirements_file = Path(requirements_path)
        toml_file = Path(toml_file_path)
        
        if not requirements_file.is_file():
            raise FileNotFoundError(f"Requirements file not found at: {requirements_file}")
        if not toml_file.is_file():
            raise FileNotFoundError(f"TOML file not found at: {toml_file}")
        
        # Read requirements.txt
        logger.info(f"Reading requirements from: {requirements_file}")
        with open(requirements_file, 'r', encoding='utf-8') as f:
            requirements = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        
        # Convert git dependencies to pyproject.toml format
        toml_dependencies = []
        for requirement in requirements:
            if requirement.startswith('git+'):
                # Extract package name from git URL
                # Example: git+https://github.com/user/repo.git -> repo
                git_url = requirement
                if git_url.endswith('.git'):
                    repo_name = git_url.split('/')[-1][:-4]  # Remove .git extension
                else:
                    repo_name = git_url.split('/')[-1]
                
                # Format for pyproject.toml: "package-name @ git+url"
                toml_format = f'{repo_name} @ {git_url}'
                toml_dependencies.append(toml_format)
            else:
                toml_dependencies.append(requirement)
        
        # Update dependencies in pyproject.toml using FieldUtils
        logger.info(f"Updating dependencies in: {toml_file}")
        FieldUtils.save_field_list(toml_file, "dependencies", toml_dependencies)
        
        logger.info(f"Successfully synced {len(toml_dependencies)} dependencies to {toml_file}")

    @staticmethod
    def publish_new_python_package_version(toml_file_path: str, readme_file_path: str, repository_path: str, requirements_path: str, logger: logging.Logger = None) -> None:
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
            requirements_path (str): Path to requirements.txt file to sync dependencies.
            logger (logging.Logger, optional): Logger instance to use. If None, a new logger is created.

        Raises:
            FileNotFoundError: If the pyproject.toml file is not found.
            RuntimeError: If the Git repository is not in a clean state.
        """
        # Get logger
        logger = logger or LoggerUtils.get_logger()
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
        # Sync requirements to pyproject.toml dependencies
        logger.info("Syncing requirements.txt to pyproject.toml dependencies")
        PublishUtils._sync_requirements_to_toml(requirements_path, toml_file_path, logger)
        # Get current version
        current_version = FieldUtils.get_field(toml_file_path, "version", "=", "\"")
        logger.info(f"Current version: {current_version}")
        # Increment version
        new_version = VersionUtils.increment_version(current_version)
        logger.info(f"New version: {new_version}")
        # Update version in toml and readme files
        logger.info(f"Updating version in {toml_file_path} and {readme_file_path}")
        FieldUtils.save_field(toml_file_path, "version", new_version, "=", "\"")
        FieldUtils.save_field(readme_file_path, "**Latest stable tag**", new_version, ": ", "")
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