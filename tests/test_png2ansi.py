from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PNG2ANSI.py"
SPEC = importlib.util.spec_from_file_location("png2ansi", SCRIPT)
assert SPEC and SPEC.loader
PNG2ANSI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PNG2ANSI
SPEC.loader.exec_module(PNG2ANSI)


def synthetic(path: Path) -> None:
    image = Image.new("RGB", (96, 64), (8, 12, 18))
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, 91, 59), outline=(220, 225, 214), width=2)
    draw.ellipse((12, 10, 44, 42), outline=(55, 210, 204), width=3)
    draw.line((48, 50, 86, 14), fill=(232, 70, 50), width=3)
    draw.rectangle((55, 25, 82, 48), fill=(30, 155, 45))
    image.save(path)


class PNG2ANSITests(unittest.TestCase):
    def test_default_cli_and_classic_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.png"
            synthetic(source)
            result = subprocess.run([sys.executable, str(SCRIPT), str(source)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            ansi = source.with_suffix(".ans").read_bytes()
            self.assertTrue(Path(str(source.with_suffix(".ans")) + ".png").is_file())
            self.assertNotIn(b"SAUCE00", ansi)
            self.assertNotRegex(ansi, rb"\x1b\[(?:38|48);")
            plain = re.sub(rb"\x1b\[[0-9;]*m", b"", ansi)
            self.assertEqual(len(plain), 80 * 40)

    def test_config_precedence_and_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "sample.png"
            synthetic(source)
            profile = directory / "profile.json"
            profile.write_text(json.dumps({"canvas": {"columns": 32, "rows": 16}}), encoding="utf-8")
            effective = directory / "effective.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--config", str(profile), "--columns", "40", "--write-config", str(effective)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(effective.read_text(encoding="utf-8"))
            self.assertEqual(data["canvas"]["columns"], 40)
            self.assertEqual(data["canvas"]["rows"], 16)

    def test_unknown_and_out_of_range_values_fail(self) -> None:
        config = json.loads(json.dumps(PNG2ANSI.DEFAULT_CONFIG))
        with self.assertRaisesRegex(ValueError, "unknown configuration key"):
            PNG2ANSI.merge_config(config, {"mystery": 1})
        config = json.loads(json.dumps(PNG2ANSI.DEFAULT_CONFIG))
        config["industrial"]["sparsity_range"] = 0
        with self.assertRaisesRegex(ValueError, "sparsity_range"):
            PNG2ANSI.validate_config(config)

    def test_multiple_reference_union(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.ans"
            second = Path(directory) / "b.ans"
            first.write_bytes(b"\x1b[31mAAAA" + "░".encode("cp437"))
            second.write_bytes(b"\x1b[36mBB" + "▓".encode("cp437"))
            vocab = PNG2ANSI.reference_vocabulary([first, second])
            self.assertEqual(vocab[0], " ")
            self.assertLess(vocab.index("A"), vocab.index("B"))
            self.assertIn("░", vocab)
            self.assertIn("▓", vocab)

    def test_deterministic_fixture_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.png"
            output = Path(directory) / "fixture.ans"
            synthetic(source)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), str(output), "--columns", "24", "--rows", "12", "--vocabulary", "box-block"],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            self.assertEqual(digest, "2e39bb11a3065268f14a99ecb44467d89be26f0660f674a7088251e4c40cb0eb")

    def test_v1_profile_migrates_and_cli_precedence_includes_new_filters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            profile = directory / "v1.json"
            profile.write_text(json.dumps({
                "schema_version": 1,
                "fit": {"foreground_candidates": 4, "background_candidates": 4},
            }), encoding="utf-8")
            effective = directory / "v2.json"
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--config", str(profile),
                "--derez", "--derez-width", "96", "--derez-height", "80",
                "--nl-filter", "--nl-mode", "optimal-estimation",
                "--nl-radius", "0.8", "--nl-alpha", "0.25",
                "--foreground-candidates", "7", "--write-config", str(effective),
            ], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(effective.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["fit"], {"foreground_candidates": 7, "background_candidates": 4})
            self.assertEqual(data["derez"], {"enabled": True, "width": 96, "height": 80})
            self.assertEqual(data["nl_filter"]["mode"], "optimal-estimation")

    def test_nl_filter_modes_and_derez_bounds(self) -> None:
        flat = np.full((7, 7, 3), 91, dtype=np.uint8)
        for mode in ("alpha-trimmed-mean", "optimal-estimation", "edge-enhancement"):
            filtered = PNG2ANSI.nl_filter_array(flat, mode, 1.0, 0.9)
            np.testing.assert_array_equal(filtered, flat)
        impulse = flat.copy()
        impulse[3, 3] = 240
        edge = PNG2ANSI.nl_filter_array(impulse, "edge-enhancement", 1.0, 0.9)
        self.assertGreater(int(edge[3, 3, 0]), int(impulse[3, 3, 0]))
        smooth = PNG2ANSI.nl_filter_array(impulse, "alpha-trimmed-mean", 1.0, 1.0)
        self.assertEqual(int(smooth[3, 3, 0]), 91)
        for derez, nl_filter, expected in (
            (False, False, (32, 24)),
            (True, False, (32, 24)),
            (False, True, (320, 320)),
            (True, True, (32, 24)),
        ):
            config = json.loads(json.dumps(PNG2ANSI.DEFAULT_CONFIG))
            config["derez"].update({"enabled": derez, "width": 160, "height": 160})
            config["nl_filter"]["enabled"] = nl_filter
            result = PNG2ANSI.preprocess_source(Image.new("RGB", (32, 24)), config)
            self.assertEqual(result.size, expected)

    def test_candidate_safety_and_workload_budget(self) -> None:
        config = json.loads(json.dumps(PNG2ANSI.DEFAULT_CONFIG))
        default_units = PNG2ANSI.workload_units(config, 218)
        old_baseline = 80 * 40 * (218 * (4 * 8 * 3 + 12) + 218 * 3 * 3 * 3)
        self.assertLessEqual(default_units, old_baseline)
        config["fit"].update({"foreground_candidates": 12, "background_candidates": 8})
        self.assertLessEqual(PNG2ANSI.workload_units(config, 218), old_baseline * 1.5)
        PNG2ANSI.validate_workload(config, 218)
        config["canvas"].update({"columns": 512, "rows": 512})
        with self.assertRaisesRegex(ValueError, "safe limit"):
            PNG2ANSI.validate_workload(config, 218)
        invalid = json.loads(json.dumps(PNG2ANSI.DEFAULT_CONFIG))
        invalid["fit"]["background_candidates"] = 12
        with self.assertRaisesRegex(ValueError, "background_candidates"):
            PNG2ANSI.validate_config(invalid)


if __name__ == "__main__":
    unittest.main()
