# PNG2ANSI parameters

All visual constants used by the converter are public. JSON names appear in
backticks; CLI flags use the same name with hyphens. Defaults form schema
version 1 and are also the parity target for PNG2ANSI-web.

## Top level

| JSON / CLI | Default | Values | Effect |
| --- | ---: | --- | --- |
| `style` / `--style` | `photographic` | `photographic`, `industrial` | Selects direct colour fitting or sparse structural preprocessing. |
| `vocabulary` / `--vocabulary` | `full-cp437` | Five built-ins | Selects the candidate glyph set when no references are supplied. |

Repeated `--reference-ansi` arguments replace the built-in vocabulary with the
frequency-ordered union extracted from those files.

## Canvas and rasterization

| JSON key | Default | Range/values | Effect |
| --- | ---: | --- | --- |
| `canvas.columns` | 80 | 16–512 | ANSI cells per row. |
| `canvas.rows` | 40 | 8–512 | ANSI rows. |
| `canvas.cell_width` | 8 | 4–32 | Preview/glyph-mask cell width in pixels. |
| `canvas.cell_height` | 16 | 8–64 | Preview/glyph-mask cell height in pixels. |
| `canvas.sample_width` | 4 | 1–16 | Source fitting samples per cell horizontally. |
| `canvas.sample_height` | 8 | 1–32 | Source fitting samples per cell vertically. |
| `canvas.font_size` | 14 | 4–64 | Bundled font rasterization size. |
| `canvas.resampler` | `lanczos` | nearest, bilinear, bicubic, lanczos | Source resize filter. |

## Common image preprocessing

| JSON key | Default | Range | Effect |
| --- | ---: | --- | --- |
| `image.brightness` | 1.0 | 0–4 | Overall source brightness. |
| `image.contrast` | 1.0 | 0–4 | Separation between light and dark values. |
| `image.saturation` | 1.0 | 0–4 | Source colour intensity before fitting. |
| `image.gamma` | 1.0 | 0.1–4 | Midtone response; values above one brighten midtones. |
| `image.sharpness` | 1.18 | 0–4 | Edge/detail emphasis before cell sampling. |

## Photographic fitting

| JSON key | Default | Range | Effect |
| --- | ---: | --- | --- |
| `fit.foreground_candidates` | 3 | 1–16 | Nearest foreground colours searched per cell. |
| `fit.background_candidates` | 3 | 1–8 | Nearest background colours searched per cell. |

## Industrial preprocessing

| JSON key | Default | Range | Effect |
| --- | ---: | --- | --- |
| `industrial.structure_blur` | 0.85 | 0–8 | Blur used before structural gradients. |
| `industrial.texture_blur` | 1.85 | 0–12 | Blur used to separate local texture. |
| `industrial.edge_threshold` | 11 | 0–255 | Minimum structural gradient. |
| `industrial.edge_range` | 57 | 0.001–255 | Edge normalization span. |
| `industrial.texture_threshold` | 24 | 0–255 | Minimum local texture difference. |
| `industrial.texture_range` | 62 | 0.001–255 | Texture normalization span. |
| `industrial.highlight_threshold` | 138 | 0–255 | Luminance where broad highlights begin. |
| `industrial.highlight_range` | 110 | 0.001–255 | Highlight normalization span. |
| `industrial.highlight_exponent` | 2.2 | 0.1–8 | Highlight response curve. |
| `industrial.accent_luminance_scale` | 145 | 1–255 | Brightness scale for saturated accents. |
| `industrial.edge_weight` | 0.92 | 0–4 | Structural edge contribution. |
| `industrial.texture_weight` | 0.18 | 0–4 | Fine texture contribution. |
| `industrial.highlight_weight` | 0.05 | 0–4 | Broad highlight contribution. |
| `industrial.accent_weight` | 0.70 | 0–4 | Saturated colour contribution. |
| `industrial.sparsity_threshold` | 0.14 | 0–0.99 | Ink removed before final fitting. |
| `industrial.sparsity_range` | 0.86 | 0.001–1 | Remaining ink normalization span. |
| `industrial.ink_exponent` | 0.92 | 0.1–8 | Final ink response curve. |
| `industrial.saturation_threshold` | 0.10 | 0–1 | Saturation where hue preservation begins. |
| `industrial.saturation_range` | 0.34 | 0.001–1 | Transition from grey to source hue. |

## Planned web controls

PNG2ANSI-web presents canvas, style, vocabulary, brightness, contrast,
saturation, gamma, sharpness, and sparsity in its basic panel. Every remaining
field appears in Advanced. Profile import/export uses this same schema, and
live previews debounce changes while preserving exact effective values.
