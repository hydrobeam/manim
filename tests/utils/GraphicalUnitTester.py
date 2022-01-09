import logging
import os

import numpy as np

from manim import config, tempconfig
from manim.renderer.opengl_renderer import OpenGLRenderer


class GraphicalUnitTester:
    """Class used to test the animations.

    Parameters
    ----------
    scene_class : :class:`~.Scene`
        The scene to be tested
    config_scene : :class:`dict`
        The configuration of the scene
    module_tested : :class:`str`
        The name of the module tested. i.e if we are testing functions of creation.py, the module will be "creation"

    Attributes
    -----------
    path_tests_medias_cache : : class:`str`
        Path to 'media' folder generated by manim. This folder contains cached data used by some tests.
    path_control_data : :class:`str`
        Path to the data used for the tests (i.e the pre-rendered frames).
    scene : :class:`Scene`
        The scene tested
    """

    def __init__(self, scene_class, module_tested, tmpdir, rgb_atol=0):
        # Disable the the logs, (--quiet is broken) TODO
        logging.disable(logging.CRITICAL)
        tests_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.path_tests_medias_cache = os.path.join(
            tmpdir,
            "test_graphical_units",
            "tests_cache",
            module_tested,
            scene_class.__name__,
        )
        self.path_control_data = os.path.join(
            tests_directory,
            "control_data",
            "graphical_units_data",
            module_tested,
        )
        self.rgb_atol = rgb_atol

        # IMPORTANT NOTE : The graphical units tests don't use for now any
        # custom manim.cfg, since it is impossible to manually select a
        # manim.cfg from a python file. (see issue #293)
        config["text_dir"] = os.path.join(self.path_tests_medias_cache, "Text")
        config["tex_dir"] = os.path.join(self.path_tests_medias_cache, "Tex")

        config["disable_caching"] = True
        config["quality"] = "low_quality"

        for dir_temp in [
            self.path_tests_medias_cache,
            config["text_dir"],
            config["tex_dir"],
        ]:
            os.makedirs(dir_temp)

        with tempconfig({"dry_run": True}):
            self.scene = scene_class(renderer=OpenGLRenderer())
            self.scene.render()

    def _load_data(self):
        """Load the np.array of the last frame of a pre-rendered scene. If not found, throw FileNotFoundError.

        Returns
        -------
        :class:`numpy.array`
            The pre-rendered frame.
        """
        frame_data_path = os.path.join(
            os.path.join(self.path_control_data, f"{self.scene}.npz"),
        )
        return np.load(frame_data_path)["frame_data"]

    def _show_diff_helper(self, frame_data, expected_frame_data):
        """Will visually display with matplotlib differences between frame generated and the one expected."""
        import matplotlib.gridspec as gridspec  # type: ignore
        import matplotlib.pyplot as plt

        gs = gridspec.GridSpec(2, 2)
        fig = plt.figure()
        fig.suptitle(f"Test for {str(self.scene).replace('Test', '')}", fontsize=16)

        ax = fig.add_subplot(gs[0, 0])
        ax.imshow(frame_data)
        ax.set_title("Generated :")

        ax = fig.add_subplot(gs[0, 1])
        ax.imshow(expected_frame_data)
        ax.set_title("Expected :")

        ax = fig.add_subplot(gs[1, :])
        diff_im = expected_frame_data.copy()
        diff_im = np.where(
            frame_data != np.array([0, 0, 0, 255]),
            np.array([0, 255, 0, 255], dtype="uint8"),
            np.array([0, 0, 0, 255], dtype="uint8"),
        )  # Set any non-black pixels to green
        np.putmask(
            diff_im,
            expected_frame_data != frame_data,
            np.array([255, 0, 0, 255], dtype="uint8"),
        )  # Set any different pixels to red
        ax.imshow(diff_im, interpolation="nearest")
        ax.set_title("Differences summary : (green = same, red = different)")

        plt.show()
        plt.savefig(f"{self.scene}.png")

    def test(self, show_diff=False):
        """Compare pre-rendered frame to the frame rendered during the test."""
        frame_data = self.scene.renderer.get_frame()
        expected_frame_data = self._load_data()

        assert frame_data.shape == expected_frame_data.shape, (
            "The frames have different shape:"
            + f"\nexpected_frame_data.shape = {expected_frame_data.shape}"
            + f"\nframe_data.shape = {frame_data.shape}"
        )

        mismatches = np.logical_not(
            np.isclose(frame_data, expected_frame_data, atol=self.rgb_atol, rtol=0),
        )
        if mismatches.any():
            incorrect_indices = np.argwhere(mismatches)
            first_incorrect_index = incorrect_indices[0][:2]
            first_incorrect_point = frame_data[tuple(first_incorrect_index)]
            expected_point = expected_frame_data[tuple(first_incorrect_index)]
            if show_diff:
                self._show_diff_helper(frame_data, expected_frame_data)
            assert not mismatches.any(), (
                f"The frames don't match. {str(self.scene).replace('Test', '')} has been modified."
                + "\nPlease ignore if it was intended."
                + f"\nFirst unmatched index is at {first_incorrect_index}: {first_incorrect_point} != {expected_point}"
            )
