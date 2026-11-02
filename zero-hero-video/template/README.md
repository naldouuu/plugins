# ZERO hero template

Turns one small brief file into a 30–40 second vertical reel:
**the struggling tradesman → Zero bursts out of the brand's crest like a superhero → Zero handles the calls → your ending.**

Zero is drawn as the hero living inside the brand: a shield crest in the brand's colors with its initials, an energy-burst reveal,
glowing corner frames whenever he's working, and notification cards stamped with the crest.
The ZERO mark (a zero ring with a lightning bolt) always sits inside the client's shield, and every end card carries "Powered by ZERO".
Logo files: `brand/`. The full brand book is kept privately (not in this repo). Add owner photos locally under `assets/` and point `brand.face` at them; they are not committed.

## Make a new video in 5 steps

1. **Get the footage.** 6–9 clips or images. Use the prompts in `SHOT_PROMPTS.md` in Luma or Higgsfield, or real job-site footage.
   Put them in `footage/<brand-name>/`.
2. **Copy a brief.** Duplicate `briefs/apex_electrician.json` (video clips) or `briefs/example_stills_hvac.json` (still images).
3. **Fill it in.** Brand name, 2 colors, captions, the Zero notification text, the ending. (Field list below.)
4. **Preview it (20 seconds):**
   ```
   python3 render.py briefs/your_brief.json --preview
   ```
5. **Render the real one (about 3 minutes):**
   ```
   python3 render.py briefs/your_brief.json
   ```
   The video lands in `output/`.

Needs: Python 3 with `numpy` and `Pillow` (`pip install numpy pillow`), and `ffmpeg`.

## The brief

```jsonc
{
  "output": "../output/name.mp4",
  "brand": {
    "name": "Summit Air Pros",       // shown on the end card
    "initials": "SA",                // goes on the hero crest (default: first letters of the name)
    "primary": "#E4572E",            // crest border, end-card button, edge glow
    "accent": "#7FD8FF",             // Zero energy color: rays, cards, corners
    "dark": "#101820",               // backgrounds
    "logo": "../assets/logo.png",    // optional, shown on the end card if there's no face
    "face": "../assets/owner.jpg",   // optional, round photo on the end card
    "person": "Owner Name",          // optional
    "role": "Company",               // optional
    "handle": "@handle", "site": "site.com"
  },
  "hero": { "name": "Zero", "tagline": "The hero living inside your business." },
  "scenes": [ ... ],                 // in order, see below
  "voice": [ { "file": "../assets/voice/j1.wav", "scene": 5, "offset": 0.3 } ],
  "end": { "dur": 4.5, "headline": "Get your own Zero.", "sub": "One line.", "cta": "DM @handle" }
}
```

### Scenes

| kind | what it is | fields |
|---|---|---|
| `problem` (default) | the struggle shots | `src`, `in` (start second in the clip), `dur`, `caption`, `sound`: `phone` / `ringtone` / `buzz` |
| `reveal` | the superhero reveal card (no footage needed) | `dur`, `caption` ("Meet Zero."), `sub` |
| `hero` | Zero at work, with glowing frame | `src`, `in`, `dur`, `caption`, `cards`: `[{"at": 0.4, "body": "text"}]`, `finale: true` on the last one |

`src` can be a video (`.mp4`, `.mov`) or an image (`.jpg`, `.png`). Images get a slow zoom; `"zoom": "out"` reverses it.

### Captions

Wrap a word in asterisks to light it up in the brand's accent color: `"Zero answers *every* *call*."`

## Sound

Sound design is automatic: a hit on the first frame, whooshes into every cut, phone buzzes and dings where you set `sound`,
a riser and bass drop into the reveal, chimes on each Zero card, a kick on the finale and a sting on the end card.
All effects were made in code with earshot (MIT) and live in `assets/sfx/`.

Zero's voice comes from the `voice` list. The bundled lines are "Hey. I'm Zero." (z1) / "I answer every call while you work." /
"I book the job, log it in your CRM, and find your next customer." / "You do the work. I'll handle the rest." and "Zero missed calls. Zero lost jobs." (z_tag, put it on the end card with `"scene": "end"`).
For new lines, generate them with Higgsfield's `seed_audio` model and the **Jasper** voice, and add them to `assets/voice/`.
Background music and effects dip automatically while he talks.

## Rules that keep the ads honest

- Captions and Zero cards must describe things the system really does for that client.
- No made-up stats, reviews or results.
- Free-plan AI clips carry the generator's watermark. Download clean versions on a paid plan before posting; don't paint it out.
