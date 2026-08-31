from __future__ import annotations

import argparse
import collections
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
except ModuleNotFoundError as error:
    missing = "Pillow" if error.name == "PIL" else error.name or "a dependency"
    print(
        f"Missing {missing}. Install dependencies with:\n"
        f"  {sys.executable} -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2) from None


ESC = "\x1b["
ANSI_BYTES = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|[78]|[ -/]*[@-~])")
ROOT = Path(__file__).resolve().parent
DEFAULT_FONT = ROOT / "assets" / "DejaVuSansMono.ttf"
GLYPH_SHORTLIST = 32
MAX_WORK_UNITS = 125_000_000

WINDOWS_ANSI = np.array(
    [
        (12, 12, 12), (197, 15, 31), (19, 161, 14), (193, 156, 0),
        (0, 55, 218), (136, 23, 152), (58, 150, 221), (204, 204, 204),
        (118, 118, 118), (231, 72, 86), (22, 198, 12), (249, 241, 165),
        (59, 120, 255), (180, 0, 158), (97, 214, 214), (242, 242, 242),
    ],
    dtype=np.float32,
)

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 2,
    "style": "photographic",
    "vocabulary": "full-cp437",
    "canvas": {
        "columns": 80,
        "rows": 40,
        "cell_width": 8,
        "cell_height": 16,
        "sample_width": 4,
        "sample_height": 8,
        "font_size": 14,
        "resampler": "lanczos",
    },
    "image": {
        "brightness": 1.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "gamma": 1.0,
        "sharpness": 1.18,
    },
    "fit": {
        "foreground_candidates": 6,
        "background_candidates": 5,
    },
    "derez": {
        "enabled": False,
        "width": 160,
        "height": 160,
    },
    "nl_filter": {
        "enabled": False,
        "mode": "edge-enhancement",
        "radius": 1.0,
        "alpha": 0.9,
    },
    "industrial": {
        "structure_blur": 0.85,
        "texture_blur": 1.85,
        "edge_threshold": 11.0,
        "edge_range": 57.0,
        "texture_threshold": 24.0,
        "texture_range": 62.0,
        "highlight_threshold": 138.0,
        "highlight_range": 110.0,
        "highlight_exponent": 2.2,
        "accent_luminance_scale": 145.0,
        "edge_weight": 0.92,
        "texture_weight": 0.18,
        "highlight_weight": 0.05,
        "accent_weight": 0.70,
        "sparsity_threshold": 0.14,
        "sparsity_range": 0.86,
        "ink_exponent": 0.92,
        "saturation_threshold": 0.10,
        "saturation_range": 0.34,
    },
}

RANGES: dict[tuple[str, str], tuple[float, float]] = {
    ("canvas", "columns"): (16, 512),
    ("canvas", "rows"): (8, 512),
    ("canvas", "cell_width"): (4, 32),
    ("canvas", "cell_height"): (8, 64),
    ("canvas", "sample_width"): (1, 16),
    ("canvas", "sample_height"): (1, 32),
    ("canvas", "font_size"): (4, 64),
    ("image", "brightness"): (0, 4),
    ("image", "contrast"): (0, 4),
    ("image", "saturation"): (0, 4),
    ("image", "gamma"): (0.1, 4),
    ("image", "sharpness"): (0, 4),
    ("fit", "foreground_candidates"): (1, 12),
    ("fit", "background_candidates"): (1, 8),
    ("derez", "width"): (16, 2048),
    ("derez", "height"): (16, 2048),
    ("nl_filter", "radius"): (0.33, 1),
    ("nl_filter", "alpha"): (0, 1),
    ("industrial", "structure_blur"): (0, 8),
    ("industrial", "texture_blur"): (0, 12),
    ("industrial", "edge_threshold"): (0, 255),
    ("industrial", "edge_range"): (0.001, 255),
    ("industrial", "texture_threshold"): (0, 255),
    ("industrial", "texture_range"): (0.001, 255),
    ("industrial", "highlight_threshold"): (0, 255),
    ("industrial", "highlight_range"): (0.001, 255),
    ("industrial", "highlight_exponent"): (0.1, 8),
    ("industrial", "accent_luminance_scale"): (1, 255),
    ("industrial", "edge_weight"): (0, 4),
    ("industrial", "texture_weight"): (0, 4),
    ("industrial", "highlight_weight"): (0, 4),
    ("industrial", "accent_weight"): (0, 4),
    ("industrial", "sparsity_threshold"): (0, 0.99),
    ("industrial", "sparsity_range"): (0.001, 1),
    ("industrial", "ink_exponent"): (0.1, 8),
    ("industrial", "saturation_threshold"): (0, 1),
    ("industrial", "saturation_range"): (0.001, 1),
}

