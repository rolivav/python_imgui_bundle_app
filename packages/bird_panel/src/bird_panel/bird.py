"""Model of the "Bird" panel: a random bird picture decoded into RGBA pixels.

The *procurement* of the picture (the HTTP requests to the Nuthatch API, and the
JSON parsing that picks a bird and extracts its picture URL) happens in the native
Rust core :mod:`bird_core`; this module only decodes the returned bytes into
pixels.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from bird_core import fetch_random_bird

#: Shown when the API does not report a name for the bird.
UNKNOWN_NAME = "Bird"

#: Unsplash originals can be several thousand pixels wide. The panel scales the
#: picture down to the window anyway, and a texture that large would cost a lot of
#: GPU memory (4 bytes per pixel), so decoding is capped at this size.
MAX_DECODED_SIZE = 2048


@dataclass(frozen=True)
class BirdPicture:
    """A bird picture decoded into a single RGBA image."""

    pixels: np.ndarray  # uint8, shape (height, width, 4)
    name: str  # common name, e.g. "House Wren", for the caption
    sci_name: str = ""  # scientific name, e.g. "Troglodytes aedon"

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])

    @property
    def caption(self) -> str:
        """The species, as shown under the picture."""
        return f"{self.name} ({self.sci_name})" if self.sci_name else self.name


def decode_picture(data: bytes, name: str = UNKNOWN_NAME, sci_name: str = "") -> BirdPicture:
    """Decode image bytes (JPEG, PNG, ...) into a :class:`BirdPicture`.

    Pictures larger than :data:`MAX_DECODED_SIZE` are scaled down (keeping their
    ratio); the caption reports the size of the decoded picture.
    """
    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        rgba.thumbnail((MAX_DECODED_SIZE, MAX_DECODED_SIZE))
        pixels = np.ascontiguousarray(np.asarray(rgba, dtype=np.uint8))

    if pixels.ndim != 3 or pixels.shape[2] != 4 or pixels.shape[0] == 0 or pixels.shape[1] == 0:
        raise ValueError("the downloaded file does not contain a usable image")
    return BirdPicture(pixels=pixels, name=name, sci_name=sci_name)


def fetch_random_bird_picture() -> BirdPicture:
    """Download a random bird picture through the native core and decode it.

    Blocking: always call this from a worker thread (see
    :meth:`bird_panel.BirdPanel.request_new_bird`). The Rust core performs the
    network I/O and releases the GIL while doing so.
    """
    image = fetch_random_bird()
    return decode_picture(image.data, image.name, image.sci_name)
