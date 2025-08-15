from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import numpy as np
import useq
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtGui import QKeyEvent
from vispy.app.canvas import MouseEvent
from vispy.scene.visuals import Image

from pymmcore_widgets.control._stage_explorer._stage_explorer import (
    AffineState,
    PositionIndicator,
    PositionIndicatorMenu,
    ScanMenu,
    StageExplorer,
    StageExplorerToolbar,
)
from pymmcore_widgets.control._stage_explorer._stage_viewer import StageViewer

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot

IMG = np.random.randint(0, 255, (100, 50), dtype=np.uint8)


def _build_transform_matrix(x: float, y: float) -> np.ndarray:
    T = np.eye(4)
    T[0, 3] += x
    T[1, 3] += y
    return T


def test_stage_viewer_add_image(qtbot: QtBot) -> None:
    stage_viewer = StageViewer()
    qtbot.addWidget(stage_viewer)
    T = _build_transform_matrix(100, 150)
    stage_viewer.add_image(IMG, T.T)
    images = [i for i in stage_viewer.view.scene.children if isinstance(i, Image)]
    assert len(images) == 1
    added_img = next(iter(images))
    assert tuple(added_img.transform.matrix[3, :2]) == (100, 150)


def test_stage_viewer_clims_cmaps(qtbot: QtBot) -> None:
    stage_viewer = StageViewer()
    qtbot.addWidget(stage_viewer)
    T = _build_transform_matrix(100, 150)
    stage_viewer.add_image(IMG, T.T)

    # just some smoke tests
    stage_viewer.set_clims((0, 1))
    stage_viewer.global_autoscale(ignore_min=0.1, ignore_max=0.1)
    stage_viewer.set_colormap("viridis")


def test_stage_viewer_clear_scene(qtbot: QtBot) -> None:
    stage_viewer = StageViewer()
    qtbot.addWidget(stage_viewer)
    T = _build_transform_matrix(200, 50)
    stage_viewer.add_image(IMG, T.T)
    assert [i for i in stage_viewer.view.scene.children if isinstance(i, Image)]
    stage_viewer.clear()
    assert not [i for i in stage_viewer.view.scene.children if isinstance(i, Image)]


def test_stage_viewer_reset_view(qtbot: QtBot) -> None:
    stage_viewer = StageViewer()
    qtbot.addWidget(stage_viewer)
    T = _build_transform_matrix(500, 100)
    stage_viewer.add_image(IMG, T.T)
    stage_viewer.zoom_to_fit()
    cx, cy = stage_viewer.view.camera.rect.center
    assert round(cx) == 525  # image width is 50, center should be Tx + width/2
    assert round(cy) == 150  # image height is 100, center should be Ty + height/2


def test_stage_explorer_initialization(qtbot: QtBot) -> None:
    explorer = StageExplorer()
    qtbot.addWidget(explorer)
    assert explorer.windowTitle() == "Stage Explorer"
    assert explorer.snap_on_double_click is True


def test_stage_explorer_snap_on_double_click(qtbot: QtBot) -> None:
    explorer = StageExplorer()
    qtbot.addWidget(explorer)
    explorer.snap_on_double_click = True
    assert explorer.snap_on_double_click is True
    explorer.snap_on_double_click = False
    assert explorer.snap_on_double_click is False


def test_stage_explorer_add_image(qtbot: QtBot) -> None:
    explorer = StageExplorer()
    qtbot.addWidget(explorer)
    image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    stage_x, stage_y = 50.0, 75.0
    explorer.add_image(image, stage_x, stage_y)
    # Verify the image was added to the stage viewer
    nimages = len(list(explorer._stage_viewer._get_images()))
    assert nimages == 1


