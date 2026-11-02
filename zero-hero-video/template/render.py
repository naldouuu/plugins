"""ZERO hero template: turn a JSON brief into a vertical reel where Zero, the AI hero, lives inside the client's brand.

    python3 render.py briefs/apex_electrician.json            # full 1080x1920 render
    python3 render.py briefs/apex_electrician.json --preview  # quick 540x960 check

Needs Python 3.9+, numpy, Pillow and ffmpeg on PATH. See README.md for the brief format.
"""
import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ZERO_CYAN, ZERO_BOLT, ZERO_NIGHT = (25, 227, 255), (255, 210, 63), (7, 11, 18)  # the ZERO product brand, constant across clients
SR, FPS = 44100, 30
FONTS = {
    "serif": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/Library/Fonts/Georgia Bold.ttf", "C:/Windows/Fonts/georgiab.ttf"],
    "head": ["/usr/share/fonts/opentype/inter/InterDisplay-Black.otf", "/Library/Fonts/Arial Black.ttf", "C:/Windows/Fonts/ariblk.ttf"],
    "bold": ["/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "reg": ["/usr/share/fonts/opentype/inter/Inter-Medium.otf", "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"],
}
_fc = {}


def fail(msg):
    sys.exit(f"render.py: error: {msg}")


def font(kind, size):
    key = (kind, size)
    if key not in _fc:
        for p in FONTS[kind]:
            if os.path.exists(p):
                _fc[key] = ImageFont.truetype(p, size)
                break
        else:
            _fc[key] = ImageFont.load_default(size)
    return _fc[key]


def rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def wrap(d, text, f, max_w):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if d.textlength(test, font=f) <= max_w or not line:
            line = test
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def path_in(brief_dir, p, field):
    if p is None:
        return None
    full = p if os.path.isabs(p) else os.path.normpath(os.path.join(brief_dir, p))
    if not os.path.exists(full):
        fail(f"{field}: file not found: {full}")
    return full


# ---------------------------------------------------------------- brief
class Brief:
    def __init__(self, path, preview):
        if not os.path.exists(path):
            fail(f"brief not found: {path}")
        with open(path) as f:
            b = json.load(f)
        self.dir = os.path.dirname(os.path.abspath(path))
        self.preview = preview
        self.W, self.H = (540, 960) if preview else (1080, 1920)
        self.k = self.W / 1080  # layout scale
        br = b.get("brand") or fail("brand: missing")
        self.name = br.get("name") or fail("brand.name: missing")
        self.show_initials = br.get("initials_on_crest", True)
        self.initials = br.get("initials") or "".join(w[0] for w in self.name.split()[:2]).upper()
        self.primary = rgb(br.get("primary", "#2DA8E2"))
        self.accent = rgb(br.get("accent", "#40E0FF"))
        self.dark = rgb(br.get("dark", "#0B0F14"))
        self.logo = path_in(self.dir, br.get("logo"), "brand.logo")
        self.face = path_in(self.dir, br.get("face"), "brand.face")
        self.person = br.get("person")
        self.role = br.get("role", self.name)
        self.handle, self.site = br.get("handle"), br.get("site")
        hero = b.get("hero", {})
        self.hero = hero.get("name", "Zero")
        self.hero_line = hero.get("tagline", f"The hero inside {self.name}.")
        self.scenes = b.get("scenes") or fail("scenes: missing")
        for i, s in enumerate(self.scenes):
            s.setdefault("kind", "problem")
            if s["kind"] != "reveal":
                s["src_path"] = path_in(self.dir, s.get("src") or fail(f"scenes[{i}].src: missing"), f"scenes[{i}].src")
            s["dur"] = float(s.get("dur", 3.6))
            if preview:
                s["dur"] = min(s["dur"], 1.4)
        self.end = b.get("end", {})
        self.end_dur = 1.6 if preview else float(self.end.get("dur", 4.0))
        self.voice = [] if preview else [dict(v, path=path_in(self.dir, v["file"], "voice.file")) for v in b.get("voice", [])]
        out = b.get("output", "out.mp4")
        self.out = os.path.normpath(out if os.path.isabs(out) else os.path.join(self.dir, out))
        if preview:
            self.out = self.out.replace(".mp4", "_preview.mp4")
        starts = np.cumsum([0] + [s["dur"] for s in self.scenes])
        for s, t in zip(self.scenes, starts):
            s["start"] = float(t)
        self.end_start = float(starts[-1])
        self.total = self.end_start + self.end_dur


# ---------------------------------------------------------------- sources
def clip_reader(B, s):
    src, W, H = s["src_path"], B.W, B.H
    if src.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        base = ImageOps.fit(Image.open(src).convert("RGB"), (int(W * 1.12), int(H * 1.12)), Image.LANCZOS)
        n = max(1, round(s["dur"] * FPS))
        zoom_in = s.get("zoom", "in") == "in"
        for i in range(n + 10_000):
            p = ease(min(1, i / n))
            z = 1 + 0.12 * (p if zoom_in else 1 - p)
            cw, ch = W * 1.12 / z, H * 1.12 / z
            x0, y0 = (base.width - cw) / 2, (base.height - ch) * 0.45
            yield base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
        return
    p = subprocess.Popen(["ffmpeg", "-v", "quiet", "-ss", str(s.get("in", 0)), "-t", str(s["dur"] + .3), "-i", src,
                          "-vf", f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    last = Image.new("RGB", (W, H), B.dark)
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        last = Image.frombuffer("RGB", (W, H), buf).copy()
        yield last
    p.stdout.close()
    p.wait()
    while True:
        yield last


# ---------------------------------------------------------------- graphics
def caption(B, d, text, lt, dur):
    """Word-by-word bold serif caption in the lower third."""
    if not text:
        return
    words = text.split()
    shown = max(1, min(len(words), int(lt / max(.9, dur * .6) * len(words)) + 1))
    k = B.k
    f = font("serif", int(64 * k))
    lines = wrap(d, " ".join(words[:shown]), f, B.W - 160 * k)
    y = 1440 * k - (len(lines) - 1) * 76 * k
    for ln in lines:
        x = (B.W - d.textlength(ln.replace("*", ""), font=f)) / 2
        for word in ln.split():  # *word* = highlighted in the brand's accent color
            hot = word.startswith("*") or word.endswith("*") or word.strip(".,!?").endswith("*")
            clean = word.replace("*", "")
            d.text((x, y), clean, font=f, fill=B.accent if hot else (255, 255, 255), stroke_width=max(2, int(6 * k)), stroke_fill=(15, 15, 15))
            x += d.textlength(clean + " ", font=f)
        y += 76 * k


def shade_band(B, im):
    band = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle((0, 1330 * B.k, B.W, 1640 * B.k), fill=(0, 0, 0, 85))
    band = band.filter(ImageFilter.GaussianBlur(40 * B.k))
    im.paste(band, (0, 0), band)


def zero_mark(g, cx, cy, R, ring=ZERO_CYAN, bolt=ZERO_BOLT, alpha=255):
    """The ZERO mark: a bold upright 0 ring with a lightning bolt cutting through it."""
    w = max(2, int(R * .26))
    g.ellipse((cx - R * .78, cy - R, cx + R * .78, cy + R), outline=ring + (alpha,), width=w)
    b = [(.18, -1.25), (-.34, .12), (-.02, .12), (-.22, 1.25), (.38, -.18), (.06, -.18), (.26, -1.25)]
    g.polygon([(cx + x * R, cy + y * R) for x, y in b], fill=bolt + (alpha,), outline=ZERO_NIGHT + (alpha,))


def crest(B, size, glow=1.0, t=0.0):
    """The hero's emblem: a shield in brand colors with the brand initials and a glowing core."""
    S = int(size)
    im = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    g = ImageDraw.Draw(im)
    cx, cy = S, S
    shield = [(cx - .62 * S, cy - .7 * S), (cx + .62 * S, cy - .7 * S), (cx + .62 * S, cy + .05 * S), (cx, cy + .78 * S), (cx - .62 * S, cy + .05 * S)]
    halo = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).polygon([(x, y) for x, y in shield], fill=B.accent + (int(170 * glow),))
    im.alpha_composite(halo.filter(ImageFilter.GaussianBlur(S * .18)))
    g.polygon(shield, fill=B.dark + (255,), outline=B.primary + (255,))
    inner = [(cx + (x - cx) * .86, cy + (y - cy) * .86 - .02 * S) for x, y in shield]
    g.line(inner + [inner[0]], fill=B.accent + (255,), width=max(2, S // 40))
    r = S * (.2 + .025 * math.sin(t * 7))
    core = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(core).ellipse((cx - r * 1.8, cy - .12 * S - r * 1.8, cx + r * 1.8, cy - .12 * S + r * 1.8), fill=B.accent + (int(150 * glow),))
    im.alpha_composite(core.filter(ImageFilter.GaussianBlur(S * .08)))
    zero_mark(g, cx, cy - .1 * S, S * .3, ring=B.accent)
    if B.show_initials:
        f = font("head", int(S * .13))
        tw = g.textlength(B.initials, font=f)
        g.text((cx - tw / 2, cy + .34 * S), B.initials, font=f, fill=(255, 255, 255, 230))
    return im


def bolt(rng, x0, y0, x1, y1, jag):
    pts = [(x0, y0)]
    n = 9
    for i in range(1, n):
        f = i / n
        pts.append((x0 + (x1 - x0) * f + rng.uniform(-jag, jag), y0 + (y1 - y0) * f + rng.uniform(-jag, jag)))
    return pts + [(x1, y1)]


def reveal_frame(B, s, lt):
    """'Meet Jarvis': the hero bursts out of the brand crest with energy rays and lightning."""
    W, H, k = B.W, B.H, B.k
    im = Image.new("RGB", (W, H), tuple(int(c * .35) for c in B.dark))
    a = ease(lt / .55)
    cx, cy = W / 2, 720 * k
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    for i in range(28):
        ang = i / 28 * math.tau + lt * .35
        L = (700 + 160 * math.sin(i * 1.7 + lt * 3)) * k * a
        w = .05
        rd.polygon([(cx, cy), (cx + L * math.cos(ang - w), cy + L * math.sin(ang - w)), (cx + L * math.cos(ang + w), cy + L * math.sin(ang + w))],
                   fill=(B.primary if i % 2 else B.accent) + (int(70 * a),))
    im.paste(rays.filter(ImageFilter.GaussianBlur(10 * k)), (0, 0), rays.filter(ImageFilter.GaussianBlur(10 * k)))
    rng = np.random.default_rng(int(lt * 12))
    lg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lg)
    for i in range(5):
        ang = rng.uniform(0, math.tau)
        R = rng.uniform(320, 520) * k * a
        ld.line(bolt(rng, cx, cy, cx + R * math.cos(ang), cy + R * math.sin(ang), 26 * k), fill=B.accent + (230,), width=max(2, int(5 * k)))
    im.paste(lg.filter(ImageFilter.GaussianBlur(1.5)), (0, 0), lg.filter(ImageFilter.GaussianBlur(1.5)))
    em = crest(B, 260 * k * (0.6 + .4 * a), glow=a, t=lt)
    im.paste(em, (int(cx - em.width / 2), int(cy - em.height / 2)), em)
    d = ImageDraw.Draw(im)
    fw = font("head", int(40 * k))
    tag = "Z E R O"
    d.text(((W - d.textlength(tag, font=fw)) / 2, 300 * k - 30 * k * (1 - a)), tag, font=fw, fill=ZERO_CYAN)
    title = s.get("caption", f"Meet {B.hero}.")
    f = font("serif", int(104 * k))
    tw = d.textlength(title, font=f)
    d.text(((W - tw) / 2, 1090 * k + 40 * k * (1 - a)), title, font=f, fill=(255, 255, 255), stroke_width=max(2, int(5 * k)), stroke_fill=(0, 0, 0))
    sub = s.get("sub", B.hero_line)
    fs = font("bold", int(42 * k))
    for i, ln in enumerate(wrap(d, sub, fs, W - 180 * k)):
        sw = d.textlength(ln, font=fs)
        d.text(((W - sw) / 2, 1230 * k + i * 54 * k), ln, font=fs, fill=B.accent)
    return im


def aura(B, im, lt):
    """Hero scenes: brand-colored HUD corners, an edge glow and a few rising sparks, so Jarvis feels present in the shot."""
    W, H, k = B.W, B.H, B.k
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(ov)
    m, L, w = 46 * k, 90 * k, max(2, int(5 * k))
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        o.line((x, y, x + sx * L, y), fill=B.accent + (200,), width=w)
        o.line((x, y, x, y + sy * L), fill=B.accent + (200,), width=w)
    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rectangle((0, 0, W, H), outline=B.primary + (110,), width=int(26 * k))
    ov.alpha_composite(edge.filter(ImageFilter.GaussianBlur(22 * k)))
    rng = np.random.default_rng(7)
    for i in range(22):
        x0, sp, ph = rng.uniform(0, W), rng.uniform(80, 220) * k, rng.uniform(0, 10)
        y = H - ((lt * sp + ph * 120 * k) % (H * .55)) - 40 * k
        r = rng.uniform(2, 5) * k
        o.ellipse((x0 - r, y - r, x0 + r, y + r), fill=B.accent + (int(160 * rng.uniform(.4, 1)),))
    im.paste(ov, (0, 0), ov)


def card(B, im, y, title, body, a):
    """Hero notification, slides in with a brand glow."""
    if a <= 0 or not body:
        return
    k, W = B.k, B.W
    x, w, h = 70 * k, W - 140 * k, 170 * k
    y = (y - 60 * (1 - a)) * k
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x - 8 * k, y - 8 * k, x + w + 8 * k, y + h + 8 * k), radius=44 * k, fill=B.accent + (90,))
    glow = glow.filter(ImageFilter.GaussianBlur(16 * k))
    im.paste(glow, (0, 0), glow)
    c = Image.new("RGBA", im.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(c)
    cd.rounded_rectangle((x, y, x + w, y + h), radius=38 * k, fill=B.dark + (238,), outline=B.accent + (255,), width=max(2, int(3 * k)))
    em = crest(B, 46 * k, glow=.8)
    c.paste(em, (int(x + 75 * k - em.width / 2), int(y + h / 2 - em.height / 2)), em)
    cd.text((x + 150 * k, y + 30 * k), title, font=font("bold", int(40 * k)), fill=B.accent + (255,))
    for i, ln in enumerate(wrap(cd, body, font("reg", int(32 * k)), w - 190 * k)[:2]):
        cd.text((x + 150 * k, y + 84 * k + i * 40 * k), ln, font=font("reg", int(32 * k)), fill=(235, 240, 245, 255))
    cd.text((x + w - 90 * k, y + 32 * k), "now", font=font("reg", int(28 * k)), fill=(160, 170, 180, 255))
    im.paste(c, (0, 0), c)


def end_frame(B, lt):
    W, H, k, e = B.W, B.H, B.k, B.end
    im = Image.new("RGB", (W, H), B.dark)
    d = ImageDraw.Draw(im)
    a = ease(lt / .6)
    f = font("serif", int(92 * k))
    y = 300 * k + 40 * k * (1 - a)
    for ln in wrap(d, e.get("headline", f"Get your own {B.hero}."), f, W - 140 * k):
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill=(255, 255, 255), stroke_width=max(2, int(4 * k)), stroke_fill=(0, 0, 0))
        y += 104 * k
    cy, r = y + 220 * k, int(170 * k)
    if B.face or B.logo:
        src = Image.open(B.face or B.logo).convert("RGB")
        face = ImageOps.fit(src, (2 * r, 2 * r), centering=(.5, .38))
        mask = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * r, 2 * r), fill=255)
        d.ellipse((W / 2 - r - 8 * k, cy - r - 8 * k, W / 2 + r + 8 * k, cy + r + 8 * k), fill=B.primary)
        im.paste(face, (int(W / 2 - r), int(cy - r)), mask)
    else:
        em = crest(B, r * 1.3, glow=1, t=lt)
        im.paste(em, (int(W / 2 - em.width / 2), int(cy - em.height / 2)), em)
    y = cy + r + 40 * k
    for txt, ff, col in ((B.person, font("bold", int(50 * k)), (255, 255, 255)), (B.role, font("reg", int(38 * k)), (170, 176, 186))):
        if txt:
            d.text((W / 2 - d.textlength(txt, font=ff) / 2, y), txt, font=ff, fill=col)
            y += 62 * k
    sub = e.get("sub")
    if sub:
        fs = font("serif", int(48 * k))
        y += 30 * k
        for ln in wrap(d, sub, fs, W - 160 * k):
            d.text(((W - d.textlength(ln, font=fs)) / 2, y), ln, font=fs, fill=(255, 255, 255))
            y += 58 * k
    cta = e.get("cta") or (f"DM {B.handle}" if B.handle else None)
    if cta:
        fc = font("head", int(46 * k))
        tw = d.textlength(cta, font=fc)
        x0 = (W - tw) / 2 - 30 * k
        d.rounded_rectangle((x0, y + 30 * k, x0 + tw + 60 * k, y + 30 * k + 82 * k), radius=41 * k, fill=B.primary)
        d.text((x0 + 30 * k, y + 46 * k), cta, font=fc, fill=B.dark)
        y += 150 * k
    if B.site:
        fsite = font("bold", int(40 * k))
        d.text(((W - d.textlength(B.site, font=fsite)) / 2, y), B.site, font=fsite, fill=(255, 255, 255))
    lock = Image.new("RGBA", (W, int(120 * k)), (0, 0, 0, 0))
    lg = ImageDraw.Draw(lock)
    fp = font("bold", int(28 * k))
    txt = "POWERED BY"
    tw = lg.textlength(txt, font=fp)
    fz = font("head", int(40 * k))
    zw = lg.textlength("ZERO", font=fz)
    total = tw + 16 * k + 44 * k + 10 * k + zw
    x0 = (W - total) / 2
    lg.text((x0, 42 * k), txt, font=fp, fill=(150, 160, 175, 255))
    zero_mark(lg, x0 + tw + 16 * k + 22 * k, 56 * k, 20 * k)
    lg.text((x0 + tw + 16 * k + 54 * k, 32 * k), "ZERO", font=fz, fill=(255, 255, 255, 255))
    im.paste(lock, (0, int(H - 170 * k)), lock)
    d.rectangle((60 * k, 94 * k, 68 * k, 128 * k), fill=B.primary)
    d.text((80 * k, 90 * k), B.name.upper(), font=font("head", int(34 * k)), fill=(255, 255, 255))
    return im


