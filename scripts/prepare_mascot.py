"""Prepare the approved reference-based redraw as true transparent monochrome PNGs."""
from io import BytesIO
from pathlib import Path
import requests
import numpy as np
from PIL import Image, ImageFilter

SOURCE = 'https://static.prod-images.emergentagent.com/jobs/7978b0af-e594-4e82-9254-304bcff2d69d/images/69551b105dc19bf71e32afdad71f8da12b9975c8df690480501683e7e7bce0fa.jpeg'
PUBLIC = Path(__file__).resolve().parents[1] / 'frontend' / 'public'


def main():
    response = requests.get(SOURCE, timeout=30)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert('RGB')
    rgb = np.asarray(image).astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    # Remove green including JPEG spill. Only black/white ink remains.
    background = (g > r + 28) & (g > b + 28)
    alpha = np.where(background, 0, 255).astype(np.uint8)
    ink = np.where(np.minimum(r, b) >= 128, 255, 0).astype(np.uint8)
    pixels = np.stack([ink, ink, ink, alpha], axis=-1)
    sprite = Image.fromarray(pixels, 'RGBA')
    sprite = sprite.crop(sprite.getbbox())
    padded = Image.new('RGBA', (sprite.width + 32, sprite.height + 32))
    padded.alpha_composite(sprite, (16, 16))
    # Strengthen existing white strokes without changing the underlying geometry.
    white_ink = padded.convert('L').point(lambda value: 255 if value > 127 else 0)
    white_ink = white_ink.filter(ImageFilter.MaxFilter(13))
    opaque = padded.getchannel('A')
    padded = Image.merge('RGBA', (white_ink, white_ink, white_ink, opaque))
    # Square-grid white contour keeps the black silhouette legible at logo size.
    outline = padded.getchannel('A').filter(ImageFilter.MaxFilter(15))
    result = Image.new('RGBA', padded.size, (255, 255, 255, 0))
    result.putalpha(outline)
    result.alpha_composite(padded)
    result.save(PUBLIC / 'tiprr-mascot-v2.png', optimize=True)
    icon = Image.new('RGBA', (256, 256))
    icon_sprite = result.copy()
    icon_sprite.thumbnail((224, 224), Image.Resampling.NEAREST)
    icon.alpha_composite(icon_sprite, ((256 - icon_sprite.width) // 2, (256 - icon_sprite.height) // 2))
    icon.save(PUBLIC / 'tiprr-favicon-v2.png', optimize=True)
    print(f'Transparent monochrome mascot prepared: {result.width}x{result.height}')


if __name__ == '__main__':
    main()