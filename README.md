# LUMARA — The Poster for a Place That Isn't There

[![make.fun](https://img.shields.io/badge/make.fun-bounty-blue)](https://make.fun)

Entry for the make.fun bounty **the-poster-for-a-place-that-i-2-20261121-0539**:
a program that writes one travel poster for a place that does not exist.

## What it is

**Lumara** is a fictional island with a single white lighthouse on a rocky
islet, seen at golden hour over a turquoise sea. The program renders the
poster deterministically:

1. `scene.png` — a flat vector-style scene painted fresh in the build session
   (golden-hour sun, sea, one lighthouse, birds). It carries no text.
2. `main.py` (Python 3.13, standard library only) resamples the scene to
   1024×1024, paints a deep-teal name band across the top, and renders the
   place name **LUMARA** in it with a procedural geometric stroke font —
   no font files, no system fonts, no network.
3. The result is written to `/output/entry.png` as an 8-bit RGB PNG.

Only the place name appears as text — no quotes, no ratings, no other copy.

## Run

```sh
python3 main.py            # writes /output/entry.png
OUTPUT_PATH=./entry.png python3 main.py   # or anywhere else
```

No dependencies, no network, no randomness, no clock: two runs produce
byte-identical output (verified: identical SHA-256 across runs), in ~6 s,
well inside the 60 s wall budget. Output is 1024×1024 and under 1 MiB.

## Files

- `main.py` — the whole program (PNG reader, bilinear resampler, stroke
  font, PNG writer; stdlib only)
- `scene.png` — the scene asset, made in this build session
- `README.md`, `LICENSE` (MIT)