INT_FIELDS = {
    ("canvas", "columns"), ("canvas", "rows"),
    ("canvas", "cell_width"), ("canvas", "cell_height"),
    ("canvas", "sample_width"), ("canvas", "sample_height"),
    ("canvas", "font_size"),
    ("fit", "foreground_candidates"), ("fit", "background_candidates"),
    ("derez", "width"), ("derez", "height"),
}

BOOL_FIELDS = {("derez", "enabled"), ("nl_filter", "enabled")}

SPARSE_CHARS = " _─═│▐▀~\"▌║▄-∙█╫.=┐/╤j\\≡╞╥≤`├πΓ╡Hⁿ]¬|}'┬■√÷%:┤╨╪Æτ╒╕└┘µ"
DENSE_CHARS = (
    SPARSE_CHARS
    + "░▒▓╔╗╚╝╬╦╩╠╣╧╪╫╭╮╯╰≈≥«»⌠⌡φΩΣ₧,![0123456789abcdefghijklnopqrstuvwxyz"
)


def _cp437_unique(text: str) -> list[str]:
    result: list[str] = []
    for char in text:
        try:
            char.encode("cp437")
        except UnicodeEncodeError:
            continue
        if char not in result:
            result.append(char)
    return result


def built_in_vocabulary(name: str) -> list[str]:
    if name == "full-cp437":
        raw = bytes(range(0x20, 0x7F)) + bytes(range(0x7F, 0x100))
        return list(dict.fromkeys(raw.decode("cp437")))
    if name == "ascii":
        return list(bytes(range(0x20, 0x7F)).decode("ascii"))
    if name == "box-block":
        return _cp437_unique(" .,:;+-=/\\_|" + bytes(range(0xB0, 0xE0)).decode("cp437"))
    if name == "industrial-sparse":
        return _cp437_unique(SPARSE_CHARS)
    if name == "industrial-dense":
        return _cp437_unique(DENSE_CHARS)
    raise ValueError(f"unknown vocabulary: {name}")


def strip_sauce(data: bytes) -> bytes:
    if len(data) < 128 or data[-128:-121] != b"SAUCE00":
        return data
    record = data[-128:]
    comments = record[104]
    end = len(data) - 128
    if comments:
        comment_size = 5 + comments * 64
        start = end - comment_size
        if start >= 0 and data[start:start + 5] == b"COMNT":
            end = start
    if end and data[end - 1] == 0x1A:
        end -= 1
    return data[:end]


def reference_vocabulary(paths: Iterable[Path]) -> list[str]:
    counts: collections.Counter[int] = collections.Counter()
    for path in paths:
        plain = ANSI_BYTES.sub(b"", strip_sauce(path.read_bytes()))
        counts.update(value for value in plain if value >= 0x20)
    ordered = [0x20]
    ordered.extend(value for value, _ in counts.most_common() if value != 0x20)
    return [bytes((value,)).decode("cp437") for value in ordered]


def merge_config(base: dict[str, Any], update: dict[str, Any], path: str = "") -> None:
    for key, value in update.items():
        if key not in base:
            raise ValueError(f"unknown configuration key: {path}{key}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{path}{key} must be an object")
            merge_config(base[key], value, f"{path}{key}.")
        else:
            base[key] = value


