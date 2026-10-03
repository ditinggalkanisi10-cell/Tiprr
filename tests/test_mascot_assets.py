"""Mascot asset validation for public PNG endpoints."""

import io
from typing import Tuple

import numpy as np
import requests
from PIL import Image


BASE_URL = "https://bonk-sender.preview.emergentagent.com"


def _fetch_png(path: str) -> Tuple[requests.Response, Image.Image]:
    response = requests.get(f"{BASE_URL}{path}", timeout=20)
    image = Image.open(io.BytesIO(response.content))
    return response, image


def _assert_opaque_bw_only(image: Image.Image):
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba)

    # Opaque pixels must be pure black or pure white only.
    opaque = arr[arr[:, :, 3] == 255][:, :3]
    if opaque.size == 0:
        raise AssertionError("No opaque pixels found in mascot image")

    allowed = {(0, 0, 0), (255, 255, 255)}
    unique = {tuple(pixel.tolist()) for pixel in np.unique(opaque, axis=0)}
    invalid = unique - allowed
    assert not invalid, f"Invalid opaque RGB colors found: {sorted(invalid)}"

    # No green spill in any visible pixel.
    visible = arr[arr[:, :, 3] > 0][:, :3]
    green_dominant = visible[
        (visible[:, 1] > visible[:, 0]) & (visible[:, 1] > visible[:, 2])
    ]
    assert len(green_dominant) == 0, "Green spill detected in visible pixels"


def test_mascot_v2_png_contract():
    """Validate mascot dimensions, RGBA mode and monochrome visible color contract."""
    response, image = _fetch_png("/tiprr-mascot-v2.png")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("image/png")
    assert image.mode == "RGBA"
    assert image.size == (774, 1208)
    alpha_min, alpha_max = image.getchannel("A").getextrema()
    assert alpha_min == 0 and alpha_max == 255
    _assert_opaque_bw_only(image)


def test_favicon_v2_png_contract():
    """Validate favicon dimensions, RGBA mode and monochrome visible color contract."""
    response, image = _fetch_png("/tiprr-favicon-v2.png")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("image/png")
    assert image.mode == "RGBA"
    assert image.size == (256, 256)
    alpha_min, alpha_max = image.getchannel("A").getextrema()
    assert alpha_min == 0 and alpha_max == 255
    _assert_opaque_bw_only(image)
