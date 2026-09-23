# -*- coding: utf-8 -*-
"""Core logic tests (no GUI)."""

from __future__ import annotations

import importlib.util
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("json_lab_main", ROOT / "main.py")
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestJson(unittest.TestCase):
    def test_format_and_minify(self) -> None:
        raw = '{"b":1,"a":"中文"}'
        pretty = mod.format_json_text(raw, 2)
        self.assertIn('"a"', pretty)
        self.assertIn("中文", pretty)
        self.assertEqual(mod.minify_json_text("  { \"x\": [1,2] }  "), '{"x":[1,2]}')

    def test_invalid_json_raises(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            mod.format_json_text("{", 2)

    def test_folds(self) -> None:
        pretty = mod.format_json_text('{"a":{"b":[1,2]},"c":true}', 2)
        folds = mod.analyze_json_folds(pretty)
        self.assertGreaterEqual(len(folds), 2)
        for start, end in folds.items():
            self.assertGreater(end, start)


class TestTimestamp(unittest.TestCase):
    def test_detect_unit(self) -> None:
        self.assertEqual(mod.detect_ts_unit(1726732200), "s")
        self.assertEqual(mod.detect_ts_unit(1726732200000), "ms")
        self.assertEqual(mod.detect_ts_unit(1726732200000000), "μs")

    def test_roundtrip(self) -> None:
        sec = 1726732200
        dt = mod.ts_to_dt(sec, "s")
        self.assertEqual(mod.dt_to_ts(dt, "s"), sec)
        self.assertEqual(mod.dt_to_ts(dt, "ms"), sec * 1000)
        dt_ms = mod.ts_to_dt(sec * 1000, "ms")
        self.assertAlmostEqual(dt_ms.timestamp(), sec, places=2)

    def test_parse_human_time(self) -> None:
        d = mod.parse_human_time("2026-09-20 12:30:00")
        self.assertIsInstance(d, datetime)
        d2 = mod.parse_human_time("2026-09-20T12:30:00Z")
        self.assertIsNotNone(d2.tzinfo)
        self.assertEqual(d2.utcoffset(), timezone.utc.utcoffset(None))
        with self.assertRaises(ValueError):
            mod.parse_human_time("not-a-date")


if __name__ == "__main__":
    unittest.main()
