"""Weekday counts and tendency verdicts are computed, not stored."""
import json
import shutil
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from codex_reset_tracker.analysis import (  # noqa: E402
    binomial_sf, evaluate_tendencies, likelihood, weekday_breakdown,
)
from codex_reset_tracker.cli import main  # noqa: E402
from codex_reset_tracker.store import Store  # noqa: E402
from codex_reset_tracker.timeutil import parse_ts  # noqa: E402

NOW = parse_ts("2026-10-17T10:30:00Z")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _load():
    store = Store(ROOT / "data")
    tendencies = json.loads((ROOT / "data" / "tendencies.json").read_text(encoding="utf-8"))["tendencies"]
    return store, tendencies


def _event(utc, *, status="confirmed", day_n=None, announce=None):
    confirm = {"utc": utc, "post_id": "1", "url": "https://x.com/thsottiaux/status/1",
               "author": "thsottiaux", "text": "reset", "taipei": utc}
    return {"status": status, "kind": "full", "day_n": day_n, "announce": announce,
            "confirm": confirm, "triggers": []}


class WeekdayTests(unittest.TestCase):
    def test_bundled_confirmed_pacific_matches_hand_count(self):
        store, _ = _load()
        report = weekday_breakdown(store.resets, NOW)
        confirmed = report["slices"]["all_time"]["confirmed"]
        self.assertEqual(confirmed["n"], 45)
        self.assertEqual(confirmed["America/Los_Angeles"],
                         {"Mon": 6, "Tue": 6, "Wed": 6, "Thu": 5, "Fri": 8, "Sat": 10, "Sun": 4})
        self.assertEqual(confirmed["Asia/Taipei"],
                         {"Mon": 3, "Tue": 6, "Wed": 7, "Thu": 6, "Fri": 5, "Sat": 7, "Sun": 11})
        self.assertEqual(sum(confirmed["hour_pacific"]), 45)
        self.assertEqual(confirmed["hour_pacific"][20], 6)
        self.assertEqual(confirmed["hour_pacific"][1], 0)

    def test_all_events_and_last_60_days(self):
        store, _ = _load()
        report = weekday_breakdown(store.resets, NOW)
        all_time = report["slices"]["all_time"]["all"]
        self.assertEqual(all_time["n"], 62)
        self.assertEqual(all_time["America/Los_Angeles"],
                         {"Mon": 10, "Tue": 9, "Wed": 10, "Thu": 8, "Fri": 11, "Sat": 10, "Sun": 4})
        recent = report["slices"]["last_60_days"]
        self.assertEqual(recent["since"], "2026-08-18T10:30:00Z")
        self.assertEqual(recent["confirmed"]["n"], 16)
        self.assertEqual(recent["confirmed"]["America/Los_Angeles"],
                         {"Mon": 2, "Tue": 2, "Wed": 2, "Thu": 2, "Fri": 4, "Sat": 3, "Sun": 1})
        self.assertEqual(recent["all"]["Asia/Taipei"]["Sun"], 3)

    def test_anchor_is_announce_then_confirm(self):
        # 2026-10-19T06:30Z is Sunday 23:30 PDT; the confirmation later that UTC day is Monday PT.
        announced = _event("2026-10-19T18:00:00Z", announce={"utc": "2026-10-19T06:30:00Z"})
        fallback = _event("2026-10-19T18:00:00Z", announce=None)
        report = weekday_breakdown([announced, fallback], NOW)
        counts = report["slices"]["all_time"]["confirmed"]["America/Los_Angeles"]
        self.assertEqual(counts["Sun"], 1)
        self.assertEqual(counts["Mon"], 1)
        self.assertEqual(sum(counts[d] for d in WEEKDAYS), 2)


