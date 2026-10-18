import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codex_reset_tracker.classifier import classify  # noqa: E402
from codex_reset_tracker.sources import load_file  # noqa: E402
from codex_reset_tracker.store import Store  # noqa: E402
from codex_reset_tracker.analysis import likelihood  # noqa: E402
from codex_reset_tracker.timeutil import campaign_day, parse_ts  # noqa: E402

RAW = ROOT / "data" / "raw" / "posts.json"


class ClassifierTests(unittest.TestCase):
    def t(self, text, author="thsottiaux", refs=None, ctx=None):
        return classify(text, author, refs, ctx).label

    def test_day_n_reset(self):
        self.assertEqual(self.t("Day 8/ Reset"), "reset_announced")
        self.assertEqual(self.t("The reports of my reset button being lost are greatly exaggerated\n\nDay 10/ Reset"), "reset_announced")

    def test_confirmations(self):
        self.assertEqual(self.t("Put the reset in the bag. All propagated."), "reset_confirmed")
        self.assertEqual(self.t("Resets all propagated. That will be all."), "reset_confirmed")
        self.assertEqual(self.t("Reset all propagated. Sweet dreams."), "reset_confirmed")

    def test_short_confirm_needs_context(self):
        self.assertEqual(self.t("Done and dusted"), "other")
        self.assertEqual(self.t("Done and dusted", refs=["1"], ctx={"1"}), "reset_confirmed")
        self.assertEqual(self.t("What would you like with your side of reset? It's done.", refs=["1"], ctx={"1"}), "reset_confirmed")
        self.assertEqual(self.t("Landing within the next 2 hours", refs=["1"], ctx={"1"}), "reset_announced")
        self.assertEqual(self.t("Landing sometime today by EOD PST", refs=["1"], ctx={"1"}), "reset_announced")
        self.assertEqual(self.t("Day 13/ Le limit reset"), "reset_announced")
        self.assertEqual(self.t("Done", refs=["1"], ctx={"1"}), "reset_confirmed")

    def test_improvement_not_reset(self):
        self.assertEqual(self.t("Day 12/\n\nWe've made improvements to Codex & Work that increase the effective usage you get."), "usage_improvement")
        self.assertEqual(self.t("Good plans are simple. I have one that should result in significantly more usage for everyone."), "usage_improvement")

    def test_negation(self):
        self.assertNotIn(self.t("Because usage on your primary dot is virtually unlimited at the moment, I can't really give a reset."),
                         ("reset_announced", "reset_confirmed"))

    def test_outage_recovery(self):
        self.assertEqual(self.t("We are aware that codex is down and are working hard to bring back normal service."), "outage")
        self.assertEqual(self.t("o yes… we’re back in action and we’ll reset usage limits for all paid users"), "reset_announced")

    def test_untrusted_cannot_confirm(self):
        self.assertNotIn(self.t("Usage limits have been reset for everyone", author="someone"), ("reset_confirmed", "reset_announced"))
        self.assertEqual(self.t("Did we just get a random Codex reset?", author="someone"), "reset_hint")

    def test_mirror_and_rivalry(self):
        self.assertEqual(self.t("✅ Codex reset confirmed", author="codex_resets"), "reset_confirmed")
        self.assertEqual(self.t("⚠️ Possible Codex reset by Oct 17, 05:00 UTC", author="codex_resets"), "reset_hint")
        self.assertEqual(self.t("me vs the reset guy", author="poteto"), "rivalry_hint")
        self.assertEqual(self.t("Can't argue with that, Let's break the cycle."), "reset_hint")


class DetectorTests(unittest.TestCase):
    def test_end_to_end_and_idempotent(self):
        posts = load_file(RAW)
        self.assertGreater(len(posts), 100)
        with tempfile.TemporaryDirectory() as d:
            st = Store(Path(d))
            st.ingest(posts)
            st.save()
            by_anchor = {e["event_id"]: e for e in st.resets}
            # Day 6 / 8 / 10 must be linked announce -> confirm with the right lags.
            for anchor, confirm, lag in (("x:2109045220411351517", "2109132167112782291", 5.76),
                                         ("x:2109812216212099456", "2109873287853707513", 4.04),
                                         ("x:2110595484180214059", "2110618732666257557", 1.54)):
                ev = by_anchor[anchor]
                self.assertEqual(ev["status"], "confirmed")
                self.assertEqual(ev["confirm"]["post_id"], confirm)
                self.assertAlmostEqual(ev["lag_hours"], lag, places=2)
            again = Store(Path(d))
            self.assertEqual(again.ingest(posts), [])

    def test_wrapped_connector_output(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.txt"
            f.write_text('note: saved\n{"data":[{"id":"2110595484180214059","author_id":"1953337039510003712",'
                         '"created_at":"2026-10-15T04:55:51.000Z","text":"Day 10/ Reset"}]}\nX reads left: 9\n')
            posts = load_file(f)
            self.assertEqual(posts[0]["author"], "thsottiaux")
            self.assertEqual(posts[0]["created_at"], "2026-10-15T04:55:51Z")

    def test_campaign_day(self):
        self.assertEqual(campaign_day(parse_ts("2026-10-15T04:55:51Z")), 10)
        self.assertEqual(campaign_day(parse_ts("2026-10-16T23:55:11Z")), 12)
        self.assertIsNone(campaign_day(parse_ts("2026-09-26T00:00:00Z")))

    def test_likelihood_bounds(self):
        st = Store(ROOT / "data")
        lk = likelihood(st.resets, st.signals, parse_ts("2026-10-17T10:30:00Z"))
        self.assertTrue(0 <= lk["score"] <= 1)
        lk2 = likelihood(st.resets, st.signals, parse_ts("2026-10-15T05:30:00Z"))
        self.assertIn(lk2["level"], ("pending", "high", "medium", "low"))


class DatasetTests(unittest.TestCase):
    def test_dataset_ids_exist_in_raw_cache(self):
        raw = {p["id"] for p in json.loads(RAW.read_text())["posts"]}
        for line in (ROOT / "data/resets.jsonl").read_text().splitlines():
            ev = json.loads(line)
            for pid in ev["posts"] + list(ev["mirror"].values()):
                self.assertIn(pid, raw)
            for k in ("announce", "confirm"):
                if ev[k]:
                    self.assertTrue(ev[k]["url"].endswith(ev[k]["post_id"]))
        for line in (ROOT / "data/signals.jsonl").read_text().splitlines():
            self.assertIn(json.loads(line)["post_id"], raw)

    def test_committed_dataset_matches_rebuild(self):
        subprocess.run([sys.executable, "scripts/build_dataset.py"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "scripts/render_timeline.py"], cwd=ROOT, check=True)
        diff = subprocess.run(
            ["git", "diff", "--exit-code", "--", "data/resets.jsonl", "data/signals.jsonl", "docs/timeline.md"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(diff.returncode, 0, diff.stdout[-2000:])


if __name__ == "__main__":
    unittest.main()