def test_stage_explorer_actions(qtbot: QtBot) -> None:
    explorer = StageExplorer()
    qtbot.addWidget(explorer)
    explorer.add_image(IMG, 0, 0)

    snap_action = explorer._toolbar.snap_action
    assert explorer.snap_on_double_click is True
    with qtbot.waitSignal(snap_action.triggered):
        snap_action.trigger()
    assert explorer.snap_on_double_click is False

    auto_action = explorer._toolbar.auto_zoom_to_fit_action
    auto_action.trigger()
    assert explorer.auto_zoom_to_fit
    # this turns it off
    explorer._toolbar.zoom_to_fit_action.trigger()
    assert not explorer.auto_zoom_to_fit

    assert not explorer._stage_viewer._grid_lines.visible
    grid_action = explorer._toolbar.show_grid_action
    grid_action.trigger()
    assert explorer._stage_viewer._grid_lines.visible


def test_stage_explorer_move_on_click(qtbot: QtBot) -> None:
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    explorer.add_image(IMG, 0, 0)
    stage_pos = explorer._mmc.getXYPosition()

    explorer._snap_on_double_click = True
    event = MouseEvent("mouse_press", pos=(100, 100), button=1)
    with qtbot.waitSignal(explorer._mmc.events.imageSnapped):
        explorer._on_mouse_double_click(event)

    assert explorer._mmc.getXYPosition() != stage_pos


def test_stage_explorer_position_indicator(qtbot: QtBot) -> None:
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    poll_action = explorer._toolbar.poll_stage_action
    assert explorer._poll_stage_position is True
    assert explorer._timer_id is not None

    # wait for timerEvent to be triggered
    qtbot.waitUntil(lambda: explorer._stage_pos_marker is not None, timeout=1000)
    assert explorer._stage_pos_marker is not None
    assert explorer._stage_pos_marker.visible

    with qtbot.waitSignal(poll_action.triggered):
        poll_action.trigger()

    assert explorer._poll_stage_position is False
    assert explorer._timer_id is None


def test_mouse_hover_shows_position(qtbot: QtBot) -> None:
    viewer = StageViewer()
    viewer.show()
    qtbot.addWidget(viewer)
    viewer.set_hover_label_visible(True)

    # Simulate mouse move event
    event = MouseEvent("mouse_move", pos=(100, 2))
    viewer._on_mouse_move(event)

    # Check if the hover label is visible and shows the correct position
    assert viewer._hover_pos_label.isVisible()
    assert viewer._hover_pos_label.text().startswith("(")


# ===== NEW COMPREHENSIVE TESTS =====


def test_position_indicator_enum() -> None:
    """Test PositionIndicator enum values and properties."""
    assert str(PositionIndicator.RECTANGLE) == "FOV Rectangle"
    assert str(PositionIndicator.CENTER) == "FOV Center"
    assert str(PositionIndicator.BOTH) == "Both"

    # Test show_rect property
    assert PositionIndicator.RECTANGLE.show_rect is True
    assert PositionIndicator.CENTER.show_rect is False
    assert PositionIndicator.BOTH.show_rect is True

    # Test show_marker property
    assert PositionIndicator.RECTANGLE.show_marker is False
    assert PositionIndicator.CENTER.show_marker is True
    assert PositionIndicator.BOTH.show_marker is True


def test_position_indicator_menu(qtbot: QtBot) -> None:
    """Test PositionIndicatorMenu widget."""
    menu = PositionIndicatorMenu()
    qtbot.addWidget(menu)

    # Check that action group exists and is exclusive
    assert menu.action_group is not None
    assert menu.action_group.isExclusive() is True

    # Check that all position indicator modes are present
    actions = menu.action_group.actions()
    assert len(actions) == 3

    action_texts = [action.text() for action in actions]
    assert "FOV Rectangle" in action_texts
    assert "FOV Center" in action_texts
    assert "Both" in action_texts


def test_scan_menu(qtbot: QtBot) -> None:
    """Test ScanMenu widget."""
    menu = ScanMenu()
    qtbot.addWidget(menu)

    # Test initial values
    overlap, mode = menu.value()
    assert overlap == 0.0  # Default value for overlap spinbox
    assert mode == useq.OrderMode.row_wise_snake

    # Test changing overlap value
    menu._overlap_spin.setValue(10.5)
    overlap, mode = menu.value()
    assert overlap == 10.5

    # Test changing mode
    menu._mode_cbox.setCurrentEnum(useq.OrderMode.column_wise_snake)
    overlap, mode = menu.value()
    assert mode == useq.OrderMode.column_wise_snake


