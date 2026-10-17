"""Locale files stay in sync, and the visualizer wires both languages."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = json.loads((ROOT / "docs" / "locales" / "en.json").read_text(encoding="utf-8"))
ZH = json.loads((ROOT / "docs" / "locales" / "zh.json").read_text(encoding="utf-8"))
HTML = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
I18N = (ROOT / "docs" / "i18n.js").read_text(encoding="utf-8")
ROOT_HTML = (ROOT / "index.html").read_text(encoding="utf-8")

# Strings the Chinese chrome must not keep in English.
MUST_DIFFER = [
    "pageTitle", "title", "daysSince", "likelihoodTitle", "timeline", "seriesTitle",
    "lagTitle", "heatTitle", "events", "refresh", "footer", "label_reset_announced",
    "label_reset_confirmed", "label_outage", "label_recovery", "label_rivalry_hint",
    "label_usage_improvement", "kind_banked", "fallbackLead", "noData", "disclaimerEmph",
    "openVisualizer",
]


class LocaleTests(unittest.TestCase):
    def test_keys_match_and_are_nonempty(self):
        self.assertEqual(set(EN), set(ZH))
        for key, value in EN.items():
            self.assertIsInstance(value, str)
            self.assertTrue(value.strip(), key)
            self.assertTrue(ZH[key].strip(), key)

    def test_chinese_chrome_is_translated(self):
        for key in MUST_DIFFER:
            self.assertNotEqual(EN[key], ZH[key], key)
            self.assertRegex(ZH[key], r"[\u4e00-\u9fff]")

    def test_html_keys_exist(self):
        used = set(re.findall(r'data-i18n(?:-attr)?="([^"]+)"', HTML))
        attr_keys = set()
        for raw in used:
            if ":" in raw:
                attr_keys.add(raw.split(":", 1)[1])
            else:
                attr_keys.add(raw)
        called = set(re.findall(r'\bt\(\s*"([A-Za-z0-9_]+)"\s*[,)]', HTML))
        missing = (attr_keys | called) - set(EN)
        self.assertFalse(missing, sorted(missing))

    def test_page_wires_toggle_and_detection(self):
        self.assertIn('data-set-lang="en"', HTML)
        self.assertIn('data-set-lang="zh"', HTML)
        self.assertIn(">EN<", HTML)
        self.assertIn(">中文<", HTML)
        self.assertIn("locales/en.json", I18N)
        self.assertIn("locales/zh.json", I18N)
        self.assertIn("codexResetTracker.lang", I18N)
        self.assertIn("navigator.languages", I18N)
        self.assertIn('src="i18n.js"', HTML)
        self.assertIn("打开可视化页面", ROOT_HTML)
        self.assertIn("Open the visualizer", ROOT_HTML)
        self.assertIn("codexResetTracker.lang", ROOT_HTML)

    def test_preferred_lang(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        script = r"""
const fs = require("fs");
const vm = require("vm");
const ctx = { console, globalThis: {} };
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync("docs/i18n.js", "utf8"), ctx);
const pref = ctx.I18N.preferredLang;
const cases = [
  [{ languages: ["zh-CN"] }, "zh"],
  [{ languages: ["zh"] }, "zh"],
  [{ languages: ["zh-TW", "en-US"] }, "zh"],
  [{ languages: ["zh-Hans"] }, "zh"],
  [{ languages: ["zh-Hant", "en"] }, "zh"],
  [{ languages: ["en-US", "zh-CN"] }, "zh"],
  [{ languages: ["en-US"] }, "en"],
  [{ languages: ["fr-FR"] }, "en"],
  [{ languages: [] }, "en"],
  [{ stored: "en", languages: ["zh-CN"] }, "en"],
  [{ stored: "zh", languages: ["en-US"] }, "zh"],
  [{ query: "zh", languages: ["en-US"] }, "zh"],
  [{ stored: "en", query: "zh", languages: ["zh-CN"] }, "en"],
  [{ stored: "nope", query: "en", languages: ["zh-CN"] }, "en"],
];
for (const [opts, want] of cases) {
  const got = pref(opts);
  if (got !== want) {
    console.error(JSON.stringify(opts), got, want);
    process.exit(1);
  }
}
"""
        subprocess.run([node, "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