# ---------------------------------------------------------------- sound
def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(float)


_sfx = {}


def sfx(name):
    if name not in _sfx:
        p = os.path.join(HERE, "assets", "sfx", f"{name}.wav")
        if not os.path.exists(p):
            fail(f"sound effect not found: {p}")
        _sfx[name] = load_audio(p)
    return _sfx[name]


def vibrate(dur):
    t = np.arange(int(SR * dur)) / SR
    motor = np.sin(2 * np.pi * 165 * t) + .35 * np.sin(2 * np.pi * 330 * t) + .15 * np.sin(2 * np.pi * 495 * t)
    env = np.convolve(((t % .5) < .32).astype(float), np.ones(220) / 220, "same")
    return .12 * (motor + np.random.default_rng(3).standard_normal(len(t)) * .25) * env


def build_audio(B, path):
    a = np.zeros(int(SR * (B.total + .5)))

    def add(sig, at, gain=1.0):
        i = int(max(0, at) * SR)
        a[i:i + len(sig)] += (sig * gain)[:len(a) - i]

    first_reveal = True
    for i, s in enumerate(B.scenes):
        t0, kind, dur = s["start"], s["kind"], s["dur"]
        if i == 0:
            add(sfx("hook"), 0, .8)
        elif kind == "problem":
            add(sfx("wtight"), t0 - .35, .45)
        cue = s.get("sound")
        if cue == "phone":  # buzzing phone with missed-call dings stacking up
            add(vibrate(min(2.6, dur - .3)), t0 + .25)
            for j, n in enumerate(("ding1", "ding2", "ding3", "ding4")[:max(1, int(dur / .8))]):
                add(sfx(n), t0 + .5 + j * .75, .5)
        elif cue == "ringtone":
            for j, n in enumerate(("E5", "G5", "B5", "G5") * 3):
                if .5 + j * .26 < dur:
                    add(sfx(f"mar_{n}"), t0 + .5 + j * .26, .22)
        elif cue == "buzz":
            add(vibrate(1.8), t0 + .4)
        if kind == "reveal" and first_reveal:
            first_reveal = False
            add(sfx("riser"), t0 - 2.8, .45)
            add(sfx("revswell"), t0 - .9, .5)
            add(sfx("thump"), t0 - .1, .8)
            add(sfx("subdrop"), t0, .6)
            add(sfx("shimmer"), t0 + .2, .35)
        if kind == "hero":
            add(sfx("swish"), t0 - .25, .4)
            for c in s.get("cards", []):
                add(sfx("card"), t0 + c.get("at", .4), .45)
            if s.get("finale"):
                add(sfx("kick"), t0, .7)
    add(sfx("sting"), B.end_start, .6)

    voice = np.zeros_like(a)
    for v in B.voice:
        where = v.get("scene", 0)
        at = (B.end_start if where == "end" else B.scenes[where]["start"]) + v.get("offset", 0)
        sig = load_audio(v["path"])
        sig *= .16 / max(1e-6, np.sqrt((sig ** 2).mean()))
        i = int(at * SR)
        voice[i:i + len(sig)] += sig[:len(voice) - i]
    env = np.convolve((np.abs(voice) > .01).astype(float), np.ones(int(SR * .15)) / int(SR * .15), "same")
    a = a * (1 - .65 * np.clip(env * 3, 0, 1)) + voice
    a = np.tanh(a * 1.1) / np.tanh(1.1)
    a *= .89 / max(1e-6, np.abs(a).max())
    pcm = (a * 32000).astype(np.int16)
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", path], input=pcm.tobytes(), check=True)


