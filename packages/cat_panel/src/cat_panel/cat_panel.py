"""Logic and UI of the "Cat" panel.

* logic: :class:`CatPanel` downloads in a background thread (so the GUI never
  freezes), uploads the frames to the GPU once they arrive, and advances the
  current frame according to each frame's duration.
* ui:    :meth:`CatPanel.draw` renders the panel content and its "Get Cat"
  button.

The model (``CatGif`` and the functions that build it) lives in
:mod:`cat_panel.cat_gif`.
"""

from __future__ import annotations

import threading
import time
from typing import Union

from imgui_bundle import hello_imgui, imgui

from .cat_gif import CatGif, fetch_random_cat_gif


class _GifTextures:
    """The GPU textures backing the frames of a :class:`CatGif`.

    Textures must be created on the GUI thread while the rendering backend is
    alive, hence this small wrapper: it keeps the owning handles alive (the GPU
    memory is released when they are garbage collected) and exposes ready to
    use ``ImTextureRef`` values.
    """

    def __init__(self, cat: CatGif) -> None:
        self._handles = [
            hello_imgui.create_texture_gpu_from_rgba_data(frame) for frame in cat.frames
        ]
        self._refs = [imgui.ImTextureRef(handle.texture_id()) for handle in self._handles]

    def __len__(self) -> int:
        return len(self._refs)

    def ref(self, frame_index: int) -> imgui.ImTextureRef:
        return self._refs[frame_index]


class CatPanel:
    """The "Cat" panel: a random animated cat GIF with a "Get Cat" button."""

    #: Title of the panel's dockable window (also the label of its tab).
    label: str = "Cat"

    def __init__(self) -> None:
        self._cat: Union[CatGif, None] = None
        self._textures: Union[_GifTextures, None] = None
        self._is_loading = False
        self._error: Union[str, None] = None

        # Written by the download thread, consumed by the GUI thread.
        self._download_result: Union[CatGif, Exception, None] = None

        self._frame_index = 0
        self._frame_deadline = 0.0

    # ------------------------------------------------------------------ logic

    def request_new_cat(self) -> None:
        """Start downloading a new random cat GIF (non-blocking)."""
        if self._is_loading:
            return
        self._is_loading = True
        self._error = None
        threading.Thread(target=self._download_worker, name="cat-gif-download", daemon=True).start()

    def _download_worker(self) -> None:
        """Thread body: fetch + decode, and hand the result over to the GUI."""
        try:
            self._download_result = fetch_random_cat_gif()
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            self._download_result = error

    def _collect_download(self) -> None:
        """Pick up the worker's result. Must run on the GUI thread."""
        result, self._download_result = self._download_result, None
        if result is None:
            return

        self._is_loading = False
        if isinstance(result, Exception):
            self._error = f"Could not fetch a cat GIF ({result})."
            return

        self._set_cat(result)

    def _set_cat(self, cat: CatGif) -> None:
        """Adopt a freshly downloaded cat (uploads its frames to the GPU)."""
        self._cat = cat
        self._textures = _GifTextures(cat)
        self._frame_index = 0
        self._frame_deadline = time.monotonic() + cat.frame_durations[0]

    def _advance_animation(self) -> None:
        """Move to the frame that should be displayed right now."""
        cat = self._cat
        if cat is None or len(cat.frames) < 2:
            return

        now = time.monotonic()
        if now < self._frame_deadline:
            return

        # Skip ahead if the app was busy (or paused), without ever looping more
        # than once through the animation.
        steps = 0
        while now >= self._frame_deadline and steps < len(cat.frames):
            steps += 1
            self._frame_index = (self._frame_index + 1) % len(cat.frames)
            self._frame_deadline += cat.frame_durations[self._frame_index]

        if now >= self._frame_deadline:  # still behind: resynchronize
            self._frame_deadline = now + cat.frame_durations[self._frame_index]

    # --------------------------------------------------------------------- ui

    def draw(self) -> None:
        """Draw the panel content (called once per frame, on the GUI thread).

        The panel does not open a window itself: the host application registers
        it as a dockable window, so hello_imgui calls ``imgui.begin()`` /
        ``imgui.end()`` around this method. The content therefore fills whatever
        space the dock layout grants the panel.
        """
        self._collect_download()
        self._advance_animation()

        # The panel shows a cat as soon as it is displayed for the first time.
        if self._cat is None and not self._is_loading and self._error is None:
            self.request_new_cat()

        self._draw_toolbar()
        imgui.separator()
        self._draw_picture()

    def _draw_toolbar(self) -> None:
        # Snapshot the state: the button handler below changes it, and
        # begin_disabled()/end_disabled() must stay balanced within a frame.
        is_loading = self._is_loading

        if is_loading:
            imgui.begin_disabled()
        clicked = imgui.button("Get Cat")
        if is_loading:
            imgui.end_disabled()

        if clicked:
            self.request_new_cat()
        if is_loading:
            imgui.same_line()
            imgui.text("Fetching a cat...")

    def _draw_picture(self) -> None:
        if self._error is not None:
            imgui.text_wrapped(self._error)
            imgui.text_wrapped("Check your internet connection, then press 'Get Cat' again.")
            return

        if self._cat is None or self._textures is None:
            imgui.text("Waiting for a cat...")
            return

        cat, textures = self._cat, self._textures
        available = imgui.get_content_region_avail()
        max_height = available.y - hello_imgui.em_size(2.5)  # leave room for the caption
        size = _fit_size(cat.width, cat.height, available.x, max(1.0, max_height))

        # Center the picture horizontally inside the window.
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + max(0.0, (available.x - size.x) * 0.5))
        imgui.image(textures.ref(self._frame_index), size)

        imgui.text_disabled(
            f"{cat.width}x{cat.height}, frame {self._frame_index + 1}/{len(textures)}"
        )


def _fit_size(image_width: int, image_height: int, max_width: float, max_height: float) -> imgui.ImVec2:
    """Largest size that fits the image in the given box, keeping its ratio."""
    if image_width <= 0 or image_height <= 0 or max_width <= 0 or max_height <= 0:
        return imgui.ImVec2(0.0, 0.0)
    scale = min(max_width / image_width, max_height / image_height)
    return imgui.ImVec2(image_width * scale, image_height * scale)
