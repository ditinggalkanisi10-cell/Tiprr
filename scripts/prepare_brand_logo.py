"""Trim the user's original TIPRR artwork, removing only connected outer black."""
from io import BytesIO
from pathlib import Path
import requests
import numpy as np
from PIL import Image, ImageDraw

SOURCE = 'https://customer-assets-jai6qajn.emergentagent.net/job_bonk-sender/artifacts/tf10yojk_file_000000006e1481faafb8aad5d292133d.png'
PUBLIC = Path(__file__).resolve().parents[1] / 'frontend' / 'public'


def main():
    response = requests.get(SOURCE, timeout=40)
    response.raise_for_status()
    original = Image.open(BytesIO(response.content)).convert('RGBA')
    original.save(PUBLIC / 'tiprr-logo-original.png', optimize=True)
    pixels = np.asarray(original).copy()
    mask = Image.fromarray(np.where(pixels[:, :, :3].max(axis=2) < 55, 255, 0).astype('uint8')).copy()
    # Flood-fill exterior only. Black wordmark ink enclosed by the white silhouette stays opaque.
    ImageDraw.floodfill(mask, (0, 0), 128)
    pixels[:, :, 3] = np.where(np.asarray(mask) == 128, 0, pixels[:, :, 3])
    cropped = Image.fromarray(pixels, 'RGBA')
    cropped = cropped.crop(cropped.getbbox())
    output = Image.new('RGBA', (cropped.width + 24, cropped.height + 24))
    output.alpha_composite(cropped, (12, 12))
    output.save(PUBLIC / 'tiprr-logo-pixel.png', optimize=True)
    icon = Image.new('RGBA', (256, 256))
    thumb = output.copy()
    thumb.thumbnail((240, 240), Image.Resampling.LANCZOS)
    icon.alpha_composite(thumb, ((256 - thumb.width) // 2, (256 - thumb.height) // 2))
    icon.save(PUBLIC / 'tiprr-logo-icon.png', optimize=True)
    print(f'Original logo prepared: {output.width}x{output.height}; artwork preserved.')


if __name__ == '__main__':
    main()