"""Native (C++) image procurement core for the Dog panel.

The extension module :mod:`dog_core._dog_core` performs the two HTTP requests
(the dog.ceo API, then the picture itself) and the JSON parsing in C++; the
caller only decodes the returned bytes into pixels.
"""

from __future__ import annotations

from typing import NamedTuple

from ._dog_core import fetch_random_dog as _fetch_random_dog


class DogImage(NamedTuple):
    """The encoded picture returned by :func:`fetch_random_dog`."""

    data: bytes  # the encoded image (JPEG/PNG/...), to be decoded by the caller
    breed: str  # e.g. "Afghan Hound"
    url: str  # where the picture was downloaded from


def fetch_random_dog() -> DogImage:
    """Fetch a random dog picture from dog.ceo (blocking network I/O).

    The native core releases the GIL while the requests are in flight, so this
    is safe to call from a worker thread.
    """
    data, breed, url = _fetch_random_dog()
    return DogImage(data=data, breed=breed, url=url)


__all__ = ["DogImage", "fetch_random_dog"]
