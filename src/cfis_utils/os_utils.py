# Standard libraries
import platform
import shutil
# Local libraries
from . import TerminalUtils

class OSUtils:
    """
    Provides utility functions to determine OS details like type,
    package manager, and architecture.
    """
    @staticmethod
    def get_system():
        """Returns the operating system name ('Windows', 'Linux', 'Mac')."""
        system = platform.system()
        if system == 'Windows':
            return 'Windows'
        elif system == 'Linux':
            return 'Linux'
        elif system == 'Darwin':
            return 'Mac'
        else:
            return system # Return the system name if it's something else

    @staticmethod
    def is_windows():
        """Checks if the current operating system is Windows."""
        return OSUtils.get_system() == 'Windows'

    @staticmethod
    def is_linux():
        """Checks if the current operating system is Linux."""
        return OSUtils.get_system() == 'Linux'

    @staticmethod
    def is_mac():
        """Checks if the current operating system is macOS."""
        return OSUtils.get_system() == 'Mac'

    @staticmethod
    def has_apt():
        """
        Checks if the 'apt' package manager is available.
        Only relevant on Linux. Returns False otherwise.
        """
        if OSUtils.is_linux():
            return shutil.which('apt') is not None
        return False

    @staticmethod
    def has_dnf():
        """
        Checks if the 'dnf' package manager is available.
        Only relevant on Linux. Returns False otherwise.
        """
        if OSUtils.is_linux():
            return shutil.which('dnf') is not None
        return False

    @staticmethod
    def has_brew():
        """
        Checks if the 'brew' package manager (Homebrew) is available.
        Only relevant on macOS. Returns False otherwise.
        """
        if OSUtils.is_mac():
            return shutil.which('brew') is not None
        return False

    @staticmethod
    def get_architecture():
        """Returns the machine type (e.g., 'x86_64', 'AMD64', 'arm64')."""
        return platform.machine()
    
    @staticmethod
    def is_64bit():
        """
        Checks if the architecture is 64-bit.
        Returns True for 'x86_64', 'AMD64', and 'arm64'.
        """
        arch = OSUtils.get_architecture()
        return arch in ['x86_64', 'AMD64', 'arm64']
    
    @staticmethod
    def is_32bit():
        """
        Checks if the architecture is 32-bit.
        Returns True for 'x86', 'i386', and 'i686'.
        """
        arch = OSUtils.get_architecture()
        return arch in ['x86', 'i386', 'i686']
    
    @staticmethod
    def has_installed(package_name: str) -> bool:
        """
        Checks if a package/formula is installed using the system's package manager
        (supports dpkg via apt and dnf on Linux; brew on macOS) by querying
        installed packages and filtering with grep.

        Only functional on Linux or macOS systems.

        Args:
            package_name: The name of the package/formula to check (case-insensitive search).

        Returns:
            True if the package seems installed (grep found matches),
            False otherwise.
        """
        # Check if on a supported OS (Linux or Mac) first
        if not (OSUtils.is_linux() or OSUtils.is_mac()):
            return False

        # Initialize command variable
        command = ""

        # Determine command based on OS and available package manager
        if OSUtils.is_linux():
            if OSUtils.has_apt():
                command = f"dpkg -l | grep -i {package_name}"
            elif OSUtils.has_dnf():
                command = f"dnf list installed | grep -i {package_name}"
            else:
                return False
        elif OSUtils.is_mac():
            if OSUtils.has_brew():
                command = f"brew list | grep -i {package_name}"
            else:
                return False

        # If no command was set, return False
        if not command:
            return False

        # Execute the command and capture the output
        result = TerminalUtils.run_command(command)
        # Exit code 0 means the command ran AND grep found at least one match
        if result.exit_code == 0:
            return True
        # Exit code 1 typically means grep ran successfully but found no matches
        elif result.exit_code == 1:
            return False
        # Any other non-zero exit code indicates an error (e.g., dpkg/dnf/brew failed)
        else:
            return False
        
if __name__ == "__main__":
    # Example usage
    print(OSUtils.has_installed("python"))