"""Pattern registry and a bounded, reusable Pillow knit renderer."""
from __future__ import annotations
from functools import lru_cache
from importlib.resources import files
import hashlib
import json
import math
import re
import warnings
from PIL import Image, ImageChops, ImageDraw, ImageColor
from .config import COLORS


def patterns():
    return json.loads(files('xfce4_sweaters').joinpath('data/patterns.json').read_text())

class Registry:
    def __init__(self, directory=None):
        self.specs = {x['id']: x for x in patterns()}
        self.custom = {}
        self.errors = []
        if directory and directory.exists():
            for path in sorted(directory.glob('*.png')):
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', path.stem):
                    self.errors.append(f'{path.name}: use letters, numbers, _ or -')
                    continue
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('error', Image.DecompressionBombWarning)
                        with Image.open(path) as img:
                            if img.format != 'PNG' or not (1 <= img.width <= 1024 and 1 <= img.height <= 1024):
                                raise ValueError('PNG tiles must be at most 1024 × 1024')
                            img.verify()
                    self.custom['user:' + path.stem] = path
                except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
                    self.errors.append(f'{path.name}: {exc}')
        self.ids = tuple(sorted((*self.specs, *self.custom)))

    def resolve(self, style, identity, seed):
        resolved = dict(style)
        digest = hashlib.sha256(f'{seed}:{identity}'.encode()).digest()
        if resolved['texture'] == 'random':
            resolved['texture'] = self.ids[int.from_bytes(digest[:8], 'big') % len(self.ids)]
        if resolved['color'] == 'random':
            resolved['color'] = COLORS[digest[8] % len(COLORS)]
        return resolved

    @lru_cache(maxsize=64)
    def tile(self, texture, color, stitch):
        if texture in self.custom:
            with Image.open(self.custom[texture]) as image:
                return image.convert('RGBA')
        spec = self.specs[texture]
        rows = spec['rows']
        scale = 3
        w, h = len(rows[0]) * stitch, len(rows) * stitch
        tile = Image.new('RGB', (w * scale, h * scale), shade(color, 0.50))
        draw = ImageDraw.Draw(tile)
        step = stitch * scale
        for y in range(-1, len(rows) + 1):
            for x in range(-1, len(rows[0]) + 1):
                symbol = rows[y % len(rows)][x % len(rows[0])]
                yarn = color if symbol == '.' else spec['colors'][ord(symbol) - ord('a')]
                px, py = x * step, y * step
                # Two curved strands form a V stitch. Repeats wrap seamlessly.
                for side in (-1, 1):
                    points = []
                    for t in range(13):
                        u = t / 12
                        xx = px + step * (0.5 + side * (0.40 * (1-u) + 0.09 * math.sin(math.pi*u)))
                        yy = py + step * (0.08 + 0.82*u)
                        points.append((xx, yy))
                    for width, brightness, offset in [(0.42, 0.42, 1), (0.29, 1.0, 0), (0.09, 1.27, -0.7)]:
                        draw.line([(a+offset,b+offset) for a,b in points], fill=shade(yarn, brightness), width=max(1,round(step*width)))
        return tile.resize((w,h), Image.Resampling.LANCZOS).convert('RGBA')

def shade(color, factor):
    return tuple(min(255, round(c*factor)) for c in ImageColor.getrgb(color))

def strip(tile, length, width):
    out = Image.new('RGBA', (length, width))
    for y in range(0, width, tile.height):
        for x in range(0, length, tile.width):
            out.paste(tile, (x, y))
    return out

def border(registry, width, height, style, opacity=1.0):
    """Render a transparent ring; width/height include the outside border."""
    band = style['width']
    if min(width, height) <= 2*band or max(width,height) > 16384:
        raise ValueError('Invalid border dimensions')
    tile = registry.tile(style['texture'], style['color'], style['stitch'])
    out = Image.new('RGBA', (width, height))
    # Four mitred fabric strips, each with stitches following the edge.
    for length, angle, pos in [(width,0,(0,0)), (height,270,(width-band,0)),
                               (width,180,(0,height-band)), (height,90,(0,0))]:
        edge = strip(tile,length,band)
        mask = Image.new('L',edge.size)
        ImageDraw.Draw(mask).polygon([(0,0),(length-1,0),(length-band,band-1),(band-1,band-1)],fill=255)
        # Preserve alpha supplied by custom textures.
        edge.putalpha(ImageChops.multiply(edge.getchannel('A'), mask))
        out.alpha_composite(edge.rotate(angle,expand=True),pos)
    # Round the outer corners like the edge of a knitted piece; the inner corners stay square.
    outline = Image.new('L',(width,height))
    ImageDraw.Draw(outline).rounded_rectangle((0,0,width-1,height-1),radius=band//2,fill=255)
    out.putalpha(ImageChops.multiply(out.getchannel('A'), outline))
    if opacity != 1:
        out.putalpha(out.getchannel('A').point(lambda v: round(v*opacity)))
    return out
