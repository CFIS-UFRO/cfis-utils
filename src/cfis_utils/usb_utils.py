# Standard libraries
from pathlib import Path
import sys
import shutil
import ctypes.util
# Local libraries
from . import OSUtils, LoggerUtils, TerminalUtils
# Third-party libraries
import usb.core
import usb.backend.libusb1


class UsbUtils:
    """
    Utility class for USB device configuration and management.
    """

    @staticmethod
    def install_libusb() -> None:
        """
        Installs libusb if not already installed.
        This function checks the operating system and installs libusb
        using the appropriate package manager.
        """
        # Get a logger
        logger = LoggerUtils.get_logger()
        logger.info("[USB] Installing libusb...")
        logger.info("[USB] Checking if libusb is installed...")
        # On windows, copy the libusb-1.0.dll file to the Python DLLs directory
        if OSUtils.is_windows():
            libusb_dll_path = Path(sys.executable).parent / "DLLs" / "libusb-1.0.dll"
            if not libusb_dll_path.exists():
                if OSUtils.is_64bit():
                    source = Path(__file__).parent / "libusb" / "windows" / "64" / "libusb-1.0.dll"
                else:
                    source = Path(__file__).parent / "libusb" / "windows" / "32" / "libusb-1.0.dll"
                shutil.copy(source, libusb_dll_path)
                logger.info(f"[USB] Libusb installed successfully")
            else:
                logger.info("[USB] Libusb found, skipping installation")
        # On Linux and Mac, check if libusb is installed, if not, install it using the package manager
        if OSUtils.is_linux() or OSUtils.is_mac():
            if not OSUtils.has_installed("libusb"):
                logger.info("[USB] Libusb not found, installing...")
                if OSUtils.has_apt():
                    cmd = "sudo apt update && sudo apt-get install -y libusb-1.0-0"
                elif OSUtils.has_dnf():
                    cmd = "sudo dnf install -y libusb1"
                elif OSUtils.has_brew():
                    cmd = "brew install libusb"
                else:
                    raise RuntimeError("Unsupported package manager, please install libusb manually")
                result = TerminalUtils.run_command(cmd, interactive=True) # Interactive because it needs sudo password on Linux
                if result.exit_code != 0:
                    raise RuntimeError("Failed to install libusb, please install it manually")
                logger.info("[USB] Libusb installed successfully")
            else:
                logger.info("[USB] Libusb found, skipping installation")

    @staticmethod
    def get_libusb_backend():
        """
        Gets the libusb backend for USB communication, trying multiple strategies.

        Attempts to find the backend automatically first. If that fails, searches
        in common OS-specific locations.

        Raises:
            usb.core.NoBackendError: If the libusb backend cannot be found after all attempts.

        Returns:
            The initialized libusb backend.
        """
        # Get a logger
        logger = LoggerUtils.get_logger()
        logger.info("[USB] Getting libusb backend...")
        # First try to get the backend using the standard method
        backend = None
        try:
            # First try to get the backend using the standard method
            backend = usb.backend.libusb1.get_backend()
            if backend:
                logger.info("[USB] Libusb backend found using standard method")
                return backend # Found it immediately
        except usb.core.NoBackendError:
             # Expected if not found automatically, continue to explicit search
            pass
        except Exception as e:
            # Log or handle unexpected errors during initial find
            print(f"Unexpected error during initial backend search: {e}")
            pass # Continue to explicit search

        logger.info("[USB] Libusb backend not found using standard method, trying explicit search...")

        # If standard method failed, try OS-specific searches
        found_path_str = None
        if OSUtils.is_mac():
            potential_paths = [
                Path("/opt/homebrew/lib/libusb-1.0.0.dylib"), # Apple Silicon
                Path("/usr/local/lib/libusb-1.0.0.dylib"),   # Intel
            ]
            for path in potential_paths:
                if path.exists():
                    found_path_str = str(path)
                    break
        elif OSUtils.is_linux():
            potential_names = ["libusb-1.0.so.0", "libusb-1.0.so"]
            for name in potential_names:
                found_path = ctypes.util.find_library(name)
                if found_path:
                    found_path_str = found_path
                    break
        elif OSUtils.is_windows():
            # Assume the DLL is placed here by the install_libusb method
            libusb_dll_path = Path(sys.executable).parent / "DLLs" / "libusb-1.0.dll"
            if libusb_dll_path.exists():
                found_path_str = str(libusb_dll_path)
            else:
                 # Try default search again just in case it's elsewhere in PATH
                 found_path_str = ctypes.util.find_library("libusb-1.0.dll")

        # If a path was found, try initializing the backend with it
        if found_path_str:
            logger.info(f"[USB] Found libusb at {found_path_str}, trying to use it...")
            try:
                backend = usb.backend.libusb1.get_backend(find_library=lambda x: found_path_str)
                if backend:
                    logger.info("[USB] Libusb backend found using explicit search")
                    return backend
            except usb.core.NoBackendError as e:
                logger.error(f"[USB] Libusb backend not found using explicit search: {e}")
            except Exception as e:
                logger.error(f"[USB] Unexpected error during explicit backend search: {e}")

        # If backend is still None after all attempts, raise error
        raise usb.core.NoBackendError("No libusb backend could be found.")

    @staticmethod
    def add_udev_rule(id_vendor: str, id_product: str) -> None:
        """
        Adds a udev rule for the USB device.
        This function creates a udev rule that allows the user to access
        the USB device without needing root permissions.
        Args:
            id_vendor (str): The vendor ID of the USB device.
            id_product (str): The product ID of the USB device.
        """
        # Get a logger
        logger = LoggerUtils.get_logger()
        logger.info("[USB] Adding udev rule...")
        if not OSUtils.is_linux():
            logger.warning("[USB] Udev rules are only supported on Linux")
            return
        # Create the udev rule
        rule_path = Path("/etc/udev/rules.d/99-amptek-px5.rules")
        if rule_path.exists():
            logger.info("[USB] udev rule already exists, skipping...")
        else:
            # Create the udev rule
            udev_rule_string = f'SUBSYSTEM=="usb", ATTR{{idVendor}}=="{id_vendor}", ATTR{{idProduct}}=="{id_product}", MODE="0666"'
            # Write it using sudo
            result = TerminalUtils.run_command(f"echo '{udev_rule_string}' | sudo tee {rule_path}", interactive=True)
            if result.exit_code != 0:
                raise RuntimeError(
                    "Failed to create udev rule, please create it manually"
                    f" at {rule_path} with the following content:\n{udev_rule_string}"
                    )
            logger.info("[USB] udev rule created successfully")
            # Reload udev rules
            result = TerminalUtils.run_command("sudo udevadm control --reload-rules && sudo udevadm trigger", interactive=True)
            if result.exit_code != 0:
                raise RuntimeError(
                    "Failed to reload udev rules, please reload them manually"
                    " with the following command:"
                    " sudo udevadm control --reload-rules && sudo udevadm trigger"
                    )
            logger.info("[USB] udev rules reloaded successfully")

if __name__ == "__main__":
    # Example usage
    UsbUtils.install_libusb()
