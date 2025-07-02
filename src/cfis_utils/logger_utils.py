# Standard libraries
import logging
import sys
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Union, Optional, Any 
import re
# Third-party libraries
import colorlog
import colorama

# Initialize colorama for Windows compatibility
colorama.init()

# Define a filter to add the level initial to the log record
class _LevelInitialFilter(logging.Filter):
    """Adds 'levelinitial' attribute to log records."""
    def filter(self, record):
        record.levelinitial = record.levelname[0].upper() if record.levelname else '?'
        return True

class LoggerUtils:
    """
    Utility class for retrieving or configuring logger instances.
    Remembers the last requested logger name for exception handling.
    Also sets up global uncaught exception logging.
    """
    _last_logger_name: Optional[str] = None # Stores the name of the last logger requested

    @staticmethod
    def get_logger(name: Optional[str] = None,
                   level: int = logging.DEBUG,
                   file_path: Optional[Union[str, Path]] = None,
                   file_max_bytes: int = 100 * 1024, # 100 KB
                   file_backup_count: int = 1
                   ) -> logging.Logger:
        """
        Retrieves an existing configured logger or configures a new one.

        Retrieval Logic:
        1. If 'name' is provided, attempts to retrieve the logger with that name.
           If it exists and has handlers, it's returned.
        2. If 'name' is None, attempts to retrieve the last requested logger.
        3. If 'name' is None, attempts to retrieve the root logger.
           If it exists and has handlers, it's returned.
        4. If no existing logger is found, a new logger is configured with the provided parameters.

        Configuration Logic (if no existing logger is found):
        - A new logger is configured using the provided parameters.
        - The name used for the new logger is 'name' if provided, otherwise 'logger'.
        - Uses the format: [asctime][name][LevelInitial] » message
        - Handles colored console output (stdout for <ERROR, stderr for >=ERROR)
          and optional rotating file logging.

        Args:
            name (str | None, optional): The name for the logger instance.
                                         If None, checks for the root logger first,
                                         then defaults to 'logger' when configuring
                                         a new one. Defaults to None.
            level (int, optional): The minimum logging level for a newly configured logger.
                                 Defaults to logging.DEBUG.
            file_path (str | Path | None, optional): If provided, logs will also be
                                                    written to this file when configuring
                                                    a new logger. Defaults to None.
            file_max_bytes (int, optional): Max size in bytes for the log file
                                            before rotation (for new configuration).
                                            Defaults to 100KB.
            file_backup_count (int, optional): Number of backup log files to keep
                                               (for new configuration). Defaults to 1.

        Returns:
            logging.Logger: A configured logger instance (either existing or new).
        """

        # 1. Check for existing logger by provided name
        if name is not None:
            logger_candidate = logging.getLogger(name)
            if logger_candidate.hasHandlers():
                LoggerUtils._last_logger_name = name
                return logger_candidate

        # 2. Check for existing logger by last requested name
        elif LoggerUtils._last_logger_name is not None:
            logger_candidate = logging.getLogger(LoggerUtils._last_logger_name)
            if logger_candidate.hasHandlers():
                return logger_candidate

        # 3. Check for existing root logger if name is None
        elif name is None:
            logger_candidate = logging.getLogger()
            if logger_candidate.hasHandlers():
                LoggerUtils._last_logger_name = "root"
                return logger_candidate

        # 4. Configure a new logger if no existing one was found
        effective_name = name if name is not None else "logger"
        LoggerUtils._last_logger_name = effective_name
        logger_to_configure = logging.getLogger(effective_name)

        # Configure only if it doesn't have handlers already
        # (This check prevents re-configuration if getLogger returned an
        # existing but unconfigured logger placeholder)
        if not logger_to_configure.hasHandlers():
            logger_to_configure.setLevel(level)
            logger_to_configure.addFilter(_LevelInitialFilter())

            # Formatters
            log_format = '[%(asctime)s][%(levelinitial)s] » %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'
            file_formatter = logging.Formatter(log_format, datefmt=date_format)
            level_log_colors = {
                'DEBUG':    'cyan', 'INFO':     'green', 'WARNING':  'yellow',
                'ERROR':    'red', 'CRITICAL': 'red,bold',
            }
            console_formatter = colorlog.ColoredFormatter(
                f'%(log_color)s{log_format}%(reset)s',
                datefmt=date_format, log_colors=level_log_colors, reset=True
            )

            # Console Handlers (stdout < ERROR, stderr >= ERROR)
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setFormatter(console_formatter)
            stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
            logger_to_configure.addHandler(stdout_handler)

            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setFormatter(console_formatter)
            stderr_handler.setLevel(logging.ERROR)
            logger_to_configure.addHandler(stderr_handler)

            # Optional File Handler
            if file_path is not None:
                if isinstance(file_path, Path):
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

                file_handler = RotatingFileHandler(
                    filename=file_path, maxBytes=file_max_bytes,
                    backupCount=file_backup_count, encoding='utf-8'
                )
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(level)
                logger_to_configure.addHandler(file_handler)

            # Prevent propagation for non-root loggers
            if logger_to_configure.name != "root":
                 logger_to_configure.propagate = False
                 
        return logger_to_configure

    @staticmethod
    def remove_color_codes(text: str) -> str:
        """
        Remove ANSI color codes from the given text.

        Args:
            text (str): The text to remove the color codes from

        Returns:
            str: The text without the color codes
        """
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub('', text)

# --- Uncaught Exception Handling ---
def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """
    Logs uncaught exceptions using the last requested logger name.
    This function is assigned to sys.excepthook to handle errors globally.
    """
    logger = LoggerUtils.get_logger(name=LoggerUtils._last_logger_name)
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    traceback_str = "".join(tb_lines)
    message = f"Uncaught exception:\n{traceback_str}"
    logger.critical(message)

# Set the global exception hook to our custom handler
# This ensures that any unhandled exception triggers the logging function
sys.excepthook = _handle_uncaught_exception
# --- End Uncaught Exception Handling ---


if __name__ == "__main__":
    # Example usage
    logger = LoggerUtils.get_logger("test1")
    logger.info("This is an info message.")
    logger = LoggerUtils.get_logger("test2")
    logger.info("This is an info message.")
    logger = LoggerUtils.get_logger()
    logger.info("This is an info message.")
    a = 1/0