def migrate_config(update: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(update, dict):
        raise ValueError("configuration root must be an object")
    migrated = copy.deepcopy(update)
    version = migrated.get("schema_version", 1)
    if version == 1:
        migrated["schema_version"] = 2
    elif version != 2:
        raise ValueError("schema_version must be 1 or 2")
    return migrated


def validate_config(config: dict[str, Any]) -> None:
    if config["schema_version"] != 2:
        raise ValueError("schema_version must be 2 after migration")
    if config["style"] not in {"photographic", "industrial"}:
        raise ValueError("style must be photographic or industrial")
    built_in_vocabulary(config["vocabulary"])
    if config["canvas"]["resampler"] not in {"nearest", "bilinear", "bicubic", "lanczos"}:
        raise ValueError("canvas.resampler must be nearest, bilinear, bicubic, or lanczos")
    if config["nl_filter"]["mode"] not in {
        "alpha-trimmed-mean", "optimal-estimation", "edge-enhancement"
    }:
        raise ValueError(
            "nl_filter.mode must be alpha-trimmed-mean, optimal-estimation, or edge-enhancement"
        )
    for field in BOOL_FIELDS:
        if not isinstance(config[field[0]][field[1]], bool):
            raise ValueError(f"{field[0]}.{field[1]} must be boolean")
    for field, (minimum, maximum) in RANGES.items():
        value = config[field[0]][field[1]]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field[0]}.{field[1]} must be numeric")
        if field in INT_FIELDS and not isinstance(value, int):
            raise ValueError(f"{field[0]}.{field[1]} must be an integer")
        if not minimum <= value <= maximum:
            raise ValueError(
                f"{field[0]}.{field[1]} must be between {minimum} and {maximum}"
            )
    if config["derez"]["width"] * config["derez"]["height"] > 4_194_304:
        raise ValueError("derez.width × derez.height must not exceed 4,194,304 pixels")


def resampler(name: str) -> Image.Resampling:
    return {
        "nearest": Image.Resampling.NEAREST,
        "bilinear": Image.Resampling.BILINEAR,
        "bicubic": Image.Resampling.BICUBIC,
        "lanczos": Image.Resampling.LANCZOS,
    }[name]


def nl_filter_array(
    pixels: np.ndarray, mode: str, radius: float, alpha: float
) -> np.ndarray:
    """Apply a bounded seven-sample GIMP/pnmnlfilt-style RGB filter."""
    source = np.asarray(pixels, dtype=np.float32)
    if source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("NL Filter expects an RGB raster")
    pad = np.pad(source, ((1, 1), (1, 1), (0, 0)), mode="edge")
    center = pad[1:-1, 1:-1]
    neighbours = (
        center,
        pad[:-2, 1:-1], pad[2:, 1:-1],
        pad[1:-1, :-2], pad[1:-1, 2:],
        pad[:-2, :-2], pad[2:, 2:],
    )
    radius_mix = np.float32(np.clip((radius - 1.0 / 3.0) / (2.0 / 3.0), 0, 1))
    samples = np.stack(
        [center + (sample - center) * radius_mix for sample in neighbours], axis=0
    )
    if mode == "alpha-trimmed-mean":
        ordered = np.sort(samples, axis=0)
        cut = float(alpha) * 3.0
        whole = int(np.floor(cut))
        fraction = cut - whole
        weights = np.ones(7, dtype=np.float32)
        if whole:
            weights[:whole] = 0
            weights[7 - whole:] = 0
        if fraction and whole < 3:
            weights[whole] = 1 - fraction
            weights[6 - whole] = 1 - fraction
        result = np.sum(ordered * weights[:, None, None, None], axis=0) / weights.sum()
    elif mode == "optimal-estimation":
        mean = samples.mean(axis=0)
        variance = np.mean((samples - mean) ** 2, axis=0)
        noise = (float(alpha) * 64.0) ** 2
        keep = variance / np.maximum(variance + noise, 1e-8)
        result = mean + keep * (center - mean)
    elif mode == "edge-enhancement":
        mean = samples.mean(axis=0)
        result = center + float(alpha) * (center - mean)
    else:
        raise ValueError(f"unknown NL Filter mode: {mode}")
    return np.uint8(np.clip(np.rint(result), 0, 255))


def apply_nl_filter(image: Image.Image, config: dict[str, Any]) -> Image.Image:
    values = config["nl_filter"]
    filtered = nl_filter_array(
        np.asarray(image.convert("RGB")), values["mode"], values["radius"], values["alpha"]
    )
    return Image.fromarray(filtered, "RGB")


def preprocess_source(image: Image.Image, config: dict[str, Any]) -> Image.Image:
    values = config["image"]
    result = image.convert("RGB")
    canvas = config["canvas"]
    if config["derez"]["enabled"]:
        width = min(config["derez"]["width"], result.width)
        height = min(config["derez"]["height"], result.height)
        result = result.resize((width, height), resampler(canvas["resampler"]))
    elif config["nl_filter"]["enabled"]:
        result = result.resize(
            (canvas["columns"] * canvas["sample_width"], canvas["rows"] * canvas["sample_height"]),
            resampler(canvas["resampler"]),
        )
    if config["nl_filter"]["enabled"]:
        result = apply_nl_filter(result, config)
    result = ImageEnhance.Brightness(result).enhance(values["brightness"])
    result = ImageEnhance.Contrast(result).enhance(values["contrast"])
    result = ImageEnhance.Color(result).enhance(values["saturation"])
    result = ImageEnhance.Sharpness(result).enhance(values["sharpness"])
    if values["gamma"] != 1.0:
        inverse = 1.0 / values["gamma"]
        table = [round(((value / 255.0) ** inverse) * 255) for value in range(256)]
        result = result.point(table * 3)
    return result