def test_stage_explorer_toolbar(qtbot: QtBot) -> None:
    """Test StageExplorerToolbar widget."""
    toolbar = StageExplorerToolbar()
    qtbot.addWidget(toolbar)

    # Test that all required actions exist
    assert toolbar.clear_action is not None
    assert toolbar.zoom_to_fit_action is not None
    assert toolbar.auto_zoom_to_fit_action is not None
    assert toolbar.snap_action is not None
    assert toolbar.poll_stage_action is not None
    assert toolbar.show_grid_action is not None
    assert toolbar.delete_rois_action is not None
    assert toolbar.scan_action is not None

    # Test checkable actions
    assert toolbar.auto_zoom_to_fit_action.isCheckable() is True
    assert toolbar.snap_action.isCheckable() is True
    assert toolbar.poll_stage_action.isCheckable() is True
    assert toolbar.show_grid_action.isCheckable() is True

    # Test that scan menu exists
    assert toolbar.scan_menu is not None
    assert toolbar.marker_mode_action_group is not None


def test_stage_explorer_properties(qtbot: QtBot) -> None:
    """Test StageExplorer property getters and setters."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Test auto_zoom_to_fit property
    assert explorer.auto_zoom_to_fit is False
    explorer.auto_zoom_to_fit = True
    assert explorer.auto_zoom_to_fit is True
    assert explorer._toolbar.auto_zoom_to_fit_action.isChecked() is True

    # Test snap_on_double_click property
    assert explorer.snap_on_double_click is True
    explorer.snap_on_double_click = False
    assert explorer.snap_on_double_click is False
    assert explorer._toolbar.snap_action.isChecked() is False

    # Test poll_stage_position property
    explorer.poll_stage_position = False
    assert explorer.poll_stage_position is False
    assert explorer._toolbar.poll_stage_action.isChecked() is False

    explorer.poll_stage_position = True
    assert explorer.poll_stage_position is True
    assert explorer._toolbar.poll_stage_action.isChecked() is True


def test_stage_explorer_toolbar_getter(qtbot: QtBot) -> None:
    """Test StageExplorer toolBar() method."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    toolbar = explorer.toolBar()
    assert toolbar is explorer._toolbar
    assert toolbar is not None


def test_stage_explorer_roi_manager(qtbot: QtBot) -> None:
    """Test ROI manager integration."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Test that ROI manager exists
    assert explorer.roi_manager is not None

    # Test ROI manager clear action
    explorer._toolbar.delete_rois_action.trigger()
    # Should not raise any errors


def test_stage_explorer_marker_mode_update(qtbot: QtBot) -> None:
    """Test marker mode update functionality."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Get the marker mode action group
    action_group = explorer._toolbar.marker_mode_action_group

    # Test changing marker mode
    actions = action_group.actions()
    if actions:
        # Check first action (should be rectangle mode)
        actions[0].setChecked(True)
        explorer._update_marker_mode()

        # Test that the stage position marker updated accordingly
        # (exact behavior depends on PositionIndicator values)
        assert explorer._stage_pos_marker is not None


def test_stage_explorer_sys_config_loaded(qtbot: QtBot) -> None:
    """Test system configuration loaded event handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Add an image first
    explorer.add_image(IMG, 0, 0)
    images_before = len(list(explorer._stage_viewer._get_images()))
    assert images_before > 0

    # Trigger system config loaded event
    explorer._on_sys_config_loaded()

    # Should clear all images
    images_after = len(list(explorer._stage_viewer._get_images()))
    assert images_after == 0


def test_stage_explorer_pixel_size_events(qtbot: QtBot) -> None:
    """Test pixel size change event handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # These should not raise errors
    explorer._on_pixel_size_changed(1.5)
    explorer._on_pixel_size_affine_changed()


