"""Model of the "Dog" panel: a random dog picture decoded into RGBA pixels.

The *procurement* of the picture (the two HTTP requests to dog.ceo, and the JSON
parsing that extracts the picture URL) happens in the native C++ core
:mod:`dog_core`; this module only decodes the returned bytes into pixels.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from dog_core import fetch_random_dog

#: Shown when a picture URL does not carry a recognizable breed.
UNKNOWN_BREED = "Dog"


@dataclass(frozen=True)
class DogPicture:
    """A dog picture decoded into a single RGBA image."""

    pixels: np.ndarray  # uint8, shape (height, width, 4)
    breed: str  # e.g. "Afghan Hound", for the caption

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])


def decode_picture(data: bytes, breed: str = UNKNOWN_BREED) -> DogPicture:
    """Decode image bytes (JPEG, PNG, ...) into a :class:`DogPicture`."""
    with Image.open(io.BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        pixels = np.ascontiguousarray(np.asarray(rgba, dtype=np.uint8))

    if pixels.ndim != 3 or pixels.shape[2] != 4 or pixels.shape[0] == 0 or pixels.shape[1] == 0:
        raise ValueError("the downloaded file does not contain a usable image")
    return DogPicture(pixels=pixels, breed=breed)


def fetch_random_dog_picture() -> DogPicture:
    """Download a random dog picture through the native core and decode it.

    Blocking: always call this from a worker thread (see
    :meth:`DogPanel.request_new_dog`). The C++ core performs the network I/O and
    releases the GIL while doing so.
    """
    image = fetch_random_dog()
    return decode_picture(image.data, image.breed)