def render_glyph_masks(
    chars: Iterable[str], font_path: Path, cell_width: int, cell_height: int, font_size: int
) -> tuple[list[str], np.ndarray]:
    font = ImageFont.truetype(str(font_path), font_size)
    kept: list[str] = []
    masks: list[np.ndarray] = []
    signatures: set[bytes] = set()
    for char in chars:
        tile = Image.new("L", (cell_width, cell_height), 0)
        draw = ImageDraw.Draw(tile)
        bbox = draw.textbbox((0, 0), char, font=font)
        width = bbox[2] - bbox[0]
        x = (cell_width - width) // 2 - bbox[0]
        draw.text((x, 0), char, font=font, fill=255)
        array = np.asarray(tile, dtype=np.float32) / 255.0
        signature = np.rint(array * 31).astype(np.uint8).tobytes()
        if signature in signatures:
            continue
        signatures.add(signature)
        kept.append(char)
        masks.append(array)
    return kept, np.stack(masks)


def low_masks(masks: np.ndarray, width: int, height: int) -> np.ndarray:
    result = []
    for mask in masks:
        small = Image.fromarray(np.uint8(mask * 255), "L").resize(
            (width, height), Image.Resampling.LANCZOS
        )
        result.append(np.asarray(small, dtype=np.float32) / 255.0)
    return np.stack(result).reshape(len(result), -1)


def image_cells(image: Image.Image, config: dict[str, Any]) -> np.ndarray:
    canvas = config["canvas"]
    columns, rows = canvas["columns"], canvas["rows"]
    sw, sh = canvas["sample_width"], canvas["sample_height"]
    fitted = image.resize((columns * sw, rows * sh), resampler(canvas["resampler"]))
    pixels = np.asarray(fitted, dtype=np.float32)
    return (
        pixels.reshape(rows, sh, columns, sw, 3)
        .transpose(0, 2, 1, 3, 4)
        .reshape(rows * columns, sw * sh, 3)
    )