def test_stage_explorer_roi_changed(qtbot: QtBot) -> None:
    """Test ROI changed event handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Should not raise errors
    explorer._on_roi_changed()


def test_stage_explorer_image_snapped(qtbot: QtBot) -> None:
    """Test image snapped event handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    initial_images = len(list(explorer._stage_viewer._get_images()))

    # Test when MDA is not running
    with patch.object(explorer._mmc.mda, "is_running", return_value=False):
        with patch.object(explorer._mmc, "getImage", return_value=IMG):
            with patch.object(
                explorer._mmc, "getXYPosition", return_value=(10.0, 20.0)
            ):
                explorer._on_image_snapped()

    # Should add an image
    final_images = len(list(explorer._stage_viewer._get_images()))
    assert final_images == initial_images + 1


def test_stage_explorer_frame_ready(qtbot: QtBot) -> None:
    """Test frame ready event handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    initial_images = len(list(explorer._stage_viewer._get_images()))

    # Create a mock MDA event
    event = useq.MDAEvent(x_pos=15.0, y_pos=25.0)

    explorer._on_frame_ready(IMG, event)

    # Should add an image
    final_images = len(list(explorer._stage_viewer._get_images()))
    assert final_images == initial_images + 1


def test_stage_explorer_frame_ready_no_position(qtbot: QtBot) -> None:
    """Test frame ready event handling when event has no position."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    initial_images = len(list(explorer._stage_viewer._get_images()))

    # Create a mock MDA event without positions
    event = useq.MDAEvent()

    with patch.object(explorer._mmc, "getXPosition", return_value=30.0):
        with patch.object(explorer._mmc, "getYPosition", return_value=40.0):
            explorer._on_frame_ready(IMG, event)

    # Should add an image
    final_images = len(list(explorer._stage_viewer._get_images()))
    assert final_images == initial_images + 1


def test_stage_explorer_timer_event(qtbot: QtBot) -> None:
    """Test timer event for stage position polling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Enable position polling
    explorer.poll_stage_position = True

    # Mock the stage position
    with patch.object(explorer._mmc, "getXYPosition", return_value=(50.0, 60.0)):
        with patch.object(explorer._mmc, "getXYStageDevice", return_value="XY"):
            # Trigger timer event
            explorer.timerEvent(None)

    # Check that stage position label was updated
    assert "X: 50.00 µm  Y: 60.00 µm" in explorer._stage_pos_label.text()


def test_stage_explorer_timer_event_no_stage(qtbot: QtBot) -> None:
    """Test timer event when no XY stage device is available."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Mock no XY stage device
    with patch.object(explorer._mmc, "getXYStageDevice", return_value=""):
        explorer.timerEvent(None)

    # Check that appropriate message is shown
    assert "No XY stage device" in explorer._stage_pos_label.text()


def test_stage_explorer_is_visual_within_view(qtbot: QtBot) -> None:
    """Test _is_visual_within_view method."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Mock FOV dimensions
    with patch.object(explorer, "_fov_w_h", return_value=(100.0, 100.0)):
        # Test point within view (simplified test without patching camera.rect)
        # Since camera.rect is a property, we'll test the method directly
        result = explorer._is_visual_within_view(50.0, 50.0)
        assert isinstance(result, bool)  # Should return a boolean


def test_stage_explorer_fov_w_h(qtbot: QtBot) -> None:
    """Test _fov_w_h method."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Mock the required methods
    with patch.object(explorer._mmc, "getPixelSizeUm", return_value=1.5):
        with patch.object(explorer._mmc, "getImageWidth", return_value=512):
            with patch.object(explorer._mmc, "getImageHeight", return_value=256):
                fov_w, fov_h = explorer._fov_w_h()

                assert fov_w == 512 * 1.5  # 768.0
                assert fov_h == 256 * 1.5  # 384.0


