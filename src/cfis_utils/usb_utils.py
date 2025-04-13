# Standard libraries
from pathlib import Path
import sys
import shutil
# Local libraries
from . import OSUtils, LoggerUtils, TerminalUtils
# Third-party libraries


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
            executable_path = sys.executable
            executable_dir = Path(executable_path).parent
            std_dlls_dir = Path(executable_dir) / "DLLs"
            libusb_dll_path = std_dlls_dir / "libusb-1.0.dll"
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