# PNG2ANSI parameters

Schema version 2 is shared with PNG2ANSI-web. JSON names appear below; CLI
flags replace underscores with hyphens. Configuration precedence is defaults,
migrated JSON, then CLI. Version 1 profiles are accepted and gain the new
Derez/NL defaults automatically.

## Top level and canvas

| Setting | Default | Range / values | Visual effect | Cost and interactions |
| --- | ---: | --- | --- | --- |
| `style` | `photographic` | photographic, industrial | Chooses direct colour reconstruction or sparse structural ink. | Industrial ignores foreground/background candidate counts. |
| `vocabulary` | `full-cp437` | five built-ins | Controls available shapes. | Larger sets cost more; ANSI references replace this set. |
| `canvas.columns` | 80 | 16–512 | Horizontal ANSI detail. | Cost grows linearly and participates in the safe-work limit. |
| `canvas.rows` | 40 | 8–512 | Vertical ANSI detail. | Cost grows linearly and participates in the safe-work limit. |
| `canvas.cell_width` | 8 | 4–32 | Pixel width of each preview cell. | Changes font masks and PNG size, not ANSI cell count. |
| `canvas.cell_height` | 16 | 8–64 | Pixel height of each preview cell. | Changes font masks and PNG size. |
| `canvas.sample_width` | 4 | 1–16 | Horizontal samples fitted per cell. | Higher values retain detail but increase fitting work. |
| `canvas.sample_height` | 8 | 1–32 | Vertical samples fitted per cell. | Higher values retain detail but increase fitting work. |
| `canvas.font_size` | 14 | 4–64 | Rasterized glyph size. | Rebuilds masks; coordinate with cell dimensions. |
| `canvas.resampler` | `lanczos` | nearest, bilinear, bicubic, lanczos | Controls resize softness or pixelation. | Nearest suits deliberately blocky Derez; Lanczos is the photographic default. |

Repeated `--reference-ansi` inputs create a frequency-ordered CP437 union.
The converter rejects estimated work above 125,000,000 units with guidance to
reduce canvas size, sampling, vocabulary, or photographic candidates.

## Derez and NL Filter

| Setting | Default | Range / values | Visual effect | Cost and interactions |
| --- | ---: | --- | --- | --- |
| `derez.enabled` | false | boolean | Enables an exact intermediate raster before other adjustments. | Useful for suppressing details too fine for ANSI. |
| `derez.width` | 160 | 16–2048 | Intermediate pixel width. | Never exceeds source width; width×height may not exceed 4,194,304. |
| `derez.height` | 160 | 16–2048 | Intermediate pixel height. | Independent dimensions may intentionally alter aspect ratio. |
| `nl_filter.enabled` | false | boolean | Enables seven-sample nonlinear preprocessing. | Runs after Derez and before tonal controls. |
| `nl_filter.mode` | `edge-enhancement` | alpha-trimmed-mean, optimal-estimation, edge-enhancement | Despeckles, adaptively smooths, or sharpens local edges. | Alpha meaning depends on mode. |
| `nl_filter.radius` | 1.0 | 0.33–1 | Size/mix of the seven-sample neighbourhood. | 0.33 is nearly neutral; 1 uses the complete neighbourhood. |
| `nl_filter.alpha` | 0.9 | 0–1 | Trim amount, smoothing strength, or edge strength. | Edge 0.9 is intentionally strong; reduce it if halos dominate. |

If NL Filter is enabled without Derez, it operates on the bounded final
sampling raster. The modes process RGB channels independently: alpha-trimmed
mean moves from averaging toward a median, optimal estimation smooths low
variance areas while retaining edges, and edge enhancement increases local
contrast.

## Common image preprocessing

