# Local imports
from . import LoggerUtils
# Third-party imports
from serial.tools.list_ports import comports

class SerialUtils():

    @staticmethod
    def get_available_serial_ports() -> list:
        """
        Returns a list of available serial ports.
        """
        try:
            ports = list(comports())
        except Exception as e:
            # Log error if comports fails and return an empty list
            logger = LoggerUtils.get_logger()
            logger.exception(f"Failed to retrieve serial ports: {e}", exc_info=True)
            return []

        return ports

    @staticmethod
    def log_available_serial_ports() -> None:
        """
        Logs available serial ports with device name and description.
        """
        logger = LoggerUtils.get_logger()    
        ports = SerialUtils.get_available_serial_ports()
        if not ports:
            logger.info("No serial ports detected.")
        else:
            num_ports = len(ports)
            logger.info(f"Found {num_ports} serial port(s):")
            # Log details for each port
            for i, port in enumerate(ports):
                is_last_port = (i == num_ports - 1)
                # Determine prefixes based on whether it's the last port
                port_prefix = "└──" if is_last_port else "├──"
                detail_indent = "    " if is_last_port else "│   "
                # Log port number line
                logger.info(f"  {port_prefix} Port {i+1}:")
                logger.info(f"  {detail_indent}├── Name        : {port.name}")
                logger.info(f"  {detail_indent}├── Device      : {port.device}")
                logger.info(f"  {detail_indent}└── Description : {port.description}")

if __name__ == "__main__":
    # Example usage
    SerialUtils.log_available_serial_ports()