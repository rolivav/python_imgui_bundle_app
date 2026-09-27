"""Application entry point."""

from __future__ import annotations

import traceback

from imgui_bundle import hello_imgui, immapp

from .panels import Panel, create_panels

#: Name of the dock space provided by hello_imgui when a full screen dock space
#: is requested. Every panel starts there, so a single panel fills the whole
#: window; adding panels makes them share it (as tabs by default).
MAIN_DOCK_SPACE = "MainDockSpace"


def main() -> None:
    """Run the application."""
    panels = create_panels()
    # A Python exception raised inside the GUI callback crosses the C++ boundary
    # and aborts the process, so panel content is drawn through a guard: the
    # traceback is printed and the faulty panel is disabled instead of killing
    # the app.
    failed: list[Panel] = []

    def draw_panel(panel: Panel) -> None:
        if panel in failed:
            return
        try:
            panel.draw()
        except Exception:  # noqa: BLE001 - last resort guard
            failed.append(panel)
            traceback.print_exc()

    def make_dockable_window(panel: Panel) -> hello_imgui.DockableWindow:
        """Wrap a panel as a dockable window.

        hello_imgui calls ``imgui.begin()``/``imgui.end()`` around the gui
        function, so the panel only draws its content.
        """

        def gui() -> None:
            draw_panel(panel)

        return hello_imgui.DockableWindow(
            label_=panel.label,
            dock_space_name_=MAIN_DOCK_SPACE,
            gui_function_=gui,
        )

    runner_params = immapp.RunnerParams()
    runner_params.app_window_params.window_title = "Cat GIFs"
    runner_params.app_window_params.window_geometry.size = (900, 700)

    # Name of the settings file (window geometry, dock layout, panel
    # visibility). It is written inside `ini_folder_type` - the working
    # directory by default - and takes precedence over the name that is
    # otherwise derived from the window title.
    runner_params.ini_filename = "python_imgui_settings.ini"

    # Docking: hello_imgui provides a full screen dock space, and every panel is
    # a dockable window inside it. With one panel, "MainDockSpace" covers the
    # whole window, so that panel occupies all the available space; with several
    # panels the user can tab, split and rearrange them, and the layout is
    # remembered between runs.
    runner_params.imgui_window_params.default_imgui_window_type = (
        hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
    )
    # The "View" menu of the menu bar lists the panels (show/hide) and restores
    # the default layout - the escape hatch once there are several panels.
    runner_params.imgui_window_params.show_menu_bar = True
    runner_params.docking_params.dockable_windows = [
        make_dockable_window(panel) for panel in panels
    ]

    # Animated GIFs must keep rendering even when the mouse does not move.
    runner_params.fps_idling.enable_idling = False

    immapp.run(runner_params)


if __name__ == "__main__":
    main()