| Setting | Default | Range | Visual effect | Cost and interactions |
| --- | ---: | --- | --- | --- |
| `image.brightness` | 1.0 | 0–4 | Scales overall light. | Raise cautiously before highlights collapse to white. |
| `image.contrast` | 1.0 | 0–4 | Separates dark and light regions. | Often the most effective photographic control. |
| `image.saturation` | 1.0 | 0–4 | Changes hue intensity. | Industrial accent ink depends on saturation. |
| `image.gamma` | 1.0 | 0.1–4 | Adjusts midtones; above 1 brightens them. | More selective than brightness. |
| `image.sharpness` | 1.18 | 0–4 | Emphasizes detail before cell fitting. | Combine carefully with NL edge enhancement to avoid halos. |

## Photographic fitting

| Setting | Default | Range | Visual effect | Cost and interactions |
| --- | ---: | --- | --- | --- |
| `fit.foreground_candidates` | 6 | 1–12 | Searches more nearby foreground palette colours. | Multiplies background candidates; 32 glyph shapes are shortlisted per cell. |
| `fit.background_candidates` | 5 | 1–8 | Searches more of the eight legal background colours. | Values above 8 are invalid and web input clamps to 8. |

The `12×8` maximum remains inside the safe default-canvas budget because each
cell searches only its 32 best continuous-fit glyph shapes. Candidate counts
do not affect industrial mode.

## Industrial preprocessing

| Setting | Default | Range | Visual effect | Cost and interactions |
| --- | ---: | --- | --- | --- |
| `industrial.structure_blur` | 0.85 | 0–8 | Scale used to find major edges. | Larger values favour broad machinery outlines. |
| `industrial.texture_blur` | 1.85 | 0–12 | Scale used to separate local texture. | Larger values classify broader variation as texture. |
| `industrial.edge_threshold` | 11 | 0–255 | Edge strength where ink begins. | Lower values add structural lines and noise. |
| `industrial.edge_range` | 57 | 0.001–255 | Edge strength needed to reach full ink. | Smaller values create harder edges. |
| `industrial.texture_threshold` | 24 | 0–255 | Texture difference where ink begins. | Raise to remove grain. |
| `industrial.texture_range` | 62 | 0.001–255 | Texture normalization span. | Smaller values make remaining texture denser. |
| `industrial.highlight_threshold` | 138 | 0–255 | Luminance where highlight ink starts. | Lower values add broad bright fills. |
| `industrial.highlight_range` | 110 | 0.001–255 | Highlight transition span. | Smaller values saturate highlights sooner. |
| `industrial.highlight_exponent` | 2.2 | 0.1–8 | Curves highlight response. | Higher values confine highlight ink to peaks. |
| `industrial.accent_luminance_scale` | 145 | 1–255 | Brightness scale for coloured accents. | Lower values strengthen saturated colour marks. |
| `industrial.edge_weight` | 0.92 | 0–4 | Structural edge contribution. | Primary line-density control before sparsity. |
| `industrial.texture_weight` | 0.18 | 0–4 | Fine texture contribution. | Raise for gritty surfaces. |
| `industrial.highlight_weight` | 0.05 | 0–4 | Broad highlight contribution. | Usually kept low for sparse art. |
| `industrial.accent_weight` | 0.70 | 0–4 | Saturated colour contribution. | Raise for indicator lights and wiring. |
| `industrial.sparsity_threshold` | 0.14 | 0–0.99 | Removes weak combined ink. | Raise for more black space. |
| `industrial.sparsity_range` | 0.86 | 0.001–1 | Normalizes ink remaining above threshold. | Smaller values drive surviving marks to full strength. |
| `industrial.ink_exponent` | 0.92 | 0.1–8 | Curves final ink density. | Below 1 lifts faint marks; above 1 suppresses them. |
| `industrial.saturation_threshold` | 0.10 | 0–1 | Saturation where source hue starts appearing. | Raise for greyer output. |
| `industrial.saturation_range` | 0.34 | 0.001–1 | Width of grey-to-hue transition. | Smaller values make colour selection abrupt. |
