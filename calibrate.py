from typing import Dict, Optional, Tuple

import numpy as np
from pymmcore_plus import CMMCorePlus
from rich import print
np.set_printoptions(suppress=True)

# Exception class for calibration failure
class CalibrationFailedException(Exception):
    pass


def parabolic_subpixel(corr: np.ndarray, peak: Tuple[int, int]) -> Tuple[float, float]:
    """
    Refines the peak location using a simple parabolic fit.
    The peak is given as (row, col) indices.
    Returns (subpixel_row_offset, subpixel_col_offset) corrections.
    """
    peak_y, peak_x = peak
    sub_y = 0.0
    sub_x = 0.0
    # For x (columns)
    if 0 < peak_x < corr.shape[1] - 1:
        left = corr[peak_y, peak_x - 1]
        center = corr[peak_y, peak_x]
        right = corr[peak_y, peak_x + 1]
        denom = 2 * center - left - right
        if denom != 0:
            sub_x = (left - right) / (2 * denom)
    # For y (rows)
    if 0 < peak_y < corr.shape[0] - 1:
        top = corr[peak_y - 1, peak_x]
        center = corr[peak_y, peak_x]
        bottom = corr[peak_y + 1, peak_x]
        denom = 2 * center - top - bottom
        if denom != 0:
            sub_y = (top - bottom) / (2 * denom)
    return sub_y, sub_x


def phase_correlate(
    img1: np.ndarray, img2: np.ndarray, eps: float = 1e-10
) -> Tuple[Tuple[float, float], float]:
    """
    Estimates the translation shift between two images using phase correlation.

    Args:
        img1: First input image as a 2D NumPy array.
        img2: Second input image as a 2D NumPy array.
        eps: Small constant to avoid division by zero.

    Returns
    -------
        A tuple ((shift_x, shift_y), peak_value), where shift_x and shift_y
        are the estimated subpixel shifts (in pixels) needed to align img2 to img1,
        and peak_value is the correlation peak magnitude.
    """
    print("Computing phase correlation...", img1.shape, img2.shape)

    # Compute the FFTs of the two images.
    F1 = np.fft.fft2(img1)
    F2 = np.fft.fft2(img2)

    # Compute cross-power spectrum.
    R = F1 * np.conjugate(F2)
    R /= np.abs(R) + eps

    # Compute cross-correlation by inverse FFT and shift zero-frequency to center.
    corr = np.fft.ifft2(R)
    corr = np.fft.fftshift(corr)
    corr_abs = np.abs(corr)

    # Locate the peak.
    peak_idx = np.unravel_index(np.argmax(corr_abs), corr.shape)
    center = np.array(corr.shape) // 2
    # Integer shift estimate (note: indices are in (row, col) order)
    shift_y = peak_idx[0] - center[0]
    shift_x = peak_idx[1] - center[1]

    # Refine estimate with subpixel interpolation.
    sub_y, sub_x = parabolic_subpixel(corr_abs, peak_idx)
    shift_x += sub_x
    shift_y += sub_y

    # Return shift as (dx, dy) in pixels along x and y, respectively.
    return (shift_x, shift_y), corr_abs[peak_idx]


