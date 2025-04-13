# Standard libraries
from pathlib import Path
from typing import Union

class FieldUtils:
    """
    Utility class for reading and writing specific fields from text files.
    """

    @staticmethod
    def get_field(
        file_path: Union[str, Path],
        field_name: str,
        separator: str = "=",
        enclosure: str = "\""
    ) -> str:
        """
        Reads the value of a specified field from a text file.

        Searches for the first line containing 'field_name <separator> ' and extracts
        the value part. Optionally removes the specified 'enclosure' string
        from the start and end of the extracted value.

        Args:
            file_path: The path to the text file.
            field_name: The name of the field (key) to search for.
            separator: The string separating the key and value (default: '=').
            enclosure: The string used to enclose the value (e.g., '"', "'"),
                       which will be removed from the start and end (default: "\"").

        Returns:
            The extracted value string.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If no line defining the field is found, or if the line
                        format is incorrect.
        """
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found at: {file_path}")

        # Trim the separator for accurate searching
        trimmed_separator = separator.strip()

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped_line = line.strip()
                # Check if the field name is present
                if field_name in stripped_line:
                    # Find the position of the separator
                    separator_pos = stripped_line.find(trimmed_separator)
                    if separator_pos != -1:
                        # Extract the key part and check if it matches exactly
                        key = stripped_line[:separator_pos].strip()
                        if key == field_name:
                            # Get the part after the separator and strip whitespace
                            value_part = stripped_line[separator_pos + len(trimmed_separator):].strip()
                            # Remove enclosure if it exists at both ends
                            if enclosure and value_part.startswith(enclosure) and value_part.endswith(enclosure):
                                value_part = value_part[len(enclosure):-len(enclosure)]
                            return value_part

        # If the loop finishes without finding the field
        raise ValueError(
            f"Could not find a line defining '{field_name}' "
            f"with separator '{trimmed_separator}' in {file_path}"
        )

    @staticmethod
    def save_field(
        target_file_path: Union[str, Path],
        field_name: str,
        new_value: str,
        separator: str = "=",
        enclosure: str = ""
    ) -> None:
        """
        Finds the first line starting with 'field_name <separator> ' and replaces
        the value part with the new value, optionally enclosing it.

        Args:
            target_file_path: The path to the file to modify.
            field_name: The name of the field (key) whose line needs modification.
            new_value: The new value string to write.
            separator: The string separating the key and value (default: '=').
                     Whitespace around the separator is handled automatically.
            enclosure: The string used to enclose the new value (e.g., '"', "'")
                       (default: "\"").

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If no line defining the field is found.
        """
        file_path = Path(target_file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Target file not found at: {file_path}")

        new_lines: list[str] = []
        line_found = False
        # Prepare the string to search for at the beginning of the relevant part of the line
        # We look for the field name, potential whitespace, and the separator
        search_pattern = f"{field_name}" # Start with field name

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped_line = line.lstrip() # Remove leading whitespace only

                # Check if the relevant part starts with the field name
                if not line_found and stripped_line.startswith(search_pattern):
                    # Find the actual separator in the stripped line
                    separator_pos = -1
                    temp_line_part = stripped_line[len(field_name):] # Part after field_name
                    separator_pos_in_part = temp_line_part.find(separator.strip())

                    if separator_pos_in_part != -1:
                         # Check if the part before the separator is just whitespace
                         part_before_sep = temp_line_part[:separator_pos_in_part].strip()
                         if not part_before_sep: # Ensure only whitespace between field_name and separator
                            separator_pos = len(field_name) + separator_pos_in_part
                            key = stripped_line[:separator_pos].strip() # Extract key to double-check

                            if key == field_name:
                                line_found = True
                                # Preserve original indentation
                                indent = len(line) - len(stripped_line)
                                indentation = ' ' * indent

                                # Format the value part with enclosure
                                value_part = f"{enclosure}{new_value}{enclosure}"

                                # Construct the new line, preserving original spacing around separator if possible,
                                # otherwise use ' <separator> '
                                # Get original spacing around separator
                                original_separator_with_spacing = temp_line_part[separator_pos_in_part : separator_pos_in_part + len(separator.strip())]
                                # Reconstruct using original spacing if just the separator, else default spacing
                                separator_to_write = separator.strip() # Default to no extra space
                                if original_separator_with_spacing == separator.strip():
                                    # Try to capture original spacing for reconstruction
                                    full_separator_match = temp_line_part[separator_pos_in_part:]
                                    import re
                                    match = re.match(r"(\s*" + re.escape(separator.strip()) + r"\s*)", full_separator_match)
                                    if match:
                                        separator_to_write = match.group(1)
                                    else: # fallback if regex fails somehow
                                        separator_to_write = f" {separator.strip()} "
                                else: # fallback if structure is unexpected
                                    separator_to_write = f" {separator.strip()} "


                                modified_line = f"{indentation}{field_name}{separator_to_write}{value_part}\n"
                                new_lines.append(modified_line)
                                continue # Skip appending the original line

                # Append the original line if it wasn't the target line or if target was already processed
                new_lines.append(line)

        if not line_found:
            raise ValueError(
                f"Could not find a line starting with '{field_name}' followed by separator '{separator.strip()}' in {file_path}"
            )

        # Write the modified content back to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)