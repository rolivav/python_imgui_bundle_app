"""Application entry point."""

from __future__ import annotations

import traceback

from imgui_bundle import immapp

from .panels import Panel, create_panels


def main() -> None:
    """Run the application."""
    panels = create_panels()
    # A Python exception raised inside the GUI callback crosses the C++ boundary
    # and aborts the process, so panels are drawn through a guard: the traceback
    # is printed and the faulty panel is disabled instead of killing the app.
    failed: list[Panel] = []

    def draw_panels() -> None:
        for panel in panels:
            if panel in failed:
                continue
            try:
                panel.draw()
            except Exception:  # noqa: BLE001 - last resort guard
                failed.append(panel)
                traceback.print_exc()

    runner_params = immapp.RunnerParams()
    runner_params.app_window_params.window_title = "Cat GIFs"
    runner_params.app_window_params.window_geometry.size = (900, 700)
    runner_params.callbacks.show_gui = draw_panels
    # Animated GIFs must keep rendering even when the mouse does not move.
    runner_params.fps_idling.enable_idling = False

    immapp.run(runner_params)


if __name__ == "__main__":
    main()
