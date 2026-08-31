"""Manual 80x40 candidate-fitting benchmark used for release validation.

Run from the repository root with ``python tests/benchmark_candidates.py``.
Timing assertions intentionally live outside the unit suite because shared CI
hosts are noisy; the deterministic workload ratios remain unit-tested.
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import PNG2ANSI as converter  # noqa: E402


def synthetic_source() -> Image.Image:
    y, x = np.mgrid[0:512, 0:640]
    image = np.stack(
        (
            (x * 255 // 639),
            (y * 255 // 511),
            ((x ^ y) & 255),
        ),
        axis=2,
    ).astype(np.uint8)
    return Image.fromarray(image, "RGB")


def old_full_glyph_fit(image: Image.Image, masks_hi: np.ndarray, config: dict) -> None:
    """Reproduce the v0.1 full-glyph 3x3 inner search for comparison."""
    canvas = config["canvas"]
    masks = converter.low_masks(masks_hi, canvas["sample_width"], canvas["sample_height"])
    cells = converter.image_cells(image, config)
    seed_fg, seed_bg, _ = converter.continuous_seed(cells, masks)
    for index, cell in enumerate(cells):
        foregrounds = np.argsort(
            np.sum((converter.WINDOWS_ANSI - seed_fg[index]) ** 2, axis=1)
        )[:3]
        backgrounds = np.argsort(
            np.sum((converter.WINDOWS_ANSI[:8] - seed_bg[index]) ** 2, axis=1)
        )[:3]
        pair_fg = np.repeat(foregrounds, len(backgrounds))
        pair_bg = np.tile(backgrounds, len(foregrounds))
        colours_fg = converter.WINDOWS_ANSI[pair_fg]
        colours_bg = converter.WINDOWS_ANSI[pair_bg]
        reconstruction = (
            colours_bg[:, None, None, :]
            + masks[None, :, :, None]
            * (colours_fg - colours_bg)[:, None, None, :]
        )
        np.sum((reconstruction - cell[None, None]) ** 2, axis=(2, 3)).argmin()


def timed(label: str, callback) -> float:
    started = time.perf_counter()
    callback()
    elapsed = time.perf_counter() - started
    print(f"{label:24} {elapsed:8.3f} s")
    return elapsed


def main() -> int:
    config = copy.deepcopy(converter.DEFAULT_CONFIG)
    glyphs, masks = converter.render_glyph_masks(
        converter.built_in_vocabulary("full-cp437"),
        converter.DEFAULT_FONT,
        config["canvas"]["cell_width"],
        config["canvas"]["cell_height"],
        config["canvas"]["font_size"],
    )
    image = converter.preprocess_source(synthetic_source(), config)
    print(f"80x40, {len(glyphs)} distinct glyph masks")
    baseline = timed("v0.1 full-glyph 3x3", lambda: old_full_glyph_fit(image, masks, config))
    passed = True
    for foregrounds, backgrounds in ((4, 4), (6, 5), (8, 6), (12, 8)):
        current = copy.deepcopy(config)
        current["fit"]["foreground_candidates"] = foregrounds
        current["fit"]["background_candidates"] = backgrounds
        elapsed = timed(
            f"v0.2 shortlist {foregrounds}x{backgrounds}",
            lambda current=current: converter.fit_photographic(image, masks, current),
        )
        ratio = elapsed / baseline
        print(f"{'runtime ratio':24} {ratio:8.3f} x")
        if (foregrounds, backgrounds) == (6, 5):
            passed &= ratio <= 1.0
        if (foregrounds, backgrounds) == (12, 8):
            passed &= ratio <= 1.5
    if not passed:
        print("candidate runtime acceptance threshold exceeded", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
