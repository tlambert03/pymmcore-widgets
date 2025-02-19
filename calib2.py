from functools import partial
from typing import Callable, Optional

import numpy as np
from pymmcore_plus import CMMCorePlus
from rich import print


def phase_correlate(
    img1: np.ndarray, img2: np.ndarray, eps: float = 1e-10
) -> tuple[tuple[float, float], float]:
    """
    Estimates the translation shift between two images using phase correlation.
    Returns a tuple ((shift_x, shift_y), peak_value).
    """
    # Compute FFTs of the two images.
    F1 = np.fft.fft2(img1)
    F2 = np.fft.fft2(img2)
    # Compute normalized cross-power spectrum.
    R = F1 * np.conjugate(F2)
    R /= np.abs(R) + eps
    # Inverse FFT to get correlation; shift the zero-frequency component to center.
    corr = np.fft.ifft2(R)
    corr = np.fft.fftshift(corr)
    corr_abs = np.abs(corr)

    # Find the peak location.
    peak_idx = np.unravel_index(np.argmax(corr_abs), corr.shape)
    center = np.array(corr.shape) // 2
    shift_y = peak_idx[0] - center[0]
    shift_x = peak_idx[1] - center[1]

    # Subpixel refinement via a simple parabolic fit.
    def parabolic_subpixel(c: np.ndarray, peak: tuple[int, int]) -> tuple[float, float]:
        py, px = peak
        sub_y, sub_x = 0.0, 0.0
        if 0 < px < c.shape[1] - 1:
            left = c[py, px - 1]
            center_val = c[py, px]
            right = c[py, px + 1]
            denom = 2 * center_val - left - right
            if denom != 0:
                sub_x = (left - right) / (2 * denom)
        if 0 < py < c.shape[0] - 1:
            top = c[py - 1, px]
            center_val = c[py, px]
            bottom = c[py + 1, px]
            denom = 2 * center_val - top - bottom
            if denom != 0:
                sub_y = (top - bottom) / (2 * denom)
        return sub_y, sub_x

    sub_y, sub_x = parabolic_subpixel(corr_abs, peak_idx)
    shift_x += sub_x
    shift_y += sub_y
    return (shift_x, shift_y), corr_abs[peak_idx]


class CameraCalibrator:
    def __init__(
        self,
        camera: Callable[[], np.ndarray],
        stage: "StageController",
        roi: Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        self.camera = camera
        self.stage = stage
        self.roi = roi

    def capture_roi(self) -> np.ndarray:
        """Capture an image and return the ROI (or the full image if no ROI is provided)."""
        img = self.camera().astype(np.float32)
        if self.roi is not None:
            x, y, w, h = self.roi
            img = img[y : y + h, x : x + w]
        return img

    def calibrate(self, moves: list[tuple[float, float]]) -> np.ndarray:
        # Capture reference image at initial stage position.
        initial_stage = self.stage.get_position()  # (sx0, sy0)
        ref = self.capture_roi()

        pixel_displacements = []
        stage_displacements = []

        # For each known stage move, capture a new image and measure pixel displacement.
        for dx_stage, dy_stage in moves:
            new_stage = (initial_stage[0] + dx_stage, initial_stage[1] + dy_stage)
            self.stage.move_to(*new_stage)
            # (Optionally, wait a bit for the stage to settle.)
            img = self.capture_roi()
            (dx_pix, dy_pix), _ = phase_correlate(ref, img)
            pixel_displacements.append([dx_pix, dy_pix])
            stage_displacements.append([dx_stage, dy_stage])
            print(
                "stage move:",
                (dx_stage, dy_stage),
                "---> pixel displacement:",
                (dx_pix, dy_pix),
            )

        pixel_displacements = np.array(pixel_displacements)  # shape (N, 2)
        stage_displacements = np.array(stage_displacements)  # shape (N, 2)

        # Solve for the linear transformation A (a 2x2 matrix) that maps pixel shifts to stage shifts.
        # That is, we want: stage_disp = A @ pixel_disp.
        A, _, _, _ = np.linalg.lstsq(
            pixel_displacements, stage_displacements, rcond=None
        )  # A is 2×2

        # Construct the full affine transform.
        # The translation component is the initial stage position, which corresponds to the ROI center.
        affine = np.eye(3, dtype=np.float32)
        affine[0, 0:2] = A[0]
        affine[1, 0:2] = A[1]
        # affine[0, 2] = initial_stage[0]
        # affine[1, 2] = initial_stage[1]

        print("Calibration successful. Affine transform:")
        print(affine)

        # extract pixel size and rotation, assuming no skew

        pixel_size = np.linalg.norm(affine[0, 0:2])
        rotation = np.arctan2(affine[1, 0], affine[0, 0])
        print("Pixel size:", pixel_size)
        print("Rotation (degrees):", np.rad2deg(rotation))
        return affine


# Example stub implementations for demonstration:


class StageController:
    def __init__(self, core: CMMCorePlus) -> None:
        self.core = core

    def get_position(self) -> tuple[float, float]:
        return self.core.getXYPosition()

    def move_to(self, x: float, y: float) -> None:
        self.core.setXYPosition(x, y)
        self.core.waitForSystem()


np.set_printoptions(suppress=True, precision=6)
if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication, QPushButton

    from pymmcore_widgets import ImagePreview

    app = QApplication([])

    core = CMMCorePlus()
    core.loadSystemConfiguration(r"c:\Users\Admin\dev\min.cfg")
    stage = StageController(core)
    # Optionally, define an ROI. For example, use the central 256x256 region.
    roi = (128, 128, 256, 256)

    print(core.getXYPosition())

    def snap():
        img = core.snap()
        QApplication.processEvents()
        return img

    calibrator = CameraCalibrator(snap, stage=stage, roi=roi)

    # Define known stage moves in stage units.
    max_distance = 50
    num_steps = 5
    x_moves = [(i, 0) for i in range(0, max_distance, num_steps)]
    y_moves = [(0, i) for i in range(0, max_distance, num_steps)]
    xy_moves = [(i, i) for i in range(0, max_distance, num_steps)]
    moves = x_moves + y_moves + xy_moves

    preview = ImagePreview(mmcore=core)
    preview.show()
    run_btn = QPushButton("Run Calibration")
    run_btn.show()
    run_btn.clicked.connect(partial(calibrator.calibrate, moves))

    app.exec()