class VerdictTests(unittest.TestCase):
    def test_binomial_upper_tail(self):
        self.assertAlmostEqual(binomial_sf(4, 5, 0.5), 0.1875, places=6)
        self.assertAlmostEqual(binomial_sf(0, 10, 0.2), 1.0, places=6)

    def test_seed_file_has_claims_and_no_stored_verdicts(self):
        raw = json.loads((ROOT / "data" / "tendencies.json").read_text(encoding="utf-8"))
        ids = [row["id"] for row in raw["tendencies"]]
        self.assertEqual(ids, [
            "monday_resets", "even_day_cadence", "morning_taipei",
            "outage_recovery_reset", "poteto_banter",
        ])
        for row in raw["tendencies"]:
            self.assertNotIn("verdict", row)
            self.assertIn(row["source"], ("community observation", "data"))
            self.assertTrue(row["claim"].strip())
        self.assertEqual(raw["tendencies"][0]["source"], "community observation")

    def test_bundled_verdicts(self):
        store, tendencies = _load()
        before = (ROOT / "data" / "tendencies.json").read_text(encoding="utf-8")
        rows = {r["id"]: r for r in evaluate_tendencies(tendencies, store.resets, store.signals, NOW)}
        self.assertEqual((ROOT / "data" / "tendencies.json").read_text(encoding="utf-8"), before)
        monday = rows["monday_resets"]
        self.assertEqual(monday["verdict"], "not supported")
        self.assertEqual((monday["k"], monday["n"]), (6, 45))
        self.assertEqual(monday["baseline_name"], "1/7")
        self.assertGreater(monday["p_value"], 0.05)
        self.assertFalse(monday["small_sample"])
        even = rows["even_day_cadence"]
        self.assertEqual(even["verdict"], "insufficient data")
        self.assertEqual((even["k"], even["n"]), (4, 5))
        morning = rows["morning_taipei"]
        self.assertEqual(morning["verdict"], "supported")
        self.assertEqual((morning["k"], morning["n"]), (35, 62))
        self.assertLess(morning["p_value"], 0.05)
        outage = rows["outage_recovery_reset"]
        self.assertEqual(outage["verdict"], "insufficient data")
        self.assertEqual((outage["k"], outage["n"]), (2, 3))
        banter = rows["poteto_banter"]
        self.assertEqual(banter["verdict"], "supported")
        self.assertEqual((banter["k"], banter["n"]), (10, 14))
        self.assertTrue(banter["small_sample"])

    def test_weekday_factor_only_when_supported(self):
        spec = {
            "id": "monday_resets",
            "claim": "Tibo tends to reset on Mondays",
            "source": "community observation",
            "test": {"kind": "weekday", "weekday": "Mon", "zone": "America/Los_Angeles",
                     "population": "confirmed", "window": "all_time"},
        }
        monday0 = datetime(2026, 1, 5, 18, tzinfo=timezone.utc)
        mondays = [_event((monday0 + timedelta(days=7 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")) for i in range(12)]
        supported = evaluate_tendencies([spec], mondays, [], parse_ts("2026-06-01T00:00:00Z"))
        self.assertEqual(supported[0]["verdict"], "supported")
        on_monday = likelihood(mondays, [], parse_ts("2026-03-30T18:00:00Z"), supported)
        on_tuesday = likelihood(mondays, [], parse_ts("2026-03-31T18:00:00Z"), supported)
        self.assertTrue(any("weekday tendency supported" in f["factor"] for f in on_monday["factors"]))
        self.assertAlmostEqual(on_monday["score"] - on_tuesday["score"], 0.10, places=2)
        self.assertFalse(any("weekday" in f["factor"] for f in on_tuesday["factors"]))

        tuesday0 = datetime(2026, 1, 6, 18, tzinfo=timezone.utc)
        tuesdays = [_event((tuesday0 + timedelta(days=7 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")) for i in range(12)]
        rejected = evaluate_tendencies([spec], tuesdays, [], parse_ts("2026-06-01T00:00:00Z"))
        self.assertEqual(rejected[0]["verdict"], "not supported")
        quiet = likelihood(tuesdays, [], parse_ts("2026-03-30T18:00:00Z"), rejected)
        self.assertFalse(any("weekday" in f["factor"] for f in quiet["factors"]))

    def test_real_data_does_not_apply_weekday_factor(self):
        store, tendencies = _load()
        rows = evaluate_tendencies(tendencies, store.resets, store.signals, NOW)
        lk = likelihood(store.resets, store.signals, NOW, rows)
        self.assertEqual(lk["score"], 0.41)
        self.assertFalse(any("weekday" in f["factor"] for f in lk["factors"]))

    def test_cli_prints_computed_verdicts(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--data-dir", str(ROOT / "data"), "--dry-run", "--now", "2026-10-17T10:30:00Z", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        by_id = {row["id"]: row["verdict"] for row in payload["stats"]["tendencies"]}
        self.assertEqual(by_id["monday_resets"], "not supported")
        self.assertEqual(by_id["morning_taipei"], "supported")
        self.assertEqual(payload["stats"]["weekday"]["slices"]["all_time"]["confirmed"]["America/Los_Angeles"]["Mon"], 6)

    def test_js_matches_python_on_bundled_data(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        store, tendencies = _load()
        expected = evaluate_tendencies(tendencies, store.resets, store.signals, NOW)
        report = weekday_breakdown(store.resets, NOW)
        script = r"""
const fs = require("fs");
const vm = require("vm");
const ctx = { console, globalThis: {} };
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync("docs/tendency.js", "utf8"), ctx);
const T = ctx.Tendency;
const load = p => fs.readFileSync(p, "utf8").trim().split(/\n/).map(JSON.parse);
const resets = load("data/resets.jsonl");
const signals = load("data/signals.jsonl");
const tendencies = JSON.parse(fs.readFileSync("data/tendencies.json", "utf8")).tendencies;
const now = Date.parse("2026-10-17T10:30:00Z");
const rows = T.evaluateTendencies(tendencies, resets, signals, now);
const wd = T.weekdayCounts(resets, { zone: "America/Los_Angeles", population: "confirmed", window: "all_time", now });
const recent = T.weekdayCounts(resets, { zone: "Asia/Taipei", population: "all", window: "last_60_days", now });
process.stdout.write(JSON.stringify({ rows, wd, recent }));
"""
        proc = subprocess.run([node, "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
        got = json.loads(proc.stdout)
        self.assertEqual(got["wd"]["counts"], report["slices"]["all_time"]["confirmed"]["America/Los_Angeles"])
        self.assertEqual(got["recent"]["counts"], report["slices"]["last_60_days"]["all"]["Asia/Taipei"])
        for row, js in zip(expected, got["rows"]):
            for key in ("id", "verdict", "k", "n", "share", "baseline", "baseline_name", "p_value", "small_sample"):
                self.assertEqual(js[key], row[key], f"{row['id']} {key}")


if __name__ == "__main__":
    unittest.main()
