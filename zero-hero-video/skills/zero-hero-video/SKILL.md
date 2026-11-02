---
name: zero-hero-video
description: >-
  Makes ZERO hero reels for trade businesses (electricians, HVAC, plumbers, any service company): a struggling-owner story,
  a superhero reveal where Zero bursts out of the client's shield, Zero handling calls on screen, and a branded call to action.
  Use when asked for a Zero video, a "Jarvis-style" reel, an AI receptionist ad for a trade business, or a new client version of the Zero reel.
license: MIT
compatibility: >-
  Needs Python 3 with numpy and Pillow, and ffmpeg. New voice lines and new footage need Higgsfield or another generator.
---

# ZERO hero video

ZERO is Apex Zero Studio's AI hero: it answers calls, books jobs, logs leads in the client's own CRM and finds new customers.
In every video it lives *inside the client's brand*: the Zero mark glows inside a shield drawn in the client's colors.
Never call it Jarvis: Marvel owns JARVIS for assistant software (US 4737881).

## Make a video

1. **Brief.** Copy `template/briefs/apex_zero_electrician.json`. Set brand name, initials, `primary`, `accent`, `dark`, face or logo, handle, site.
   Write one caption per scene; wrap 1-2 key words in `*asterisks*` to color them.
2. **Footage.** 5 struggle shots + 3 hero shots, vertical. Use `template/SHOT_PROMPTS.md`. Stills work (slow zoom); clips work better.
3. **Cards.** Only describe things the client's system really does. No invented stats, reviews or results.
4. **Voice.** Bundled: `z1` "Hey. I'm Zero.", `j2` "I answer every call while you work.", `j3` "I book the job, log it in your CRM,
   and find your next customer.", `j4` "You do the work. I'll handle the rest.", `z_tag` "Zero missed calls. Zero lost jobs."
   New lines: Higgsfield `generate_audio`, model `seed_audio`, preset voice **Jasper** (`a7b8abe9-47f1-553e-a9df-87945a7e5bc8`).
   Transcribe each line back before using it.
5. **Preview** `python3 render.py briefs/X.json --preview` (about 20 s), look at frames from the reveal, a hero scene and the end card.
6. **Render** `python3 render.py briefs/X.json` (about 3-4 min for 38 s). Check `ffprobe` shows h264 + aac at 1080x1920.

## Lessons from the first reels

- **Watermarks.** Free-plan Luma/Higgsfield output carries a watermark. Never paint, crop or blur it out; use paid-plan downloads
  or watermark-free sources.
- **Paid ads.** Meta rejects ads showing nicotine or alcohol, even as props. Keep a prop-free cut for ads.
- **Sound.** Synthesized beeps sound cheap. Use the bundled earshot effects (`assets/sfx`); the renderer places them by scene type.
- **Voice choice.** Match a reference voice by measuring pitch and expressiveness against candidate voices, not by name.
  Jasper matched the "Dessa" demo the client liked (about 87 Hz vs 90 Hz).
- **Props on moving footage.** Track a patch of the shirt with OpenCV optical flow, put the real shirt pixels back in front of the
  prop, check close-up crops at the start, middle and end of each shot, and skip shots where the subject turns away.
- **Cloud sessions.** Many CDNs are blocked; the Higgsfield sandbox has internet. To move a file out of it, pack the bytes into a
  grayscale PNG, return it with `image_paths`, and unpack it locally (verify with md5).
- **Delivery.** Send finished videos one by one (not zipped), with a one-line caption on what changed.
