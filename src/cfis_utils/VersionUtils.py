# Standard libraries
import datetime

class VersionUtils():

    @staticmethod
    def increment_version(current_version_str: str) -> str:
        """
        Increments a version string based on the current date.

        Expected format for the input version string: 'vyyyy.mm.dd.xx' 
        (e.g., "v2025.04.12.05"). The 'xx' represents a revision number for the day.

        Logic:
        - If the date part (yyyy.mm.dd) in the input version matches today's date, 
          it increments the revision number ('xx').
        - If the date part is older than today, it updates the date part to 
          today's date and resets the revision number ('xx') to '01'.

        Args:
            current_version_str: The current version string in 'vyyyy.mm.dd.xx' format.

        Returns:
            The calculated next version string in 'vyyyy.mm.dd.xx' format.

        Raises:
            ValueError: If the input string format is invalid, does not start with 'v', 
                        does not match the expected 'vyyyy.mm.dd.xx' structure, 
                        contains an invalid date, or if the date part represents a future date.
        """
        # --- Validation and Parsing ---
        if not current_version_str.startswith('v'):
            raise ValueError("Version string must start with 'v'")
        
        parts = current_version_str[1:].split('.')
        if len(parts) != 4:
            raise ValueError("Version string format must be 'vyyyy.mm.dd.xx'")

        # Attempt to convert parts to integers
        year, month, day, revision = map(int, parts)
        
        # Create a date object to validate the date itself (e.g., rejects day 32)
        version_date = datetime.date(year, month, day)
        
        # --- Logic ---
        today = datetime.date.today()

        if version_date == today:
            # Same day: Increment revision
            next_rev = revision + 1
            next_year, next_month, next_day = year, month, day
        elif version_date < today:
                # Previous day: Update date to today, reset revision to 1
            next_rev = 1
            next_year, next_month, next_day = today.year, today.month, today.day
        else: # version_date > today
            # Future date: Invalid scenario
                raise ValueError(f"Version date {version_date} cannot be in the future compared to today {today}")

        # --- Formatting Output ---
        # Ensure month, day, and revision have leading zeros (01, 02, ..., 10, 11...)
        return f"v{next_year}.{next_month:02d}.{next_day:02d}.{next_rev:02d}"

if __name__ == "__main__":
    # Example usage
    version = "v2025.04.12.04"
    next_version = VersionUtils.increment_version(version)
    print(next_version)