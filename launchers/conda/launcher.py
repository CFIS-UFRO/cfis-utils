#!/usr/bin/env python3
"""
CFIS Utils Conda Launcher
A cross-platform Python launcher for managing conda environments and running the main application.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
LOG_PREFIX = "[Conda launcher]"
ENV_NAME = "conda_env"
PYTHON_VERSION = "3.8"
REQUIREMENTS_FILE = "requirements.txt"
MAIN_SCRIPT = "main.py"
CHECK_GIT = True
# --- End Configuration ---


def log(message):
    """Print a message with the log prefix."""
    print(f"{LOG_PREFIX} {message}")


def run_command(cmd, capture_output=False, check=True):
    """Run a command and return the result."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode == 0, "", ""
    except subprocess.CalledProcessError as e:
        return False, "", str(e)


def check_conda():
    """Check if conda is available."""
    log("Checking if conda is available...")
    success, _, _ = run_command("conda --version", capture_output=True, check=False)
    if success:
        log("Conda found.")
        return True
    else:
        log("Error: Conda command not found. Please ensure Conda is installed and in your PATH.")
        return False


def check_git():
    """Check if git is available (if enabled)."""
    if not CHECK_GIT:
        return True
    
    log("Checking if git is available...")
    success, _, _ = run_command("git --version", capture_output=True, check=False)
    if success:
        log("Git found.")
        return True
    else:
        log("Error: Git command not found. Please ensure Git is installed and in your PATH.")
        return False


def environment_exists():
    """Check if the conda environment exists."""
    success, output, _ = run_command("conda env list", capture_output=True, check=False)
    if not success:
        return False
    
    # Check if our environment is in the list
    for line in output.split('\n'):
        if line.strip().startswith(ENV_NAME + ' ') or line.strip().startswith(ENV_NAME + '\t'):
            return True
    return False


def test_environment():
    """Test if the environment actually works."""
    success, _, _ = run_command(f"conda run --no-capture-output -n {ENV_NAME} python --version", capture_output=True, check=False)
    return success


def create_environment():
    """Create the conda environment."""
    log(f"Creating environment '{ENV_NAME}' with Python {PYTHON_VERSION}...")
    success, _, error = run_command(f"conda create -n {ENV_NAME} python={PYTHON_VERSION} -y", check=False)
    if not success:
        log(f"Error: Failed to create Conda environment '{ENV_NAME}'.")
        log(f"Error details: {error}")
        return False
    log(f"Environment '{ENV_NAME}' created successfully.")
    return True


def remove_environment():
    """Remove the conda environment."""
    log(f"Removing environment '{ENV_NAME}'...")
    success, _, _ = run_command(f"conda env remove -n {ENV_NAME} -y", check=False)
    return success


def install_requirements():
    """Install requirements in the environment."""
    if not Path(REQUIREMENTS_FILE).exists():
        log(f"Warning: Requirements file '{REQUIREMENTS_FILE}' not found. Skipping dependency installation.")
        return True
    
    log(f"Installing requirements from {REQUIREMENTS_FILE} into {ENV_NAME}...")
    success, _, error = run_command(f"conda run --no-capture-output -n {ENV_NAME} python -m pip install -r {REQUIREMENTS_FILE}", check=False)
    if not success:
        log(f"Error: Failed to install requirements in '{ENV_NAME}'.")
        log(f"Error details: {error}")
        return False
    log("Requirements installed/updated successfully.")
    return True


def autoconfigure():
    """Perform autoconfiguration: setup environment and install dependencies."""
    log("Starting autoconfiguration process...")
    
    # Check prerequisites
    if not check_conda():
        return False
    
    if not check_git():
        return False
    
    # Check environment
    log(f"Checking for environment: {ENV_NAME}...")
    if environment_exists():
        log(f"Environment '{ENV_NAME}' found, verifying it works...")
        if not test_environment():
            log(f"Environment '{ENV_NAME}' exists but is corrupted. Removing and recreating...")
            if not remove_environment():
                log("Failed to remove corrupted environment.")
                return False
            if not create_environment():
                return False
        else:
            log(f"Environment '{ENV_NAME}' is working correctly.")
    else:
        log(f"Environment '{ENV_NAME}' not found.")
        if not create_environment():
            return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    log("Autoconfiguration finished.")
    return True


def run_main(args):
    """Run the main script in the conda environment."""
    if not Path(MAIN_SCRIPT).exists():
        log(f"Error: Main script '{MAIN_SCRIPT}' not found.")
        return False
    
    # Check if environment exists and works before running
    needs_autoconfigure = False
    
    if not environment_exists():
        log(f"Environment '{ENV_NAME}' not found. Running autoconfigure first...")
        needs_autoconfigure = True
    elif not test_environment():
        log(f"Environment '{ENV_NAME}' exists but is corrupted. Running autoconfigure first...")
        needs_autoconfigure = True
    
    # Run autoconfigure if needed
    if needs_autoconfigure:
        log("Automatically running autoconfiguration...")
        if not autoconfigure():
            log("Autoconfiguration failed. Cannot run main script.")
            return False
        log("Autoconfiguration completed. Proceeding with main script execution...")
    
    # Build command
    cmd_parts = ["conda", "run", "--no-capture-output", "-n", ENV_NAME, "python", MAIN_SCRIPT]
    if args:
        cmd_parts.extend(args)
    
    cmd = " ".join(f'"{part}"' if " " in part else part for part in cmd_parts)
    
    if args:
        log(f"Executing {MAIN_SCRIPT} {' '.join(args)} in {ENV_NAME}...")
    else:
        log(f"Executing {MAIN_SCRIPT} in {ENV_NAME}...")
    
    success, _, error = run_command(cmd, check=False)
    if not success:
        log(f"Error: Failed to execute {MAIN_SCRIPT} in '{ENV_NAME}'.")
        log(f"Error details: {error}")
        return False
    
    log("Script execution finished successfully.")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CFIS Utils Conda Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py --autoconfigure    # Setup environment and install dependencies
  python launcher.py                    # Run main.py in the conda environment
  python launcher.py arg1 arg2          # Run main.py with arguments
        """
    )
    
    parser.add_argument(
        "--autoconfigure",
        action="store_true",
        help="Setup conda environment and install dependencies"
    )
    
    # Parse known args to allow forwarding unknown args to main script
    args, unknown_args = parser.parse_known_args()
    
    if args.autoconfigure:
        log("Autoconfigure flag detected.")
        log("---------------------------------------")
        success = autoconfigure()
        log("---------------------------------------")
        sys.exit(0 if success else 1)
    else:
        log("---------------------------------------")
        success = run_main(unknown_args)
        log("---------------------------------------")
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()