"""Logic and UI of the "Bird" panel.

* logic: :class:`BirdPanel` downloads in a background thread (so the GUI never
  freezes) and uploads the picture to the GPU once it arrives.
* ui:    :meth:`BirdPanel.draw` renders the panel content and its "Get Bird"
  button.

The model (``BirdPicture`` and the functions that build it) lives in
:mod:`bird_panel.bird`.
"""

from __future__ import annotations

import threading
from typing import Union

from imgui_bundle import hello_imgui, imgui

from .bird import BirdPicture, fetch_random_bird_picture


class _BirdTexture:
    """The GPU texture backing a :class:`BirdPicture`.

    Textures must be created on the GUI thread while the rendering backend is
    alive, hence this small wrapper: it keeps the owning handle alive (the GPU
    memory is released when it is garbage collected) and exposes a ready to use
    ``ImTextureRef``.
    """

    def __init__(self, picture: BirdPicture) -> None:
        self._handle = hello_imgui.create_texture_gpu_from_rgba_data(picture.pixels)
        self._ref = imgui.ImTextureRef(self._handle.texture_id())

    @property
    def ref(self) -> imgui.ImTextureRef:
        return self._ref


class BirdPanel:
    """The "Bird" panel: a random bird picture with a "Get Bird" button."""

    #: Title of the panel's dockable window (also the label of its tab).
    label: str = "Bird (Rust)"

    def __init__(self) -> None:
        self._picture: Union[BirdPicture, None] = None
        self._texture: Union[_BirdTexture, None] = None
        self._is_loading = False
        self._error: Union[str, None] = None

        # Written by the download thread, consumed by the GUI thread.
        self._download_result: Union[BirdPicture, Exception, None] = None

    # ------------------------------------------------------------------ logic

    def request_new_bird(self) -> None:
        """Start downloading a new random bird picture (non-blocking)."""
        if self._is_loading:
            return
        self._is_loading = True
        self._error = None
        threading.Thread(
            target=self._download_worker, name="bird-picture-download", daemon=True
        ).start()

    def _download_worker(self) -> None:
        """Thread body: fetch + decode, and hand the result over to the GUI."""
        try:
            self._download_result = fetch_random_bird_picture()
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            self._download_result = error

    def _collect_download(self) -> None:
        """Pick up the worker's result. Must run on the GUI thread."""
        result, self._download_result = self._download_result, None
        if result is None:
            return

        self._is_loading = False
        if isinstance(result, Exception):
            self._error = f"Could not fetch a bird picture ({result})."
            return

        self._set_picture(result)

    def _set_picture(self, picture: BirdPicture) -> None:
        """Adopt a freshly downloaded picture (uploads it to the GPU)."""
        self._picture = picture
        self._texture = _BirdTexture(picture)

    # --------------------------------------------------------------------- ui

    def draw(self) -> None:
        """Draw the panel content (called once per frame, on the GUI thread).

        The panel does not open a window itself: the host application registers
        it as a dockable window, so hello_imgui calls ``imgui.begin()`` /
        ``imgui.end()`` around this method. The content therefore fills whatever
        space the dock layout grants the panel.
        """
        self._collect_download()

        # The panel shows a bird as soon as it is displayed for the first time.
        if self._picture is None and not self._is_loading and self._error is None:
            self.request_new_bird()

        self._draw_toolbar()
        imgui.separator()
        self._draw_picture()

    def _draw_toolbar(self) -> None:
        # Snapshot the state: the button handler below changes it, and
        # begin_disabled()/end_disabled() must stay balanced within a frame.
        is_loading = self._is_loading

        if is_loading:
            imgui.begin_disabled()
        clicked = imgui.button("Get Bird")
        if is_loading:
            imgui.end_disabled()

        if clicked:
            self.request_new_bird()
        if is_loading:
            imgui.same_line()
            imgui.text("Fetching a bird...")

    def _draw_picture(self) -> None:
        if self._error is not None:
            imgui.text_wrapped(self._error)
            imgui.text_wrapped("Check your connection, then press 'Get Bird' again in a moment.")
            return

        if self._picture is None or self._texture is None:
            imgui.text("Waiting for a bird...")
            return

        picture, texture = self._picture, self._texture
        available = imgui.get_content_region_avail()
        max_height = available.y - hello_imgui.em_size(2.5)  # leave room for the caption
        size = _fit_size(picture.width, picture.height, available.x, max(1.0, max_height))

        # Center the picture horizontally inside the window.
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + max(0.0, (available.x - size.x) * 0.5))
        imgui.image(texture.ref, size)

        imgui.text_disabled(f"{picture.caption} - {picture.width}x{picture.height}")


def _fit_size(image_width: int, image_height: int, max_width: float, max_height: float) -> imgui.ImVec2:
    """Largest size that fits the image in the given box, keeping its ratio."""
    if image_width <= 0 or image_height <= 0 or max_width <= 0 or max_height <= 0:
        return imgui.ImVec2(0.0, 0.0)
    scale = min(max_width / image_width, max_height / image_height)
    return imgui.ImVec2(image_width * scale, image_height * scale)
