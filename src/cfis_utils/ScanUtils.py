
# Standard libraries
from typing import Union, List, Tuple
import numbers
# Third-party libraries
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class ScanUtils():

    @staticmethod
    def generate_scan_points(
            end_point: Union[Tuple[numbers.Number, numbers.Number, numbers.Number],List[numbers.Number]],
            step_size: Union[numbers.Number, Tuple[numbers.Number, numbers.Number, numbers.Number], List[numbers.Number]],
            start_point: Tuple[numbers.Number, numbers.Number, numbers.Number] = (0.0, 0.0, 0.0),
            relative: bool = False, plot_points: bool = False
        ) -> List[List[float]]:
        """
        Generates a list of 3D coordinates for a full 3D serpentine scan pattern.

        The scan proceeds by:
        1. Sweeping X back and forth for each Y line.
        2. Sweeping Y back and forth for each Z plane.
        Includes the start point and the end_point coordinates for each axis.
        Optionally displays a 3D animation of the generated points path.

        Args:
            end_point (tuple or list): A sequence (max_x, max_y, max_z) representing the
                                    maximum coordinate values for the scan volume
                                    **relative** to the start_point.
            step_size (float or tuple/list): The step size(s).
                                            If a single number (float or int), it's used as the
                                            step size for X, Y, and Z dimensions.
                                            If a sequence (tuple or list), it must contain three
                                            positive numbers (step_x, step_y, step_z).
            start_point (tuple, optional): The (x, y, z) starting coordinates for the scan.
                                        Defaults to (0.0, 0.0, 0.0).
            relative (bool, optional): If False (default), returns absolute coordinates.
                                    If True, returns coordinates relative to the previous
                                    point in the sequence. The first point is relative
                                    to itself.
            plot_points (bool, optional): If True, displays a 3D animation of the
                                        scan path being traced. Defaults to False.

        Returns:
            list: A list of [x, y, z] coordinates for the scan points, rounded to 4 decimal places.

        Raises:
            ValueError: If end_point or step_size have incorrect format/values, or if any
                        resulting step size is non-positive.
            TypeError: If end_point or step_size have incorrect type.
        """
        # === Input Validation ===
        if not isinstance(end_point, (list, tuple)) or len(end_point) != 3:
            raise ValueError("end_point must be a list or tuple of length 3 (max_x, max_y, max_z).")
        if not all(isinstance(v, numbers.Number) for v in end_point):
            raise TypeError("end_point values must be numeric.")
        if isinstance(step_size, numbers.Number):
            step = float(step_size)
            if step <= 0:
                raise ValueError("If 'step_size' is a single number, it must be positive.")
            step_x = step_y = step_z = step
        elif isinstance(step_size, (list, tuple)) and len(step_size) == 3:
            if not all(isinstance(s, numbers.Number) for s in step_size):
                raise TypeError("step_size sequence values must be numeric.")
            steps = [float(s) for s in step_size]
            if any(s <= 0 for s in steps):
                raise ValueError("If 'step_size' is a sequence, all step sizes must be positive.")
            step_x, step_y, step_z = steps
        else:
            raise TypeError("step_size must be a single positive number or a list/tuple of 3 positive numbers.")
        if not isinstance(start_point, (list, tuple)) or len(start_point) != 3:
            raise ValueError("start_point must be a list or tuple of length 3 (x, y, z).")
        if not all(isinstance(v, numbers.Number) for v in start_point):
            raise TypeError("start_point values must be numeric.")

        # === Point Generation ===
        start_np = np.array(start_point, dtype=float)
        end_np = np.array(end_point, dtype=float)
        target_np = start_np + end_np # Absolute end coordinates

        # Calculate number of points per axis, handling zero distance case
        num_x = int(np.round(abs(end_np[0]) / step_x)) + 1 if abs(end_np[0]) > 1e-9 else 1
        num_y = int(np.round(abs(end_np[1]) / step_y)) + 1 if abs(end_np[1]) > 1e-9 else 1
        num_z = int(np.round(abs(end_np[2]) / step_z)) + 1 if abs(end_np[2]) > 1e-9 else 1

        # Generate base coordinate ranges using linspace
        x_coords_base = np.linspace(start_np[0], target_np[0], num=num_x)
        y_coords_base = np.linspace(start_np[1], target_np[1], num=num_y)
        z_coords = np.linspace(start_np[2], target_np[2], num=num_z)

        points_abs_list = []
        # Iterate through Z planes
        for z_idx, z in enumerate(z_coords):
            # Determine Y direction based on z_idx (plane index)
            if z_idx % 2 == 0:  # Even Z index: sweep Y forwards
                y_coords_iter = y_coords_base
                y_indices = range(num_y) # Original indices (0 to num_y-1)
            else:              # Odd Z index: sweep Y backwards
                y_coords_iter = y_coords_base[::-1] # Reversed Y coordinates
                y_indices = range(num_y - 1, -1, -1) # Original indices in reverse order

            # Iterate through Y lines within the current Z plane
            # y_idx_in_iter is the index within the current y_coords_iter (0 to num_y-1)
            # y is the actual Y coordinate value
            for y_idx_in_iter, y in enumerate(y_coords_iter):
                # effective_y_idx is the index this Y value had in the original y_coords_base
                effective_y_idx = y_indices[y_idx_in_iter]

                # Determine X direction based on the combined parity of effective_y_idx and z_idx
                # This ensures the X sweep direction continues correctly across Z planes
                if (effective_y_idx + z_idx) % 2 == 0: # Even combined index: sweep X forwards
                    x_coords_iter = x_coords_base
                else:                                  # Odd combined index: sweep X backwards
                    x_coords_iter = x_coords_base[::-1]

                # Iterate through X points for the current Y line
                for x in x_coords_iter:
                    points_abs_list.append([x, y, z])

        # Convert list to NumPy array and round
        points_abs_np = np.array(points_abs_list, dtype=float)
        points_abs_np = np.round(points_abs_np, 4)


        # === Plotting (Animation) ===
        if plot_points > 0:
            fig = plt.figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection='3d')

            # Set axis limits based on the full range of points
            margin = 1.0 # Add a small margin around the data
            min_coords = points_abs_np.min(axis=0)
            max_coords = points_abs_np.max(axis=0)
            ax.set_xlim(min_coords[0] - margin, max_coords[0] + margin)
            ax.set_ylim(min_coords[1] - margin, max_coords[1] + margin)
            ax.set_zlim(min_coords[2] - margin, max_coords[2] + margin)

            # Initialize plot elements for animation
            # line: shows the path traced so far
            # point: shows the current position marker
            line, = ax.plot([], [], [], color='blue', linestyle='-', linewidth=1.5, label='Scan Path')
            point, = ax.plot([], [], [], color='red', marker='o', markersize=5, label='Current Point')

            # Mark start and end points statically for reference
            ax.scatter(points_abs_np[0, 0], points_abs_np[0, 1], points_abs_np[0, 2],
                    c='green', marker='^', s=60, label='Start', depthshade=False)
            ax.scatter(points_abs_np[-1, 0], points_abs_np[-1, 1], points_abs_np[-1, 2],
                    c='black', marker='s', s=60, label='End', depthshade=False)

            # Setup plot labels and title
            ax.set_xlabel('X Axis')
            ax.set_ylabel('Y Axis')
            ax.set_zlabel('Z Axis')
            ax.set_title('Scan Path Animation')
            ax.legend(loc='upper left')

            # Update function called for each animation frame
            def update(i):
                # Update the line plot data up to the current frame (i)
                line.set_data(points_abs_np[:i+1, 0], points_abs_np[:i+1, 1])
                line.set_3d_properties(points_abs_np[:i+1, 2])
                # Update the current point marker position to frame i
                point.set_data([points_abs_np[i, 0]], [points_abs_np[i, 1]])
                point.set_3d_properties([points_abs_np[i, 2]])
                # Return the updated plot elements
                return line, point

            # Create the animation object
            # interval=50 ms -> 0.05 seconds per frame -> 20 frames per second
            # repeat=False -> animation stops after the last frame
            anim = FuncAnimation(fig, update, frames=len(points_abs_np), interval=50, repeat=False)

            plt.tight_layout() # Adjust layout
            plt.show() # Display the animation window


        # === Return requested coordinate type ===
        if relative:
            # Calculate differences between consecutive absolute points
            diffs = np.diff(points_abs_np, axis=0)
            # Prepend a zero vector for the first point (relative to itself)
            output = np.vstack((np.zeros((1, 3)), diffs))
        else:
            # Return absolute coordinates if relative=False
            output = points_abs_np
        # Round, convert to list, and return
        return np.round(output, 4).tolist()
    
if __name__ == "__main__":
    # Example usage
    points = ScanUtils.generate_scan_points((3, 3, 3), 1, plot_points=True)
    print(points)