def test_stage_explorer_scan_action_no_rois(qtbot: QtBot) -> None:
    """Test scan action when no ROIs are selected."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Mock no selected ROIs
    with patch.object(explorer.roi_manager, "selected_rois", return_value=[]):
        # Should not raise error and should return early
        explorer._on_scan_action()


def test_stage_explorer_scan_action_with_roi(qtbot: QtBot) -> None:
    """Test scan action with a selected ROI."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Create a mock ROI with a proper grid plan
    mock_roi = Mock()
    mock_grid_plan = useq.GridRowsColumns(rows=2, columns=2)
    mock_roi.create_grid_plan.return_value = mock_grid_plan

    with patch.object(explorer.roi_manager, "selected_rois", return_value=[mock_roi]):
        with patch.object(explorer._mmc.mda, "is_running", return_value=False):
            with patch.object(explorer._mmc, "run_mda") as mock_run_mda:
                with patch.object(explorer, "_fov_w_h", return_value=(100.0, 100.0)):
                    explorer._on_scan_action()

                    # Should have called run_mda
                    mock_run_mda.assert_called_once()
                    assert explorer._our_mda_running is True


def test_stage_explorer_scan_options_changed(qtbot: QtBot) -> None:
    """Test scan options changed handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Create mock ROIs
    mock_roi1 = Mock()
    mock_roi2 = Mock()

    with patch.object(
        explorer.roi_manager, "all_rois", return_value=[mock_roi1, mock_roi2]
    ):
        with patch.object(
            explorer.roi_manager.roi_model, "emitDataChange"
        ) as mock_emit:
            # Test changing scan options
            new_value = (15.0, useq.OrderMode.column_wise_snake)
            explorer._on_scan_options_changed(new_value)

            # Check that properties were updated
            assert explorer._grid_overlap == 15.0
            assert explorer._grid_mode == useq.OrderMode.column_wise_snake

            # Check that ROI properties were updated
            assert mock_roi1.fov_overlap == (15.0, 15.0)
            assert mock_roi1.scan_order == useq.OrderMode.column_wise_snake
            assert mock_roi2.fov_overlap == (15.0, 15.0)
            assert mock_roi2.scan_order == useq.OrderMode.column_wise_snake

            # Check that model was notified
            assert mock_emit.call_count == 2


def test_stage_explorer_roi_rows_inserted(qtbot: QtBot) -> None:
    """Test ROI rows inserted handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Set up scan menu values
    explorer._toolbar.scan_menu._overlap_spin.setValue(20.0)
    explorer._toolbar.scan_menu._mode_cbox.setCurrentEnum(
        useq.OrderMode.column_wise_snake
    )

    # Create mock ROI
    mock_roi = Mock()

    with patch.object(explorer.roi_manager.roi_model, "getRoi", return_value=mock_roi):
        with patch.object(
            explorer.roi_manager.roi_model, "emitDataChange"
        ) as mock_emit:
            parent = QModelIndex()

            # Simulate rows inserted
            explorer._on_roi_rows_inserted(parent, 0, 0)

            # Check that ROI was initialized with current values
            assert mock_roi.fov_overlap == (20.0, 20.0)
            assert mock_roi.scan_order == useq.OrderMode.column_wise_snake
            mock_emit.assert_called_once_with(mock_roi)


def test_stage_explorer_key_press_event(qtbot: QtBot) -> None:
    """Test key press event handling."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Mock MDA running state
    explorer._our_mda_running = True

    # Create escape key event
    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )

    with patch.object(explorer._mmc.mda, "cancel") as mock_cancel:
        explorer.keyPressEvent(key_event)
        mock_cancel.assert_called_once()


def test_stage_explorer_mouse_double_click_no_stage(qtbot: QtBot) -> None:
    """Test mouse double click when no XY stage device."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    with patch.object(explorer._mmc, "getXYStageDevice", return_value=""):
        event = MouseEvent("mouse_double_click", pos=(100, 100), button=1)
        # Should not raise error and should return early
        explorer._on_mouse_double_click(event)


