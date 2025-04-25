# Standard imports
import json
import time
import logging
from typing import Optional, Tuple, Union, Dict, Any, List
from pathlib import Path
# Local imports
from . import LoggerUtils
# Third-party imports
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict

class Spectrum:
    """
    Class to store and manipulate an X-ray fluorescence spectrum.
    """
    FORMAT_VERSION = "1.0" # Version for the custom JSON format

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes an empty Spectrum object.

        Args:
            logger: Optional logger instance. If None, a new one named "Spectrum"
                    will be created using LoggerUtils.
        """
        self.logger = logger if logger else LoggerUtils.get_logger("Spectrum")
        self._raw_counts: Optional[np.ndarray] = None
        self._background_counts: Optional[np.ndarray] = None
        # Linear calibration: energy = slope_a * channel + intercept_b
        self._cal_a: float = 1.0 # eV per channel (slope)
        self._cal_b: float = 0.0 # eV at channel 0 (intercept)
        self._metadata: Dict[str, Any] = OrderedDict() # Store metadata

    def set_raw_counts(self, counts: Union[List[int], np.ndarray]) -> None:
        """
        Sets the raw spectrum counts.

        Args:
            counts: A list or NumPy array of counts per channel.
        """
        if isinstance(counts, list):
            self._raw_counts = np.array(counts, dtype=np.int32)
        elif isinstance(counts, np.ndarray):
            # Ensure dtype is appropriate, copy to avoid external modification
            self._raw_counts = counts.astype(np.int32, copy=True)
        else:
            raise TypeError("counts must be a list or NumPy array.")

        if np.any(self._raw_counts < 0):
             self.logger.warning("Raw counts contain negative values.")
             self._raw_counts = np.maximum(0, self._raw_counts)

        # Reset background if the number of channels changes implicitly
        if self._background_counts is None or len(self._raw_counts) != len(self._background_counts):
            if self._background_counts is not None: # Log only if overwriting non-None
                self.logger.warning("Number of channels changed or background mismatch. Resetting background to zeros.")
            self._reset_background()
        self.logger.debug(f"Raw counts set with {len(self._raw_counts)} channels.")

    def set_calibration(self, slope_a: float, intercept_b: float) -> None:
        """
        Sets the linear energy calibration constants (Energy = A * channel + B).

        Args:
            slope_a: The slope (A) in eV/channel.
            intercept_b: The intercept (B) in eV for channel 0.
        """
        if not isinstance(slope_a, (int, float)) or not isinstance(intercept_b, (int, float)):
            raise TypeError("Calibration constants A and B must be numeric.")
        self._cal_a = float(slope_a)
        self._cal_b = float(intercept_b)
        self.logger.debug(f"Calibration set: A={self._cal_a}, B={self._cal_b}")

    def get_calibration(self) -> Tuple[float, float]:
        """Returns the calibration constants (A, B)."""
        return self._cal_a, self._cal_b

    def get_num_channels(self) -> int:
        """Returns the number of channels in the spectrum."""
        return len(self._raw_counts) if self._raw_counts is not None else 0

    def _calculate_energy_axis(self) -> Optional[np.ndarray]:
        """Internal helper to calculate the energy axis based on calibration."""
        num_channels = self.get_num_channels()
        if num_channels > 0:
            channels = np.arange(num_channels)
            energy = self._cal_a * channels + self._cal_b  # Energy = A * channel + B
            return energy
        return None

    def _reset_background(self) -> None:
        """Internal helper to set the background to zeros matching raw counts shape."""
        if self._raw_counts is not None:
            # Create a zeros array with the same shape and type as raw_counts
            self._background_counts = np.zeros_like(self._raw_counts, dtype=np.int32)
            self.logger.debug("Background reset to array of zeros.")
        else:
            # If no raw counts, background should also be None
            self._background_counts = None
            # Log a warning because this function shouldn't ideally be called without raw counts
            self.logger.warning("_reset_background called but no raw counts exist.")

    def get_data(self, use_energy_axis: bool = False, without_background: bool = False) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Returns the spectrum data (optionally background-subtracted) vs channels or energy.

        Args:
            use_energy_axis: If True, returns energy (eV) vs counts on the x-axis.
                             If False, returns channel vs counts. Defaults to False.
            without_background: If True, returns background-subtracted counts on the y-axis.
                                If False, returns raw counts. Defaults to False.

        Returns:
            A tuple (x_axis, y_counts) or None if no data is set or an error occurs.
            x_axis is either channel numbers or energy in eV.
            y_counts is either raw counts or background-subtracted counts (clipped at zero).
        """
        # Determine which counts to use (y-axis)
        y_counts: Optional[np.ndarray] = None
        if without_background:
            y_counts = self.get_counts_without_background()
            if y_counts is None:
                # This typically means raw_counts was None, which get_counts_without_background handles
                self.logger.warning("Cannot get background-subtracted data (raw counts likely missing).")
                return None
        else:
            y_counts = self._raw_counts
            if y_counts is None:
                self.logger.warning("No raw counts data available.")
                return None

        # Determine which axis to use (x-axis) based on the length of the selected y_counts
        num_channels = len(y_counts)
        x_axis: Optional[np.ndarray] = None
        if use_energy_axis:
            # Calculate energy axis based on the number of channels in y_counts
            channels_for_cal = np.arange(num_channels)
            x_axis = self._cal_a * channels_for_cal + self._cal_b
            if x_axis is None: # Should not happen if num_channels > 0
                 self.logger.error("Failed to calculate energy axis.")
                 return None
        else:
            # Return channel axis corresponding to y_counts
            x_axis = np.arange(num_channels)

        return x_axis, y_counts

    def add_metadata(self, metadata_dict: Dict[str, Any]) -> None:
        """
        Adds or updates metadata associated with the spectrum.

        Args:
            metadata_dict: A dictionary containing metadata key-value pairs.
        """
        if not isinstance(metadata_dict, dict):
            raise TypeError("metadata_dict must be a dictionary.")
        self._metadata.update(metadata_dict)
        self.logger.debug(f"Metadata updated: {metadata_dict}")

    def get_metadata(self) -> Dict[str, Any]:
        """Returns the current metadata dictionary."""
        return self._metadata.copy() # Return a copy

    def set_background(self, background_spectrum: 'Spectrum') -> None:
        """
        Sets another Spectrum object as the background for this spectrum.

        Args:
            background_spectrum: A Spectrum object containing the background data.

        Raises:
            TypeError: If background_spectrum is not a Spectrum instance.
            ValueError: If the number of channels does not match the main spectrum.
        """
        if not isinstance(background_spectrum, Spectrum):
            raise TypeError("background_spectrum must be an instance of Spectrum.")
        if self._raw_counts is None:
             raise ValueError("Cannot set background before setting raw counts for the main spectrum.")

        bg_counts = background_spectrum._raw_counts # Access internal directly
        if bg_counts is None:
             raise ValueError("The provided background spectrum object does not contain raw counts.")

        if self.get_num_channels() != len(bg_counts):
            raise ValueError(f"Channel count mismatch: Main spectrum has {self.get_num_channels()} channels, background has {len(bg_counts)} channels.")

        self._background_counts = bg_counts.astype(np.int32, copy=True) # Store a copy
        self.logger.debug(f"Background spectrum set with {len(self._background_counts)} channels.")

    def reset_background(self) -> None:
        """Resets the background spectrum to an array of zeros."""
        self._reset_background() # Call the helper

    def get_counts_without_background(self) -> Optional[np.ndarray]:
        """
        Returns the raw counts minus the background counts.
        Counts are clipped at zero (no negative counts).
        Returns:
            A NumPy array of background-subtracted counts, or None if no raw data.
        """
        if self._raw_counts is None:
            return None

        # Assume _background_counts is always an array (zeros or real) if _raw_counts exists
        if self._background_counts is None: # Should only happen if _reset_background failed when raw_counts was set
            self.logger.error("Background is None despite raw counts existing. Resetting background.")
            self._reset_background()
            if self._background_counts is None: # If reset still failed
                return self._raw_counts.copy() # Fallback

        if len(self._raw_counts) != len(self._background_counts):
            self.logger.error("Channel mismatch between raw and background counts during subtraction. Resetting background and returning raw counts.")
            self._reset_background() # Attempt to fix for future calls
            return self._raw_counts.copy()

        # Subtract (background might be zeros or actual data) and clip at zero
        subtracted_counts = np.maximum(0, self._raw_counts - self._background_counts)
        return subtracted_counts

    def save_as_mca(self, filename: Union[str, Path]) -> None:
        """
        Saves the spectrum counts to a MCA text file.

        This version ONLY writes the data block (counts per channel)
        preceded by "<<DATA>>" and followed by "<<END>>". No other metadata
        or headers are included.

        Args:
            filename: The path to the file to save (e.g., 'my_spectrum.mca').
        """
        if self._raw_counts is None:
            raise ValueError("Cannot save MCA file: No raw counts data available.")
        
        filepath = Path(filename).with_suffix(".mca")
        self.logger.info(f"Saving spectrum counts to MCA file: {filepath}")

        try:
            with filepath.open('w', encoding='utf-8') as f:
                # Write only the DATA block
                f.write("<<DATA>>\n")
                for count in self._raw_counts:
                    f.write(f"{count}\n")
                f.write("<<END>>\n")
            self.logger.info(f"Spectrum counts successfully saved to {filepath}")
        except IOError as e:
             self.logger.error(f"Failed to write MCA file {filepath}: {e}")
             raise IOError(f"Failed to write MCA file {filepath}: {e}") # Re-raise standard IOError

    def load_from_mca(self, filename: Union[str, Path]) -> None:
        """
        Loads spectrum counts from a MCA text file, replacing current data.

        This simplified version ONLY reads integer values found between lines
        starting with "<<DATA>>" and "<<END>>". All other lines and metadata
        are ignored. Existing calibration and metadata in the
        object are NOT reset by this method.

        Args:
            filename: The path to the MCA file to load.
        """
        filepath = Path(filename).with_suffix(".mca")
        self.logger.info(f"Loading spectrum counts from MCA file: {filepath}")
        if not filepath.is_file():
            raise FileNotFoundError(f"MCA file not found: {filepath}")

        raw_counts_list = []
        in_data_section = False

        try:
            with filepath.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue

                    if line.startswith("<<DATA>>"):
                        in_data_section = True
                        continue # Don't try to parse the tag itself as data
                    # Any other tag stops the data section
                    elif line.startswith("<<"):
                        in_data_section = False
                        # If we hit <<END>>, we can stop reading early
                        if line.startswith("<<END>>"):
                            break
                        continue

                    if in_data_section:
                        try:
                             raw_counts_list.append(int(line))
                        except ValueError:
                             self.logger.warning(f"Could not parse data line as integer: '{line}'")
                             continue

            if raw_counts_list:
                self.set_raw_counts(raw_counts_list)
            else:
                self.logger.warning("No valid data points found...")
                self._raw_counts = np.array([], dtype=np.int32)
                self._reset_background() # Ensure background is also None/empty

            self.logger.info(f"Spectrum counts successfully loaded from {filepath} ({self.get_num_channels()} channels).")

        except IOError as e:
             self.logger.error(f"Failed to read MCA file {filepath}: {e}")
             raise IOError(f"Failed to read MCA file {filepath}: {e}")
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred loading MCA file {filepath}")
            raise # Re-raise the original exception

    def save_as_json(self, filename: Union[str, Path]) -> None:
        """
        Saves the spectrum data, calibration, metadata, and background
        to a custom JSON format.

        Args:
            filename: The path to the file to save (e.g., 'my_spectrum.json').
                      Extension will be forced to .json.
        """
        if self._raw_counts is None:
             raise ValueError("Cannot save JSON file: No raw counts data available.")

        filepath = Path(filename).with_suffix(".json")
        self.logger.info(f"Saving spectrum to JSON file: {filepath}")

        data_to_save = {
            "format_version": self.FORMAT_VERSION,
            "num_channels": self.get_num_channels(),
            "calibration_a": self._cal_a,
            "calibration_b": self._cal_b,
            "metadata": self._metadata,
            "raw_counts": self._raw_counts.tolist(),
            "background_counts": self._background_counts.tolist() if self._background_counts is not None else None,
        }

        try:
            with filepath.open('w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4) # Use indent for readability
            self.logger.info(f"Spectrum successfully saved to {filepath}")
        except IOError as e:
             self.logger.error(f"Failed to write JSON file {filepath}: {e}")
             raise IOError(f"Failed to write JSON file {filepath}: {e}") # Re-raise standard IOError
        except TypeError as e:
            self.logger.error(f"Failed to serialize data to JSON: {e}. Check metadata types.")
            raise TypeError(f"Failed to serialize data to JSON: {e}") # Re-raise standard TypeError

    def load_json(self, filename: Union[str, Path]) -> None:
        """
        Loads spectrum data from a custom JSON file, replacing current data.

        Args:
            filename: The path to the JSON file to load.
        """
        filepath = Path(filename).with_suffix(".json")
        self.logger.info(f"Loading spectrum from JSON file: {filepath}")
        if not filepath.is_file():
            raise FileNotFoundError(f"JSON file not found: {filepath}")

        # Reset current state before loading
        self._raw_counts = None
        self._background_counts = None
        self._cal_a = 1.0
        self._cal_b = 0.0
        self._metadata = OrderedDict()

        try:
            with filepath.open('r', encoding='utf-8') as f:
                data = json.load(f)

            # Check format version
            file_version = data.get("format_version")
            if file_version != self.FORMAT_VERSION:
                self.logger.warning(f"Loading JSON file with version {file_version}, expected {self.FORMAT_VERSION}. Attempting to load anyway.")

            # Load data
            self.set_calibration(data.get('calibration_a', 1.0), data.get('calibration_b', 0.0))
            self.add_metadata(data.get('metadata', {}))

            raw_counts = data.get('raw_counts')
            if raw_counts is not None and isinstance(raw_counts, list):
                self.set_raw_counts(np.array(raw_counts, dtype=np.int32)) # This should trigger _reset_background if needed
            else:
                raise ValueError("JSON file 'raw_counts' is not a list or is missing.")

            bg_counts = data.get('background_counts')
            if bg_counts is not None and isinstance(bg_counts, list):
                # If background is explicitly provided, try to set it
                background_spectrum = Spectrum()
                background_spectrum.set_raw_counts(np.array(bg_counts, dtype=np.int32))
                try:
                    self.set_background(background_spectrum)
                except ValueError as e: # Catch channel mismatch from set_background
                    self.logger.warning(f"Failed to set background from JSON: {e}. Resetting background to zeros.")
                    self._reset_background() # Reset to zeros if loaded BG doesn't match
            # If bg_counts was None or not a list, set_raw_counts should have already called _reset_background
            elif self._background_counts is not None:
                # This case handles if set_raw_counts didn't reset because a valid BG already existed,
                # but the JSON explicitly lacks a background. Reset to zeros.
                self.logger.debug("JSON file has no background_counts, resetting background to zeros.")
                self._reset_background()

            # Validate num_channels if present
            if "num_channels" in data and data["num_channels"] != self.get_num_channels():
                 self.logger.warning(f"Number of channels in JSON ({data['num_channels']}) does not match length of loaded raw_counts ({self.get_num_channels()}).")

            self.logger.info(f"Spectrum successfully loaded from {filepath} ({self.get_num_channels()} channels).")

        except IOError as e:
             self.logger.error(f"Failed to read JSON file {filepath}: {e}")
             raise IOError(f"Failed to read JSON file {filepath}: {e}")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
             self.logger.exception(f"Failed to parse JSON file {filepath}") # Use exception for traceback
             # Reset state again in case of partial load
             self._raw_counts = None; self._background_counts = None; self._metadata = OrderedDict(); self._cal_a=1.0; self._cal_b=0.0
             raise ValueError(f"Failed to parse JSON file {filepath}: {e}") # Re-raise as ValueError or custom


    def plot(self,
             use_energy_axis: bool = False,
             show_raw: bool = False,       
             show_background: bool = False,  
             show_subtracted: bool = False, 
             log_scale: bool = False,
             title: Optional[str] = None) -> Optional[Tuple[plt.Figure, plt.Axes]]:
        """
        Plots the spectrum data using Matplotlib.

        Allows plotting raw counts, background counts, and/or background-subtracted counts.
        If none of show_raw, show_background, or show_subtracted are True,
        it defaults to plotting the raw counts. Assumes background is zeros if not set.

        Args:
            use_energy_axis: If True, plot against energy (eV). Else, plot against channel.
            show_raw: If True, plot the raw counts spectrum.
            show_background: If True, plot the background spectrum (even if it's just zeros).
            show_subtracted: If True, plot the background-subtracted spectrum.
            log_scale: If True, use a logarithmic scale for the y-axis.
            title: Optional title for the plot. If None, a default title is generated.

        Returns:
            A tuple containing the Matplotlib Figure and Axes objects, or None if plotting failed.
        """
        if self._raw_counts is None:
            self.logger.error("Cannot plot: No raw counts data available.")
            return None

        # --- Determine what to plot ---
        plot_raw_counts = show_raw
        plot_background = show_background
        plot_subtracted = show_subtracted

        # Default case: if no specific plot is requested, show raw counts
        if not plot_raw_counts and not plot_background and not plot_subtracted:
            plot_raw_counts = True
            self.logger.debug("Plotting raw counts by default as no specific trace was requested.")

        try:
             fig, ax = plt.subplots()

             # --- Determine X axis ---
             # Get data once, primarily for x-axis calculation based on raw counts length
             num_channels = self.get_num_channels()
             if num_channels == 0:
                  self.logger.warning("Cannot plot: Spectrum has zero channels.")
                  plt.close(fig)
                  return None

             x_axis_data: Optional[np.ndarray] = None
             if use_energy_axis:
                 x_axis_data = self._calculate_energy_axis()
                 if x_axis_data is None:
                      self.logger.error("Failed to calculate energy axis.")
                      plt.close(fig)
                      return None
                 xlabel = "Energy (eV)"
             else:
                 x_axis_data = np.arange(num_channels)
                 xlabel = "Channel"

             # --- Plot requested traces ---
             plotted_lines = [] # Keep track of plotted lines for legend
             all_plotted_y_data = [] # Collect y-data for limit calculation

             # Plot Raw Counts
             if plot_raw_counts:
                 line, = ax.plot(x_axis_data, self._raw_counts, label="Raw Counts", color='blue')
                 plotted_lines.append(line)
                 all_plotted_y_data.append(self._raw_counts)

             # Plot Background Counts
             if plot_background:
                 # Assuming _background_counts is always an array (zeros or real) if _raw_counts exists
                 if self._background_counts is not None:
                      if len(x_axis_data) == len(self._background_counts):
                            is_zero_bg = not np.any(self._background_counts)
                            bg_label = "Background (zeros)" if is_zero_bg else "Background"
                            line, = ax.plot(x_axis_data, self._background_counts, label=bg_label, alpha=0.7, color='orange', linestyle='--')
                            plotted_lines.append(line)
                            all_plotted_y_data.append(self._background_counts)
                      else:
                           self.logger.warning("Cannot plot background: Channel count mismatch.")
                 else:
                      # This case implies _raw_counts exists but background is None, which shouldn't happen with the zero-bg refactor
                      self.logger.error("Background is unexpectedly None. Cannot plot background.")

             # Plot Subtracted Counts
             if plot_subtracted:
                 subtracted_counts = self.get_counts_without_background()
                 if subtracted_counts is not None:
                      if len(x_axis_data) == len(subtracted_counts):
                            line, = ax.plot(x_axis_data, subtracted_counts, label="Subtracted", color='green')
                            plotted_lines.append(line)
                            all_plotted_y_data.append(subtracted_counts)
                      else:
                           self.logger.warning("Cannot plot subtracted counts: Channel count mismatch after subtraction.")
                 else: # Should only happen if raw counts are None
                     self.logger.error("Cannot plot subtracted counts: Raw counts are missing.")


             # --- Formatting ---
             ax.set_xlabel(xlabel)
             ax.set_ylabel("Counts")

             # Set Y limits based on the data actually plotted
             if all_plotted_y_data:
                 combined_y = np.concatenate(all_plotted_y_data)
                 min_y = np.min(combined_y) if combined_y.size > 0 else 0
                 max_y = np.max(combined_y) if combined_y.size > 0 else 1

                 if log_scale:
                     ax.set_yscale('log')
                     min_positive_val = np.min(combined_y[combined_y > 0]) if np.any(combined_y > 0) else 0.1
                     # Ensure bottom is positive and slightly below min positive, top has padding
                     current_top = ax.get_ylim()[1] # Get default top limit
                     new_top = max(current_top, max_y * 1.5) # Add some headroom
                     ax.set_ylim(bottom=max(0.01, min_positive_val * 0.5), top=new_top) # Ensure bottom > 0
                 else:
                      # Add padding for linear scale
                      padding = (max_y - min_y) * 0.05
                      if padding == 0: padding = 0.5 # Add padding if plot is flat
                      ax.set_ylim(bottom=min_y - padding, top=max_y + padding)
             elif log_scale: # Handle log scale even if no data was plotted (edge case)
                  ax.set_yscale('log')
                  ax.set_ylim(bottom=0.1, top=10) # Default log limits

             if title is None:
                  title = "Spectrum"
                  title += f" ({self.get_num_channels()} channels)"
             ax.set_title(title)

             ax.grid(True, which='both', linestyle='--', linewidth=0.5)
             # Add legend only if more than one distinct trace was plotted
             if len(plotted_lines) > 1:
                 ax.legend()

             fig.tight_layout()

             # Show the plot
             plt.show()

             return fig, ax

        except Exception as e:
            self.logger.exception("Error during plotting") # Log full traceback
            # Ensure figure is closed if created before error
            if 'fig' in locals() and fig is not None:
                 plt.close(fig)
            return None
        
if __name__ == "__main__":
    # Example usage
    spectrum = Spectrum()
    spectrum.set_raw_counts(np.random.randint(0, 100, size=1024))
    spectrum.set_calibration(0.1, 0.5)
    spectrum.add_metadata({"sample": "test", "date": time.strftime("%Y-%m-%d")})
    spectrum.plot(use_energy_axis=True, show_raw=True, show_background=True, show_subtracted=True, log_scale=False)
    spectrum.save_as_json("test_spectrum.json")
    spectrum.save_as_mca("test_spectrum.mca")
    other_spectrum = Spectrum()
    other_spectrum.load_json("test_spectrum.json")
    other_spectrum.plot(use_energy_axis=True, show_raw=True, show_background=True, show_subtracted=True, log_scale=False)
    other_spectrum.load_from_mca("test_spectrum.mca")
    other_spectrum.plot(use_energy_axis=True, show_raw=True, show_background=True, show_subtracted=True, log_scale=False)