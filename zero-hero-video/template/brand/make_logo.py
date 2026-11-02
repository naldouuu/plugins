"""Render the ZERO logo files: mark, horizontal lockup, and app icon, on dark and transparent backgrounds."""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import render as r

OUT = os.path.dirname(os.path.abspath(__file__))


def glow_mark(size, bg):
    im = Image.new("RGBA", (size, size), bg)
    halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    r.zero_mark(ImageDraw.Draw(halo), size / 2, size / 2, size * .3, alpha=200)
    im.alpha_composite(halo.filter(ImageFilter.GaussianBlur(size * .05)))
    r.zero_mark(ImageDraw.Draw(im), size / 2, size / 2, size * .3)
    return im


def lockup(h, bg, ink):
    w = int(h * 3.6)
    im = Image.new("RGBA", (w, h), bg)
    im.alpha_composite(glow_mark(h, (0, 0, 0, 0)), (0, 0))
    g = ImageDraw.Draw(im)
    g.text((h * 1.0, h * .2), "ZERO", font=r.font("head", int(h * .52)), fill=ink)
    return im


for name, img in {
    "zero_mark_dark.png": glow_mark(1024, r.ZERO_NIGHT + (255,)),
    "zero_mark.png": glow_mark(1024, (0, 0, 0, 0)),
    "zero_lockup_dark.png": lockup(400, r.ZERO_NIGHT + (255,), (255, 255, 255, 255)),
    "zero_lockup_light.png": lockup(400, (255, 255, 255, 255), r.ZERO_NIGHT + (255,)),
}.items():
    img.save(os.path.join(OUT, name))
    print(name, img.size)