def get_subimage(image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    """Return a subimage (ROI) from image using slicing."""
    return image[y : y + h, x : x + w]


def subtract_minimum(image: np.ndarray) -> np.ndarray:
    """Subtract the minimum pixel value from all pixels."""
    return image - np.min(image)


def measure_displacement(
    proc1: np.ndarray, proc2: np.ndarray, display: bool = False
) -> Tuple[float, float]:
    """
    Measures displacement between two images using phase correlation.
    Returns (dx, dy). The 'display' flag is available if you want to show intermediate results.
    """
    # Convert images to float32 for phaseCorrelate
    shift, _ = phase_correlate(np.float32(proc1), np.float32(proc2))
    if display:
        print(f"Measured displacement (dx, dy): {shift}")
    return shift  # (dx, dy)


def generate_affine_transform(
    point_pairs: Dict[Tuple[float, float], Tuple[float, float]],
) -> np.ndarray:
    """
    Given point pairs mapping image displacements (dx, dy) to stage positions (sx, sy),
    solve for the affine transformation (as a 3x3 matrix) that satisfies:
        [sx]   [a  b  c] [dx]
        [sy] = [d  e  f] [dy]
        [1 ]   [0  0  1] [1 ]
    """
    A = []
    bx = []
    by = []
    print("Point pairs:", point_pairs)
    for (dx, dy), (sx, sy) in point_pairs.items():
        A.append([dx, dy, 1])
        bx.append(sx)
        by.append(sy)
    A = np.array(A)
    bx = np.array(bx)
    by = np.array(by)
    params_x, _, _, _ = np.linalg.lstsq(A, bx, rcond=None)
    params_y, _, _, _ = np.linalg.lstsq(A, by, rcond=None)
    affine = np.array(
        [
            [params_x[0], params_x[1], params_x[2]],
            [params_y[0], params_y[1], params_y[2]],
            [0, 0, 1],
        ]
    )
    return affine


class AutomaticCalibration:
    def __init__(
        self,
        core: CMMCorePlus,
        debug: bool = False,
    ) -> None:
        self._core = core
        self.debug = debug
        self.progress = 0
        self.initial_position: Optional[Tuple[float, float]] = None
        self.reference_image: Optional[np.ndarray] = None
        self._safe_travel_radius = 10000

    def snap_image_at(self, x: float, y: float) -> np.ndarray:
        """Move the stage to (x, y), wait for settling, and then capture an image."""
        initial_pos = self.initial_position
        # Example safety check (adjust the threshold as needed)
        if np.hypot(initial_pos[0] - x, initial_pos[1] - y) > self._safe_travel_radius:
            raise CalibrationFailedException("Stage safety limit reached.")
        self._core.setXYPosition(x, y)
        self._core.waitForSystem()
        img = self._core.snap()
        QApplication.processEvents()
        return img

    def smallest_power_of_2_leq(self, x: int) -> int:
        """Return the largest power of 2 that is less than or equal to x."""
        power = 1
        while power * 2 <= x:
            power *= 2
        return power

    def run_search(
        self, dxi: float, dyi: float, initial_disp: Tuple[float, float]
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Incrementally moves the stage and measures the image displacement.
        Returns a tuple: (measured image displacement, stage position).
        """
        dx = dxi
        dy = dyi
        disp = np.array(initial_disp)
        # Loop (up to 25 iterations) doubling the displacement until a threshold is met.
        for i in range(25):
            if np.abs(2 * disp[0]) > 100 or np.abs(2 * disp[1]) > 100:
                break
            dx *= 2
            dy *= 2
            disp *= 2
            # Estimate expected stage position (here we simply add the dx,dy to the initial position)
            expected_x = self.initial_position[0] + dx
            expected_y = self.initial_position[1] + dy
            img = self.snap_image_at(expected_x, expected_y)
            # h, w = img.shape
            # # Extract a central crop adjusted by the current displacement
            # side = min(w, h) // 4
            # x0 = w // 2 - side // 2 - int(disp[0])
            # y0 = h // 2 - side // 2 - int(disp[1])
            # found_image = get_subimage(img, x0, y0, side, side)
            # found_image = subtract_minimum(found_image)
            # Measure displacement relative to the reference image
            d_change = measure_displacement(self.reference_image, img, self.debug)
            disp = disp + np.array(d_change)
            self.progress += 1
            print("Progress:", self.progress)
        stage_pos = self._core.getXYPosition()
        return (tuple(disp), stage_pos)

    def measure_corner(
        self, first_approx: np.ndarray, corner: Tuple[int, int]
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Measures the displacement at a corner point. The corner is given relative to the image center.
        """
        # Convert corner to homogeneous coordinates and transform by the first approximation
        corner_homog = np.array([corner[0], corner[1], 1])
        expected_stage = first_approx @ corner_homog
        expected_stage = expected_stage[:2]
        img = self.snap_image_at(expected_stage[0], expected_stage[1])
        # h, w = img.shape
        # side = min(w, h) // 4
        # x0 = w // 2 - side // 2 - corner[0]
        # y0 = h // 2 - side // 2 - corner[1]
        # found_image = get_subimage(img, x0, y0, side, side)
        # found_image = subtract_minimum(found_image)
        d_change = measure_displacement(self.reference_image, img, self.debug)
        measured_disp = (corner[0] + d_change[0], corner[1] + d_change[1])
        stage_pos = self._core.getXYPosition()
        self.progress += 1
        return measured_disp, stage_pos

    def get_first_approx(self) -> np.ndarray:
        """
        First approximation of the affine transform based on two searches:
          one along x and one along y.
        """
        self.initial_position = self._core.getXYPosition()
        base_image = self.snap_image_at(
            self.initial_position[0], self.initial_position[1]
        )
        # h, w = base_image.shape
        # side_w = self.smallest_power_of_2_leq(w // 4)
        # side_h = self.smallest_power_of_2_leq(h // 4)
        # side = min(side_w, side_h)
        self.reference_image = base_image
        # self.reference_image = get_subimage(
        # base_image, w // 2 - side // 2, h // 2 - side // 2, side, side
        # )
        self.reference_image = subtract_minimum(self.reference_image)
        point_pairs: Dict[Tuple[float, float], Tuple[float, float]] = {}
        point_pairs[(0.0, 0.0)] = self.initial_position
        # Run search along x
        disp_x, stage_pos_x = self.run_search(0.1, 0.0, (0.0, 0.0))
        point_pairs[disp_x] = stage_pos_x
        # Optionally, re-acquire the reference image
        # self.reference_image = get_subimage(
        #     base_image, w // 2 - side // 2, h // 2 - side // 2, side, side
        # )
        # self.reference_image = subtract_minimum(self.reference_image)
        # Run search along y
        disp_y, stage_pos_y = self.run_search(0.0, 0.1, (0.0, 0.0))
        point_pairs[disp_y] = stage_pos_y
        affine = generate_affine_transform(point_pairs)
        if self.debug:
            print("First approximate affine transform:")
            print(affine)
        return affine

    def get_second_approx(self, first_approx: np.ndarray) -> np.ndarray:
        """
        Second approximation by measuring the displacement at several corners.
        """
        # Use some arbitrary offset from the image center (this value may be tuned)
        offset = 50
        point_pairs: Dict[Tuple[float, float], Tuple[float, float]] = {}
        for corner in [
            (-offset, -offset),
            (-offset, offset),
            (offset, offset),
            (offset, -offset),
        ]:
            measured_disp, stage_pos = self.measure_corner(first_approx, corner)
            point_pairs[measured_disp] = stage_pos
        affine = generate_affine_transform(point_pairs)
        if self.debug:
            print("Second approximate affine transform:")
            print(affine)
        return affine

    def run_calibration(self) -> np.ndarray:
        """
        Runs the calibration process and returns the computed affine transform.
        """
        first_approx = self.get_first_approx()
        self.progress = 20  # example progress update
        second_approx = self.get_second_approx(first_approx)
        # Reset the stage to its original position
        self._core.setXYPosition(self.initial_position[0], self.initial_position[1])
        return second_approx

    def run(self) -> None:
        """Entry point for the calibration process."""
        try:
            affine_transform = self.run_calibration()
            print("Calibration successful. Affine transform:")
            print(affine_transform)
        except CalibrationFailedException as e:
            print(f"Calibration failed: {e}")


# --- Example stubs for StageController and camera function ---


def camera_capture() -> np.ndarray:
    """
    Stub camera function.
    In a real application, this should capture an image from the camera.
    Here we return a synthetic 512x512 image.
    """
    img = np.random.rand(512, 512).astype(np.float32) * 255
    return img.astype(np.uint8)


# --- Example usage ---

if __name__ == "__main__":
    # Create an instance in simulation mode with debug info off.
    from qtpy.QtWidgets import QApplication, QPushButton

    from pymmcore_widgets import ImagePreview

    app = QApplication([])
    core = CMMCorePlus()
    core.loadSystemConfiguration(r"c:\Users\Admin\dev\min.cfg")
    core.setROI(0, 0, 512, 512)
    calib = AutomaticCalibration(core=core, debug=True)

    preview = ImagePreview(mmcore=core)
    preview.show()
    run_btn = QPushButton("Run Calibration")
    run_btn.show()
    run_btn.clicked.connect(calib.run)

    app.exec()


# # Example usage:
# if __name__ == "__main__":
#     # Create a test image and a shifted version.
#     img = np.zeros((256, 256), dtype=np.float32)
#     img[100:150, 100:150] = 1.0  # a simple square feature
#     shift_true = (5.3, -3.7)  # (dx, dy): right and up shifts
#     # To simulate a shift, we roll the array (wrap-around).
#     img2 = np.roll(img, int(round(shift_true[1])), axis=0)
#     img2 = np.roll(img2, int(round(shift_true[0])), axis=1)

#     (dx, dy), peak = phase_correlate(img, img2)
#     print(f"Estimated shift: dx={dx:.2f}, dy={dy:.2f} (peak: {peak:.4f})")
