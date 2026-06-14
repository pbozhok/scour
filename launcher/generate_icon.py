"""Generate scour.ico for the desktop shortcut."""
from PIL import Image, ImageDraw, ImageFont
import os

FONT_PATHS = [
    r'C:\Windows\Fonts\segoeuib.ttf',
    r'C:\Windows\Fonts\calibrib.ttf',
    r'C:\Windows\Fonts\arialbd.ttf',
]

BG = (7, 7, 15)       # #07070f — dark
C1 = (168, 85, 247)   # #a855f7 — violet
C2 = (34, 211, 238)   # #22d3ee — cyan
MASTER = 512


def make_master():
    size = MASTER
    radius = size // 5

    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=(*BG, 255))

    # Diagonal gradient
    pixels = []
    denom = max(1, 2 * (size - 1))
    for y in range(size):
        for x in range(size):
            t = (x + y) / denom
            pixels.append((
                int(C1[0] + t * (C2[0] - C1[0])),
                int(C1[1] + t * (C2[1] - C1[1])),
                int(C1[2] + t * (C2[2] - C1[2])),
                255,
            ))
    grad = Image.new('RGBA', (size, size))
    grad.putdata(pixels)

    # Text mask at full resolution
    font = None
    for path in FONT_PATHS:
        try:
            font = ImageFont.truetype(path, int(size * 0.68))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    bbox = mask_draw.textbbox((0, 0), 'S', font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    mask_draw.text((x, y), 'S', fill=255, font=font)

    grad.putalpha(mask)
    img.paste(grad, (0, 0), grad)
    return img


master = make_master()
sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scour.ico')
master.save(out, format='ICO', sizes=sizes)
print(f'Saved: {out}')

# Verify
import struct
with open(out, 'rb') as f:
    _, _, count = struct.unpack('<HHH', f.read(6))
    print(f'Frames in ICO: {count}')
    for i in range(count):
        w, h, _, _, _, bpp, size, _ = struct.unpack('<BBBBHHII', f.read(16))
        print(f'  {w if w else 256}x{h if h else 256}  bpp={bpp}  {size}B')