def continuous_seed(
    cells: np.ndarray, masks: np.ndarray, shortlist_size: int = GLYPH_SHORTLIST
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean_m = masks.mean(axis=1)
    centered_m = masks - mean_m[:, None]
    ss_m = np.sum(centered_m * centered_m, axis=1)
    foreground = np.empty((len(cells), 3), dtype=np.float32)
    background = np.empty((len(cells), 3), dtype=np.float32)
    shortlist_size = min(shortlist_size, len(masks))
    shortlists = np.empty((len(cells), shortlist_size), dtype=np.int32)
    for start in range(0, len(cells), 192):
        block = cells[start:start + 192] / 255.0
        mean_p = block.mean(axis=1)
        centered_p = block - mean_p[:, None, :]
        total = np.sum(centered_p * centered_p, axis=(1, 2))
        covariance = np.einsum("bnc,gn->bgc", centered_p, centered_m, optimize=True)
        explained = np.sum(covariance * covariance, axis=2) / np.maximum(ss_m[None], 1e-8)
        scores = total[:, None] - explained
        selected = np.argmin(scores, axis=1)
        partial = np.argpartition(scores, shortlist_size - 1, axis=1)[:, :shortlist_size]
        partial_scores = np.take_along_axis(scores, partial, axis=1)
        shortlists[start:start + len(block)] = np.take_along_axis(
            partial, np.argsort(partial_scores, axis=1, kind="stable"), axis=1
        )
        selected_cov = covariance[np.arange(len(block)), selected]
        beta = selected_cov / np.maximum(ss_m[selected, None], 1e-8)
        bg = mean_p - beta * mean_m[selected, None]
        foreground[start:start + len(block)] = np.clip(bg + beta, 0, 1) * 255
        background[start:start + len(block)] = np.clip(bg, 0, 1) * 255
    return foreground, background, shortlists


def workload_units(config: dict[str, Any], glyph_count: int) -> int:
    canvas = config["canvas"]
    cells = canvas["columns"] * canvas["rows"]
    samples = canvas["sample_width"] * canvas["sample_height"]
    base = glyph_count * (samples * 3 + 12)
    if config["style"] == "industrial":
        fitting = glyph_count * 15 * 3
    else:
        fitting = (
            min(GLYPH_SHORTLIST, glyph_count)
            * config["fit"]["foreground_candidates"]
            * config["fit"]["background_candidates"]
            * 3
        )
    return int(cells * (base + fitting))


def validate_workload(config: dict[str, Any], glyph_count: int) -> int:
    units = workload_units(config, glyph_count)
    if units > MAX_WORK_UNITS:
        raise ValueError(
            f"estimated workload {units:,} exceeds the safe limit {MAX_WORK_UNITS:,}; "
            "reduce columns, rows, sample grid, vocabulary size, or colour candidates"
        )
    return units


def fit_photographic(
    image: Image.Image, masks_hi: np.ndarray, config: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    canvas, fitting = config["canvas"], config["fit"]
    masks = low_masks(masks_hi, canvas["sample_width"], canvas["sample_height"])
    cells = image_cells(image, config)
    seed_fg, seed_bg, shortlists = continuous_seed(cells, masks)
    mask_sum = masks.sum(axis=1)
    mask_square_sum = np.sum(masks * masks, axis=1)
    chosen = np.empty(len(cells), dtype=np.int32)
    fg_index = np.empty(len(cells), dtype=np.uint8)
    bg_index = np.empty(len(cells), dtype=np.uint8)
    for index, cell in enumerate(cells):
        fg_options = np.argsort(np.sum((WINDOWS_ANSI - seed_fg[index]) ** 2, axis=1))[
            : fitting["foreground_candidates"]
        ]
        bg_options = np.argsort(np.sum((WINDOWS_ANSI[:8] - seed_bg[index]) ** 2, axis=1))[
            : fitting["background_candidates"]
        ]
        pair_fg = np.repeat(fg_options, len(bg_options))
        pair_bg = np.tile(bg_options, len(fg_options))
        colours_fg, colours_bg = WINDOWS_ANSI[pair_fg], WINDOWS_ANSI[pair_bg]
        differences = colours_fg - colours_bg
        glyph_options = shortlists[index]
        shortlisted_masks = masks[glyph_options]
        # Expand ||p - (b + m(f-b))||² into reusable colour/mask terms.
        # This avoids allocating pair × glyph × sample × RGB reconstructions.
        pixel_sum = cell.sum(axis=0)
        mask_pixel_dot = shortlisted_masks @ cell
        constant = (
            np.sum(cell * cell)
            + len(cell) * np.sum(colours_bg * colours_bg, axis=1)
            - 2 * (colours_bg @ pixel_sum)
        )
        error = (
            constant[:, None]
            + 2
            * np.sum(colours_bg * differences, axis=1)[:, None]
            * mask_sum[glyph_options][None]
            + np.sum(differences * differences, axis=1)[:, None]
            * mask_square_sum[glyph_options][None]
            - 2 * (differences @ mask_pixel_dot.T)
        )
        pair, glyph = np.unravel_index(np.argmin(error), error.shape)
        chosen[index], fg_index[index], bg_index[index] = (
            glyph_options[glyph], pair_fg[pair], pair_bg[pair]
        )
    shape = (canvas["rows"], canvas["columns"])
    return chosen.reshape(shape), fg_index.reshape(shape), bg_index.reshape(shape)


def fit_industrial(
    image: Image.Image, masks_hi: np.ndarray, config: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    canvas, values = config["canvas"], config["industrial"]
    columns, rows = canvas["columns"], canvas["rows"]
    sw, sh = canvas["sample_width"], canvas["sample_height"]
    masks = low_masks(masks_hi, sw, sh)
    sampled = image.resize((columns * sw, rows * sh), resampler(canvas["resampler"]))
    rgb = np.asarray(sampled, dtype=np.float32)
    luminance = rgb @ np.array((0.2126, 0.7152, 0.0722), dtype=np.float32)
    gray = Image.fromarray(np.uint8(np.clip(luminance, 0, 255)), "L")
    structure = np.asarray(gray.filter(ImageFilter.GaussianBlur(values["structure_blur"])), dtype=np.float32)
    blurred = np.asarray(gray.filter(ImageFilter.GaussianBlur(values["texture_blur"])), dtype=np.float32)
    gradient_y, gradient_x = np.gradient(structure)
    edge = np.hypot(gradient_x, gradient_y)
    local = np.abs(luminance - blurred)
    maximum, minimum = rgb.max(axis=2), rgb.min(axis=2)
    saturation = (maximum - minimum) / np.maximum(maximum, 1.0)
    edge_ink = np.clip((edge - values["edge_threshold"]) / values["edge_range"], 0, 1)
    texture_ink = np.clip((local - values["texture_threshold"]) / values["texture_range"], 0, 1)
    highlight_ink = np.clip(
        (luminance - values["highlight_threshold"]) / values["highlight_range"], 0, 1
    ) ** values["highlight_exponent"]
    accent_ink = saturation * np.clip(luminance / values["accent_luminance_scale"], 0, 1)
    ink = np.clip(
        values["edge_weight"] * edge_ink
        + values["texture_weight"] * texture_ink
        + values["highlight_weight"] * highlight_ink
        + values["accent_weight"] * accent_ink,
        0,
        1,
    )
    ink = np.clip(
        (ink - values["sparsity_threshold"]) / values["sparsity_range"], 0, 1
    ) ** values["ink_exponent"]
    hue = rgb / np.maximum(maximum[..., None], 1.0)
    mix = np.clip(
        (saturation - values["saturation_threshold"]) / values["saturation_range"], 0, 1
    )[..., None]
    stylized = ((1 - mix) + mix * hue) * (ink * 255)[..., None]
    cells = (
        stylized.reshape(rows, sh, columns, sw, 3)
        .transpose(0, 2, 1, 3, 4)
        .reshape(rows * columns, sw * sh * 3)
    )
    choices = np.arange(1, 16, dtype=np.int32)
    candidates = (masks[None, :, :, None] * WINDOWS_ANSI[choices, None, None]).reshape(
        len(choices) * len(masks), -1
    )
    distances = (
        np.sum(cells * cells, axis=1)[:, None]
        + np.sum(candidates * candidates, axis=1)[None]
        - 2 * (cells @ candidates.T)
    )
    best = np.argmin(distances, axis=1)
    colour_slot, glyph = np.divmod(best, len(masks))
    shape = (rows, columns)
    return (
        glyph.reshape(shape).astype(np.int32),
        choices[colour_slot].reshape(shape).astype(np.uint8),
        np.zeros(shape, dtype=np.uint8),
    )


def write_ansi(
    path: Path, glyphs: list[str], chosen: np.ndarray, foreground: np.ndarray, background: np.ndarray
) -> None:
    output = bytearray()
    current: tuple[int, int] | None = None
    for y in range(chosen.shape[0]):
        for x in range(chosen.shape[1]):
            fg, bg = int(foreground[y, x]), int(background[y, x])
            if (fg, bg) != current:
                bright = 1 if fg >= 8 else 22
                output.extend(f"\x1b[{bright};{30 + fg % 8};{40 + bg}m".encode("ascii"))
                current = (fg, bg)
            output.extend(glyphs[int(chosen[y, x])].encode("cp437"))
    output.extend(b"\x1b[0m")
    path.write_bytes(output)


def write_preview(
    path: Path, masks: np.ndarray, chosen: np.ndarray, foreground: np.ndarray, background: np.ndarray
) -> None:
    rows, columns = chosen.shape
    cell_height, cell_width = masks.shape[1:]
    canvas = np.empty((rows * cell_height, columns * cell_width, 3), dtype=np.uint8)
    for y in range(rows):
        for x in range(columns):
            mask = masks[int(chosen[y, x])][..., None]
            fg, bg = WINDOWS_ANSI[foreground[y, x]], WINDOWS_ANSI[background[y, x]]
            tile = bg + mask * (fg - bg)
            canvas[y * cell_height:(y + 1) * cell_height, x * cell_width:(x + 1) * cell_width] = np.uint8(np.clip(np.rint(tile), 0, 255))
    Image.fromarray(canvas, "RGB").save(path, optimize=True)


CLI_FIELDS = {
    "columns": ("canvas", "columns"), "rows": ("canvas", "rows"),
    "cell_width": ("canvas", "cell_width"), "cell_height": ("canvas", "cell_height"),
    "sample_width": ("canvas", "sample_width"), "sample_height": ("canvas", "sample_height"),
    "font_size": ("canvas", "font_size"), "resampler": ("canvas", "resampler"),
    "brightness": ("image", "brightness"), "contrast": ("image", "contrast"),
    "saturation": ("image", "saturation"), "gamma": ("image", "gamma"),
    "sharpness": ("image", "sharpness"),
    "foreground_candidates": ("fit", "foreground_candidates"),
    "background_candidates": ("fit", "background_candidates"),
    "derez_width": ("derez", "width"), "derez_height": ("derez", "height"),
    "nl_mode": ("nl_filter", "mode"), "nl_radius": ("nl_filter", "radius"),
    "nl_alpha": ("nl_filter", "alpha"),
    **{key: ("industrial", key) for key in DEFAULT_CONFIG["industrial"]},
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Convert a raster image to classic CP437 ANSI art.")
    result.add_argument("source", type=Path, nargs="?")
    result.add_argument("output", type=Path, nargs="?")
    result.add_argument("--preview", type=Path)
    result.add_argument("--config", type=Path)
    result.add_argument("--write-config", type=Path)
    result.add_argument("--font", type=Path, default=DEFAULT_FONT)
    result.add_argument("--style", choices=("photographic", "industrial"))
    result.add_argument("--vocabulary", choices=("full-cp437", "ascii", "box-block", "industrial-sparse", "industrial-dense"))
    result.add_argument("--reference-ansi", action="append", type=Path, default=[])
    result.add_argument("--list-vocabularies", action="store_true")
    result.add_argument("--derez", action=argparse.BooleanOptionalAction, default=None)
    result.add_argument("--nl-filter", action=argparse.BooleanOptionalAction, default=None)
    for name, field in CLI_FIELDS.items():
        default = DEFAULT_CONFIG[field[0]][field[1]]
        value_type = int if field in INT_FIELDS else str if isinstance(default, str) else float
        result.add_argument("--" + name.replace("_", "-"), dest=name, type=value_type)
    return result


def effective_config(args: argparse.Namespace) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if args.config:
        loaded = json.loads(args.config.read_text(encoding="utf-8"))
        merge_config(config, migrate_config(loaded))
    if args.style is not None:
        config["style"] = args.style
    if args.vocabulary is not None:
        config["vocabulary"] = args.vocabulary
    for name, field in CLI_FIELDS.items():
        value = getattr(args, name)
        if value is not None:
            config[field[0]][field[1]] = value
    if args.derez is not None:
        config["derez"]["enabled"] = args.derez
    if args.nl_filter is not None:
        config["nl_filter"]["enabled"] = args.nl_filter
    validate_config(config)
    return config


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.list_vocabularies:
        print("\n".join(("full-cp437", "ascii", "box-block", "industrial-sparse", "industrial-dense")))
        return 0
    try:
        config = effective_config(args)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"configuration error: {error}", file=sys.stderr)
        return 2
    if args.write_config:
        args.write_config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        if args.source is None:
            return 0
    if args.source is None:
        print("source image is required unless only --write-config is used", file=sys.stderr)
        return 2
    if not args.font.is_file():
        print(f"font not found: {args.font}", file=sys.stderr)
        return 2
    output = args.output or args.source.with_suffix(".ans")
    preview = args.preview or Path(str(output) + ".png")
    try:
        source = preprocess_source(Image.open(args.source), config)
        chars = reference_vocabulary(args.reference_ansi) if args.reference_ansi else built_in_vocabulary(config["vocabulary"])
        canvas = config["canvas"]
        glyphs, masks = render_glyph_masks(
            chars, args.font, canvas["cell_width"], canvas["cell_height"], canvas["font_size"]
        )
        units = validate_workload(config, len(glyphs))
        if config["style"] == "industrial":
            chosen, foreground, background = fit_industrial(source, masks, config)
        else:
            chosen, foreground, background = fit_photographic(source, masks, config)
        write_ansi(output, glyphs, chosen, foreground, background)
        write_preview(preview, masks, chosen, foreground, background)
    except (OSError, ValueError) as error:
        print(f"conversion error: {error}", file=sys.stderr)
        return 1
    print(f"ANSI: {output}")
    print(f"preview: {preview}")
    print(f"canvas: {config['canvas']['columns']} x {config['canvas']['rows']}")
    print(f"style: {config['style']}")
    print(f"vocabulary: {'references' if args.reference_ansi else config['vocabulary']} ({len(glyphs)} masks)")
    print(f"estimated work: {units:,} units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