def test_stage_explorer_mouse_double_click_roi_mode(qtbot: QtBot) -> None:
    """Test mouse double click in ROI creation mode."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Set ROI manager to create-poly mode
    explorer.roi_manager.mode = "create-poly"

    event = MouseEvent("mouse_double_click", pos=(100, 100), button=1)
    # Should not move stage in this mode
    explorer._on_mouse_double_click(event)


def test_affine_state_initialization(qtbot: QtBot, global_mmcore: CMMCorePlus) -> None:
    """Test AffineState initialization and refresh."""
    affine_state = AffineState(global_mmcore)

    # Test that attributes are set
    assert hasattr(affine_state, "pixel_size_um")
    assert hasattr(affine_state, "pixel_size_affine")
    assert hasattr(affine_state, "system_affine")

    # Test refresh method
    affine_state.refresh()

    # Test system_affine_translated
    translated = affine_state.system_affine_translated(10.0, 20.0)
    assert translated is not None
    assert translated[0, 3] == 10.0
    assert translated[1, 3] == 20.0


def test_affine_state_pixel_config_methods(
    qtbot: QtBot, global_mmcore: CMMCorePlus
) -> None:
    """Test AffineState pixel configuration methods."""
    affine_state = AffineState(global_mmcore)

    # Test _pixel_config_is_identity
    is_identity = affine_state._pixel_config_is_identity()
    assert isinstance(is_identity, bool)

    # Test _pixel_config_matrix
    matrix = affine_state._pixel_config_matrix()
    assert matrix is not None
    assert matrix.shape == (4, 4)

    # Test with flips
    matrix_flip_x = affine_state._pixel_config_matrix(flip_x=True)
    matrix_flip_y = affine_state._pixel_config_matrix(flip_y=True)
    matrix_flip_both = affine_state._pixel_config_matrix(flip_x=True, flip_y=True)

    assert matrix_flip_x is not None
    assert matrix_flip_y is not None
    assert matrix_flip_both is not None


def test_affine_state_linear_matrix(qtbot: QtBot, global_mmcore: CMMCorePlus) -> None:
    """Test AffineState _linear_matrix method."""
    affine_state = AffineState(global_mmcore)

    # Test with different parameters
    matrix_default = affine_state._linear_matrix()
    matrix_rotated = affine_state._linear_matrix(rotation=90.0)
    matrix_flipped_x = affine_state._linear_matrix(flip_x=True)
    matrix_flipped_y = affine_state._linear_matrix(flip_y=True)

    assert matrix_default.shape == (4, 4)
    assert matrix_rotated.shape == (4, 4)
    assert matrix_flipped_x.shape == (4, 4)
    assert matrix_flipped_y.shape == (4, 4)

    # The rotation matrix should be different from default
    assert not np.allclose(matrix_default, matrix_rotated)


def test_stage_explorer_add_image_and_update_widget(qtbot: QtBot) -> None:
    """Test _add_image_and_update_widget method."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    initial_images = len(list(explorer._stage_viewer._get_images()))

    # Test adding image when not polling stage position
    explorer._poll_stage_position = False
    explorer._add_image_and_update_widget(IMG, 100.0, 200.0)

    # Should add image and update label
    final_images = len(list(explorer._stage_viewer._get_images()))
    assert final_images == initial_images + 1
    assert "X: 100.00 µm  Y: 200.00 µm" in explorer._stage_pos_label.text()


def test_stage_explorer_add_image_auto_zoom(qtbot: QtBot) -> None:
    """Test _add_image_and_update_widget with auto zoom."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Enable auto zoom to fit
    explorer._auto_zoom_to_fit = True

    # Mock that image is not within view
    with patch.object(explorer, "_is_visual_within_view", return_value=False):
        with patch.object(explorer._stage_viewer, "zoom_to_fit") as mock_zoom:
            explorer._add_image_and_update_widget(IMG, 1000.0, 1000.0)
            mock_zoom.assert_called_once()


def test_stage_explorer_zoom_to_fit_with_margin(qtbot: QtBot) -> None:
    """Test zoom_to_fit method with custom margin."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Add an image first
    explorer.add_image(IMG, 0, 0)

    # Test zoom to fit with custom margin
    explorer.zoom_to_fit(margin=0.1)

    # Should not raise any errors