# ---------------------------------------------------------------- main
def render(B):
    os.makedirs(os.path.dirname(B.out) or ".", exist_ok=True)
    wav = B.out.replace(".mp4", "_audio.wav")
    build_audio(B, wav)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{B.W}x{B.H}", "-r", str(FPS), "-i", "-",
                            "-i", wav, "-c:v", "libx264", "-preset", "veryfast" if B.preview else "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", B.out], stdin=subprocess.PIPE)
    for s in B.scenes:
        n = round(s["dur"] * FPS)
        frames = clip_reader(B, s) if s["kind"] != "reveal" else None
        for i in range(n):
            lt = i / FPS
            if s["kind"] == "reveal":
                im = reveal_frame(B, s, lt)
            else:
                im = next(frames).copy()
                if s["kind"] == "hero":
                    aura(B, im, lt)
                    for j, c in enumerate(s.get("cards", [])):
                        card(B, im, c.get("y", 1150 - 190 * (len(s["cards"]) - 1 - j)), c.get("title", B.hero), c.get("body"), ease((lt - c.get("at", .4)) / .4))
                shade_band(B, im)
                caption(B, ImageDraw.Draw(im), s.get("caption", ""), lt, s["dur"])
            enc.stdin.write(im.tobytes())
    for i in range(round(B.end_dur * FPS)):
        enc.stdin.write(end_frame(B, i / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    os.remove(wav)
    print(f"{B.out}  ({B.total:.1f} s, {B.W}x{B.H})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief")
    ap.add_argument("--preview", action="store_true", help="fast 540x960 render with short scenes and no voice")
    args = ap.parse_args()
    render(Brief(args.brief, args.preview))
