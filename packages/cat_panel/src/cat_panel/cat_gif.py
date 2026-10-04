"""Model of the "Cat" panel: a cat animation decoded into RGBA frames."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Tuple

import numpy as np
import requests
from PIL import Image, ImageSequence

#: cataas.com endpoint returning a random cat GIF.
RANDOM_CAT_GIF_URL = "https://cataas.com/cat/gif"

#: How long we wait for the download before giving up.
REQUEST_TIMEOUT_S = 15.0

#: Frame durations are clamped: a GIF frame is never shorter than this, which
#: keeps the animation readable and the update loop well behaved.
MIN_FRAME_DURATION_S = 0.02

#: ... and never longer than this (some GIFs contain multi minutes pauses).
MAX_FRAME_DURATION_S = 2.0


@dataclass(frozen=True)
class CatGif:
    """A cat animation decoded into RGBA frames."""

    frames: Tuple[np.ndarray, ...]  # each frame: uint8, shape (height, width, 4)
    frame_durations: Tuple[float, ...]  # seconds, one per frame

    @property
    def width(self) -> int:
        return int(self.frames[0].shape[1])

    @property
    def height(self) -> int:
        return int(self.frames[0].shape[0])

    @property
    def duration(self) -> float:
        """Total duration of one loop of the animation, in seconds."""
        return float(sum(self.frame_durations))


def decode_gif(data: bytes) -> CatGif:
    """Decode GIF (or any Pillow supported animation) bytes into a :class:`CatGif`."""
    with Image.open(io.BytesIO(data)) as image:
        frames: list[np.ndarray] = []
        durations: list[float] = []
        for frame in ImageSequence.Iterator(image):
            duration_ms = frame.info.get("duration") or image.info.get("duration") or 0
            durations.append(
                min(max(duration_ms / 1000.0, MIN_FRAME_DURATION_S), MAX_FRAME_DURATION_S)
            )
            rgba = frame.convert("RGBA")
            frames.append(np.ascontiguousarray(np.asarray(rgba, dtype=np.uint8)))

    if not frames:
        raise ValueError("the downloaded file does not contain any image frame")
    return CatGif(frames=tuple(frames), frame_durations=tuple(durations))


def fetch_random_cat_gif(url: str = RANDOM_CAT_GIF_URL) -> CatGif:
    """Download a random cat GIF from cataas.com and decode it.

    Blocking: always call this from a worker thread (see
    :meth:`CatPanel.request_new_cat`).
    """
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT_S,
        headers={"User-Agent": "cat-gifs-imgui-bundle-app/1.0"},
    )
    response.raise_for_status()
    return decode_gif(response.content)
