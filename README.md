# pyANSI / PNG2ANSI

`PNG2ANSI.py` converts raster images into classic, 80-column-compatible CP437
ANSI artwork. It emits only the standard 16 Windows Terminal foreground
colours and eight classic background colours, plus a PNG preview rendered from
the same cells.

The converter is the reference implementation for the offline
`PNG2ANSI-web` port. It intentionally excludes UTF-8/true-colour output, SAUCE
metadata, terminal playback helpers, and image-specific drawing overlays.

## Install

Python 3.10 or newer is recommended.

```powershell
python -m pip install -r requirements.txt
```

The repository includes the exact DejaVu Sans Mono font used for glyph fitting
and previews, so output is deterministic across supported platforms.

## Convert an image

```powershell
python PNG2ANSI.py image.png
```

This creates `image.ans` and `image.ans.png`. The defaults are 80×40 cells,
photographic fitting, and the full printable CP437 vocabulary.

Common examples:

```powershell
# Sparse industrial treatment
python PNG2ANSI.py image.png --style industrial --vocabulary industrial-sparse

# Reusable JSON profile with a command-line override
python PNG2ANSI.py image.png --config profile.json --contrast 1.2

# Derive one combined glyph vocabulary from several ANSI references
python PNG2ANSI.py image.png --style industrial `
  --reference-ansi reference-a.ans --reference-ansi reference-b.ans

# Write the effective defaults without converting an image
python PNG2ANSI.py --write-config profile.json
```

Configuration precedence is built-in defaults, then `--config`, then explicit
command-line options. Unknown JSON keys, invalid enums, and out-of-range values
are errors rather than being silently ignored.

## Workflow

1. Choose `photographic` for colour/coverage fidelity or `industrial` for
   sparse edge, texture, highlight, and accent control.
2. Start with a built-in vocabulary: `full-cp437`, `ascii`, `box-block`,
   `industrial-sparse`, or `industrial-dense`.
3. Optionally supply any number of ANSI references. When references are
   present, their frequency-ordered CP437 union replaces the built-in set.
4. Adjust preprocessing through CLI flags or a versioned JSON profile.
5. Inspect the PNG preview and display the `.ans` in an 80-column-compatible
   viewer.

Every public setting is documented in [PARAMETERS.md](PARAMETERS.md). The JSON
shape is defined by [png2ansi.schema.json](png2ansi.schema.json).

## Troubleshooting

- `ModuleNotFoundError`: install `requirements.txt` with the same Python used
  to run the converter.
- Wrapped or distorted output: use an 80-column terminal/viewer, or set the
  terminal width to the configured `canvas.columns`.
- Literal metadata at the bottom: PNG2ANSI never writes SAUCE metadata.
- Unexpected glyphs: choose a narrower built-in vocabulary or supply one or
  more reference ANSI files.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests generate synthetic images in temporary directories; no example artwork
is committed.

## License

Code is MIT licensed. The bundled DejaVu font has its own license in
`assets/FONT-LICENSE.txt`.
