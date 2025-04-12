# Standard libraries
from pathlib import Path
from typing import Union
import datetime

class VersionUtils():

    @staticmethod
    def get_version(toml_file_path: Union[str, Path]) -> str:
        """
        Reads the version string directly from a TOML file by finding the first 
        line that starts with 'version' and follows the 'key = value' pattern.

        Args:
            toml_file_path: The path to the configuration file (e.g., 'pyproject.toml').

        Returns:
            The version string extracted from the file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If no line starting with 'version = ' (after stripping) is found,
                        or if the line format is incorrect after splitting.
        """
        # 1. Validate if the file exists
        if not Path(toml_file_path).is_file():
            raise FileNotFoundError(f"Configuration file not found at: {toml_file_path}")
        # 2. Open the file in read mode with UTF-8 encoding
        with open(toml_file_path, "r", encoding="utf-8") as f:
            # 3. Read line by line
            for line in f:
                # 4. Strip leading/trailing whitespace from the line
                stripped_line = line.strip()
                # 5. Check if the stripped line starts with "version"
                #    followed by potential whitespace and then '='
                if stripped_line.startswith("version"):
                    # Find the position of the first '='
                    equals_pos = stripped_line.find("=")
                    if equals_pos != -1:
                        # Check if 'version' is the keyword before '='
                        key = stripped_line[:equals_pos].strip()
                        if key == "version":
                            # 6. Get the part after '='
                            value_part = stripped_line[equals_pos + 1:].strip()
                            # 7. Remove leading/trailing quotes (single or double)
                            version_value = value_part.strip('"\'')
                            # Return the found version
                            return version_value
        # 8. If the loop finishes without finding the version
        raise ValueError(f"Could not find a line defining 'version' (e.g., 'version = \"...\") in {toml_file_path}")
    
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

    @staticmethod
    def save_version(toml_file_path: Union[str, Path], new_version: str) -> None:
        """
        Finds the line defining the project version in a TOML file and updates 
        it with the new version, saving the changes back to the file.

        It searches for the first line matching the 'version = "..."' pattern.

        Args:
            toml_file_path: The path to the configuration file (e.g., 'pyproject.toml').
            new_version: The new version string to write into the file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If no line starting with 'version = ' (after stripping) is found.
        """
        file_path = Path(toml_file_path)

        # 1. Validate if the file exists
        if not file_path.is_file():
            raise FileNotFoundError(f"Configuration file not found at: {file_path}")

        new_lines: list[str] = []
        version_line_found = False

        # 2. Read lines
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                # Use the same logic as get_version to find the line
                # Process only the *first* match found
                if not version_line_found: 
                    stripped_line = line.strip()
                    if stripped_line.startswith("version"):
                        equals_pos = stripped_line.find("=")
                        if equals_pos != -1:
                            key = stripped_line[:equals_pos].strip()
                            if key == "version":
                                # Found the line to modify
                                version_line_found = True
                                
                                # Preserve original indentation
                                indent = len(line) - len(line.lstrip(' '))
                                
                                # Construct the new line, adding quotes and newline
                                modified_line = f'{" " * indent}version = "{new_version}"\n'
                                new_lines.append(modified_line)
                                # Skip appending the original line, continue to next iteration
                                continue 

                # Append the original line if it wasn't the version line 
                # or if the version line was already found and processed
                new_lines.append(line)

        # 3. Check if the version line was actually found during the read phase
        if not version_line_found:
            raise ValueError(f"Could not find a line defining 'version' (e.g., 'version = \"...\") in {file_path}")

        # 4. Write the content back to the *same* file
        # Opening in 'w' mode overwrites the file completely
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

if __name__ == "__main__":
    # Example usage
    version = VersionUtils.get_version("pyproject.toml")
    next_version = VersionUtils.increment_version(version)
    VersionUtils.save_version("pyproject.toml", next_version)