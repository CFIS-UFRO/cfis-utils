import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import colorlog

# Define a filter to add the level initial to the log record
class LevelInitialFilter(logging.Filter):
    """Adds 'levelinitial' attribute to log records."""
    def filter(self, record):
        # Get the first letter of levelname, capitalize it. Default to '?' if no levelname.
        record.levelinitial = record.levelname[0].upper() if record.levelname else '?'
        return True 

class LoggerUtils:
    """
    Utility class for configuring and retrieving logger instances.
    """

    @staticmethod
    def get_logger(name: str | None = None,
                   level: int = logging.DEBUG,
                   file_path: str | Path | None = None,
                   file_max_bytes: int = 100 * 1024, # 100 KB
                   file_backup_count: int = 1
                   ) -> logging.Logger:
        """
        Configures (if not already configured) and returns a standard logger
        with the specified name and level using the format:
        [asctime][name][LevelInitial] > message

        Handles colored console output and optional file logging.

        Args:
            name (str | None, optional): The name for the logger instance.
                                         Defaults to None, which results in 'logger'.
            level (int, optional): The minimum logging level the logger will process.
                                 Defaults to logging.DEBUG.
            file_path (str | Path | None, optional): If provided, logs will also be
                                                    written to this file path. Defaults to None.
            file_max_bytes (int, optional): Max size in bytes for the log file
                                            before rotation. Defaults to 100KB.
            file_backup_count (int, optional): Number of backup log files to keep.
                                               Defaults to 1.

        Returns:
            logging.Logger: A configured logger instance.
        """
        # Determine the effective name to use for the logger
        effective_name = name if name is not None else "logger"

        # Get the logger instance by the effective name
        logger = logging.getLogger(effective_name)

        # Configure the logger only if it doesn't have handlers already
        if not logger.handlers:
            # Set the overall minimum logging level for the logger
            logger.setLevel(level)

            # Add the custom filter to the logger itself
            # This makes 'levelinitial' available to all formatters
            logger.addFilter(LevelInitialFilter())

            # --- Formatter Definitions ---
            # Define the base format string
            log_format = '[%(asctime)s][%(name)s][%(levelinitial)s] > %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'

            # Standard formatter for file logging
            file_formatter = logging.Formatter(log_format, datefmt=date_format)

            # Colored formatter for console logging
            level_log_colors = {
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bold',
            }
            console_formatter = colorlog.ColoredFormatter(
                f'%(log_color)s{log_format}%(reset)s',
                datefmt=date_format,
                log_colors=level_log_colors,
                reset=True
            )

            # --- Console Handler: levels BELOW ERROR -> stdout ---
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setFormatter(console_formatter)
            stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
            logger.addHandler(stdout_handler)

            # --- Console Handler: levels ERROR and ABOVE -> stderr ---
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setFormatter(console_formatter)
            stderr_handler.setLevel(logging.ERROR) # Process only ERROR or higher
            logger.addHandler(stderr_handler)

            # --- Optional File Handler ---
            if file_path is not None:
                if isinstance(file_path, Path):
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                file_handler = RotatingFileHandler(
                    filename=file_path,
                    maxBytes=file_max_bytes,
                    backupCount=file_backup_count,
                    encoding='utf-8'
                )
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(level)
                logger.addHandler(file_handler)

            logger.propagate = False

        return logger

    @staticmethod
    def get_default_logger(name: str | None = None) -> logging.Logger:
        """
        Gets an existing logger or configures a default one as a fallback.
        Logic:
        1. If a logger with the specified name exists, return it.
        2. If no name is provided, check if the root logger has handlers.
           If it does, return the root logger.
        3. If no logger exists, configure a new logger with console output
           and DEBUG level.
        Uses the format: [asctime][name][LevelInitial] > message
        """
        if name is not None:
            if name in logging.manager.loggerDict:
                return logging.getLogger(name)
        else:
            root_logger = logging.getLogger()
            if root_logger.hasHandlers():
                return root_logger

        # Fallback: Configure logger with console output and DEBUG level.
        return LoggerUtils.get_logger(name=name, level=logging.DEBUG, file_path=None)
    
if __name__ == "__main__":
    # Example usage
    logger = LoggerUtils.get_logger(name="example_logger")
    logger.debug("This is an info message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")