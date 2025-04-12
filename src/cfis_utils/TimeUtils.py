# Standard libraries
import threading
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Generator, Callable


class TimeUtils:
    """
    Utility class providing time-related functionality.
    """
    
    @staticmethod
    @contextmanager
    def timer() -> Generator[Callable[[], float], None, None]:
        """
        Context manager for timing code execution.
        
        Usage:
            with TimeUtils.timer() as get_elapsed:
                # Your code here
                elapsed = get_elapsed()
            print(f"Operation took {elapsed:.2f} seconds")
        
        Returns:
            Callable[[], float]: A function that returns the elapsed time in seconds
        """
        start_time = time.perf_counter()
        def get_elapsed() -> float:
            return time.perf_counter() - start_time
        yield get_elapsed

    @staticmethod
    def format_time(seconds: float, precision: int = 2) -> str:
        """
        Format a given time in seconds into a human-readable string.

        Args:
            seconds (float): The time to format in seconds
            precision (int, optional): The number of decimal places to display. Defaults to 2.

        Returns:
            str: A human-readable string representing the given time
        """
        if seconds < 60:
            return f"{seconds:.{precision}f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.{precision}f} minute{'s' if minutes > 1 else ''}"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.{precision}f} hour{'s' if hours > 1 else ''}"
        else:
            days = seconds / 86400
            return f"{days:.{precision}f} day{'s' if days > 1 else ''}"