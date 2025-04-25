# Standard libraries
import gzip
import shutil
from pathlib import Path
from typing import Union, Optional

class CompressionUtils:
    """
    A utility class with compression methods.
    """

    @staticmethod
    def compress_file_gz(input_filepath: Union[str, Path],
                        output_filepath: Optional[Union[str, Path]] = None,
                        compresslevel: int = 9,
                        remove_original: bool = False) -> None:
        """
        Compresses a single file using gzip. Allows specifying compression level.

        Args:
            input_filepath: Path to the file to be compressed.
            output_filepath: Path for the compressed file. '.gz' will be appended if not provided.
                         If None, the compressed file will be saved in the same directory as input_filepath.
            compresslevel: Compression level (0-9). 9 is default (slowest, best compression).
                           0 is no compression. 1 is fastest (worst compression).
            remove_original: If True, the original file will be removed after compression.
                             Default is False (original file will be kept).

        Raises:
            ValueError: If compresslevel is not between 0 and 9.
        """
        # Validate compression level
        if not 0 <= compresslevel <= 9:
            raise ValueError("compresslevel must be between 0 and 9")

        # Is output_filepath None?
        if output_filepath is None:
            output_filepath = Path(input_filepath)

        # Ensure the input and output file paths are Path objects
        input_filepath = Path(input_filepath)
        output_filepath = Path(output_filepath)

        # Append '.gz' to output_filepath
        output_filepath = Path(str(output_filepath) + '.gz')

        # Open the input file in binary read mode and the output gzip file in binary write mode
        with open(input_filepath, 'rb') as f_in:
            with gzip.open(output_filepath, 'wb', compresslevel=compresslevel) as f_out:
                # Copy data in chunks from input to compressed output
                shutil.copyfileobj(f_in, f_out)
        
        # Remove the original file if specified
        if remove_original:
            if input_filepath.is_file():
                input_filepath.unlink()
            else:
                raise FileNotFoundError(f"Original file not found at: {input_filepath}")

    @staticmethod
    def decompress_file_gz(input_filepath: Union[str, Path],
                           output_filepath: Optional[Union[str, Path]] = None,
                           remove_original: bool = False) -> None:
        """
        Decompresses a single file compressed with gzip.

        Args:
            input_filepath: Path to the compressed file.
            output_filepath: Path where the decompressed file will be saved.
                            If None, the decompressed file will be saved in the same directory as input_filepath.
            remove_original: If True, the original compressed file will be removed after decompression.
        """
        # Is output_filepath None?
        if output_filepath is None:
            output_filepath = Path(str(input_filepath).replace('.gz', ''))

        # Ensure the input and output file paths are Path objects
        input_filepath = Path(input_filepath)
        output_filepath = Path(output_filepath)

        # If input file does not exist, try appending '.gz' 
        if not input_filepath.is_file():
            input_filepath = Path(str(input_filepath) + '.gz')
            if not input_filepath.is_file():
                raise FileNotFoundError(f"Compressed file not found at: {input_filepath}")

        # Open the compressed input file in binary read mode and the output file in binary write mode
        with gzip.open(input_filepath, 'rb') as f_in:
            with open(output_filepath, 'wb') as f_out:
                # Copy data in chunks from compressed input to decompressed output
                shutil.copyfileobj(f_in, f_out)

        # Remove the original compressed file if specified
        if remove_original:
            if input_filepath.is_file():
                input_filepath.unlink()
            else:
                raise FileNotFoundError(f"Compressed file not found at: {input_filepath}")