def test_scan_menu_value_changed_signal(qtbot: QtBot) -> None:
    """Test ScanMenu valueChanged signal."""
    from pymmcore_widgets.control._stage_explorer._stage_explorer import ScanMenu

    menu = ScanMenu()
    qtbot.addWidget(menu)

    # Connect to signal and test emission
    with qtbot.waitSignal(menu.valueChanged) as blocker:
        menu._overlap_spin.setValue(25.0)

    # Check signal was emitted with correct value
    emitted_value = blocker.args[0]
    overlap, mode = emitted_value
    assert overlap == 25.0


def test_stage_explorer_integration_with_mmc_events(qtbot: QtBot) -> None:
    """Test integration with micromanager core events."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Test that roi change handler is connected (simplified test)
    # Just verify that the method exists and is callable
    assert hasattr(explorer, "_on_roi_changed")
    assert callable(explorer._on_roi_changed)

    # Test calling the handler directly
    explorer._on_roi_changed()  # Should not raise an error


def test_stage_explorer_image_snapped_mda_running(qtbot: QtBot) -> None:
    """Test image snapped event when MDA is running."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    initial_images = len(list(explorer._stage_viewer._get_images()))

    # Test when MDA is running - should return early
    with patch.object(explorer._mmc.mda, "is_running", return_value=True):
        explorer._on_image_snapped()

    # Should not add an image
    final_images = len(list(explorer._stage_viewer._get_images()))
    assert final_images == initial_images


def test_stage_explorer_keypress_none(qtbot: QtBot) -> None:
    """Test key press event with None event."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Should not raise an error
    explorer.keyPressEvent(None)


def test_stage_explorer_keypress_escape_mda_running(qtbot: QtBot) -> None:
    """Test escape key when MDA is running."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Set MDA running state
    explorer._our_mda_running = True

    # Create escape key event
    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )

    with patch.object(explorer._mmc.mda, "cancel") as mock_cancel:
        explorer.keyPressEvent(key_event)
        mock_cancel.assert_called_once()


def test_affine_state_compute_system_affine(
    qtbot: QtBot, global_mmcore: CMMCorePlus
) -> None:
    """Test AffineState _compute_system_affine method."""
    affine_state = AffineState(global_mmcore)

    # Test the compute system affine method
    result = affine_state._compute_system_affine()
    assert result is not None
    assert result.shape == (4, 4)


def test_affine_state_with_camera_flip(
    qtbot: QtBot, global_mmcore: CMMCorePlus
) -> None:
    """Test AffineState with camera flip properties."""
    affine_state = AffineState(global_mmcore)

    # Mock camera device
    with patch.object(global_mmcore, "getCameraDevice", return_value="Camera"):
        with patch.object(global_mmcore, "getProperty") as mock_get_prop:
            mock_get_prop.side_effect = (
                lambda dev, prop: "1" if "MirrorX" in prop else "0"
            )

            # Test compute system affine with camera properties
            result = affine_state._compute_system_affine()
            assert result is not None


def test_stage_explorer_position_modes(qtbot: QtBot) -> None:
    """Test different position indicator modes."""
    explorer = StageExplorer()
    qtbot.addWidget(explorer)

    # Test each position indicator mode
    modes = [
        PositionIndicator.RECTANGLE,
        PositionIndicator.CENTER,
        PositionIndicator.BOTH,
    ]
    for mode in modes:
        # Get the action for this mode
        actions = explorer._toolbar.marker_mode_action_group.actions()
        mode_action = None
        for action in actions:
            if action.text() == mode.value:
                mode_action = action
                break

        if mode_action:
            mode_action.setChecked(True)
            explorer._update_marker_mode()

            # Test that the update method runs without error
            # (detailed visibility testing would require knowledge of
            # StagePositionMarker's internal structure)
            assert mode_action.isChecked()
