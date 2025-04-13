# Standard libraries
import platform
import shutil

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