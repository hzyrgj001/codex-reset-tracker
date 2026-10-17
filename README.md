# codex-reset-tracker

> **中文。** [可视化页面](docs/index.html)会按浏览器语言在 English 与简体中文之间自动切换，也可用页眉的 **EN | 中文** 手动切换（记在 localStorage）。帖子原文不翻译。数据集和其余文档仍是英文。

**An unofficial, open-source tracker of Codex / ChatGPT Work usage resets.** It includes:

* a **historical dataset** of 62 reset events since 2025-09 (45 confirmed), each with links to its X posts, in Taipei (UTC+8) and UTC;
* a **pattern catalogue** of what has historically predicted or coincided with a reset (Day-N cadence, announce→confirm lag, outage→recovery, morning window, rivalry banter, banked vs global), with false positives;
* a small **Python detector** (stdlib only) that reads exported X results or the X API, classifies posts, and appends structured events;
* a **static visualizer** (no dependencies) for GitHub Pages or `python -m http.server`;
* a **Grok Bot skill** so anyone with Grok Bot can set up the watch with one prompt.

> **Disclaimer.** This is a community project. It is **not affiliated with, endorsed by, or speaking for OpenAI or SpaceXAI.**
> It only reads public posts, mainly by Tibo ([@thsottiaux](https://x.com/thsottiaux)) and the third-party
> [@codex_resets](https://x.com/codex_resets) mirror. Resets are entirely at OpenAI's discretion. The "likelihood" indicator is a
> transparent heuristic, **not a prediction or a promise**. Post times are announcement times, not per-account delivery times.

## Quick start

```bash
git clone https://github.com/hzyrgj001/codex-reset-tracker.git && cd codex-reset-tracker
python3 -m unittest discover -s tests            # Python 3.11+, no packages needed
PYTHONPATH=src python3 -m codex_reset_tracker --dry-run
```

Example output (2026-10-17 10:40 UTC):

```
confirmed resets in dataset: 45 (40 full)   announced-only: 17
last confirmed: 2026-10-15 14:28 TPE / 2026-10-15T06:28:13Z  (2.17 days ago)  https://x.com/thsottiaux/status/2110618732666257557
announce→confirm lag: median 8.555 h (min 0.42, max 51.89, n=14)
reset likelihood (heuristic, not a promise): MEDIUM 0.26   campaign Day 13
```

### Visualizer

```bash
python3 -m http.server 8000        # from the repo root
# open http://localhost:8000/docs/
```

The page shows:

* a timeline of resets and signals, colored by type;
* the Day-N grid with reset days highlighted;
* announce→confirm lag bars;
* a days-since-last-reset counter;
* an hour-of-day heatmap in UTC and in **your** local time;
* a weekday bar chart (Pacific or your local time) and a tendencies list with a computed verdict for each claim;
* the likelihood indicator, with every factor shown;
* the event tables.

Every point links to its X post. If you open the HTML file directly (`file://`), browsers block `fetch`.
The page then offers a file picker for the two `.jsonl` files.

For GitHub Pages: Settings → Pages → Source: **GitHub Actions**. The `pages` workflow then publishes `docs/` together with `data/`.

## Languages

The visualizer auto-selects **English** or **Simplified Chinese**. If any entry in `navigator.languages` (falling back to `navigator.language`) starts with `zh` — `zh`, `zh-CN`, `zh-TW`, `zh-Hans`, `zh-Hant`, and similar — the chrome is Mandarin; otherwise it is English. The **EN | 中文** toggle stores the choice in `localStorage` under `codexResetTracker.lang` and overrides auto-detect until that key is cleared. `?lang=zh` or `?lang=en` applies when nothing is stored. Dates and times format with `en-US` or `zh-CN`. X post text, curated notes, and URLs stay as written.

Optional PNG chart: `pip install matplotlib`, then `PYTHONPATH=src python3 -m codex_reset_tracker --dry-run --chart chart.png`.

## Using the detector

```
python -m codex_reset_tracker [--input FILE ...] [--x-api] [--dry-run] [--json] [--chart [PNG]] [--now ISO]
```

| Source | How |
|---|---|
| **Exported X results (no key)** | `--input results.json`. Accepts X API v2 responses (also when wrapped in other text, as agent tools save them), JSON lists, JSONL, or `data/raw/posts.json`. |
| **Grok Bot `x` connector (no key)** | See [skills/codex-reset-tracker/SKILL.md](skills/codex-reset-tracker/SKILL.md). The bot saves search results to a file and passes it with `--input`. |
| **X API v2 (your key)** | `export X_BEARER_TOKEN=...; ... --x-api`. Uses recent search (last 7 days) via stdlib `urllib`. Which API tier you need depends on X's current pricing; nothing here requires a paid plan if you use exports. |
| **Hand-made JSONL** | `{"id":"<real post id>","author":"thsottiaux","created_at":"2026-10-15T04:55:51Z","text":"Day 10/ Reset"}` |

`scripts/fetch_sample.sh` wraps these three modes. With no key and no files, it replays the bundled cache as a dry run.

### Labels

Posts are labelled `reset_announced`, `reset_confirmed`, `reset_hint`, `outage`, `recovery`, `rivalry_hint`,
`usage_improvement` (not a reset) or `other`. The rules live in [`src/codex_reset_tracker/classifier.py`](src/codex_reset_tracker/classifier.py):

* Only @thsottiaux can create reset events. Mirror and community posts become linked signals.
* Short replies like "It's done" or "Landing within the next 2 hours" count only when they reply to or quote a known reset post.
* Negations ("I can't really give a reset") are guarded.
* "Day N/" ships without "Reset", 2X-usage polls and "simple plan" posts are `usage_improvement`.

### Output

* `data/resets.jsonl` holds one reset event per line: announce/confirm posts, lag, kind (`full`/`banked`/`makeup`), status, Day N, triggers and co-signals.
* `data/signals.jsonl` holds related non-reset posts.
* Both are keyed by X post id, so re-ingesting is **idempotent**. Field reference: [docs/schema.md](docs/schema.md).
* `--json` prints `{changes, alert, stats, likelihood}`. `stats` includes the weekday breakdown and the computed tendency verdicts. `alert` is true when a new announcement, confirmation, or strong hint arrives.

## Data and research

* [docs/patterns.md](docs/patterns.md): the pattern catalogue, with evidence counts, sources, false positives and open questions.
* [docs/timeline.md](docs/timeline.md): every event, generated from the data.
* `data/raw/posts.json` is a verbatim cache of the X API results (127 posts) behind the dataset.
  `scripts/build_dataset.py` rebuilds both JSONL files from that cache plus a human curation table (CI checks the rebuild is reproducible).
  **No post ID or time in this repo was typed by hand.** All came from X API lookups made on 2026-10-17.

Headline findings (details and links are in patterns.md):

1. **Every-other-day cadence:** in the 28-day series (from Oct 5 PT), Days 2, 6, 8 and 10 were full resets and Day 3 was a banked reset.
   The pattern broke on Day 12, after *"Let's break the cycle."*
2. **Announce → confirm lag is shrinking:** 18.2 → 19.1 → 8.4 → 5.8 → 4.0 → 1.5 h since Sep 26. The all-time median is 8.6 h.
3. **Two-post format:** "Day N/ Reset", followed within 16–41 s by a self-reply giving the window.
4. **Morning in Taipei:** 8 of 9 events since Sep 20 began between 06:00 and 13:00 TPE (22:00–05:00 UTC).
5. **Outage → recovery → reset:** the most common trigger historically. The reset is usually promised in the recovery post.
6. **@poteto banter** came within ±2 h of 3 of 5 campaign resets. It also happens on non-reset days, so it gets a low weight.
7. **Banked (personal reset button) ≠ global reset.** Polls about 2X usage and "simple plan" posts are not resets.
8. **Monday is not a supported reset day.** Confirmed resets by Pacific weekday are Mon 6, Tue 6, Wed 6, Thu 5, Fri 8, Sat 10, Sun 4 (n=45). Monday is 13.3% vs 14.3% expected (p=0.637). Verdicts live in the CLI output, not in `data/tendencies.json`.

## Automation (GitHub Actions)

* `.github/workflows/track.yml` runs hourly. If the `X_BEARER_TOKEN` repository secret is **not** set, it prints a notice and skips.
  If it is set, it fetches, classifies, appends to `data/`, re-renders the timeline, and commits.
* `.github/workflows/ci.yml` runs the tests on Python 3.11–3.13 and checks that the dataset rebuilds exactly.
* `.github/workflows/pages.yml` publishes the visualizer.

## Grok Bot users

Paste this to your Grok Bot:

> Set up the Codex reset tracker from github.com/hzyrgj001/codex-reset-tracker. Use your x connector to check for new posts
> every 4 hours, and message me only when a Codex usage reset is announced or confirmed, or there's a strong hint.
> Show times in my time zone and in UTC, and always link the X post.

The bot follows [skills/codex-reset-tracker/SKILL.md](skills/codex-reset-tracker/SKILL.md). It stays read-only on X and never posts on your behalf.

## Repository layout

```
data/resets.jsonl  data/signals.jsonl  data/tendencies.json  data/raw/posts.json
docs/index.html (visualizer)  docs/patterns.md  docs/schema.md  docs/timeline.md
src/codex_reset_tracker/  (classifier, sources, store, analysis, chart, cli)
scripts/build_dataset.py  scripts/render_timeline.py  scripts/fetch_sample.sh
skills/codex-reset-tracker/SKILL.md
tests/test_tracker.py
.github/workflows/{track,ci,pages}.yml
```

## Contributing

Corrections are welcome. Please include the X post URL. To add a historical event:

1. Add the verbatim post to `data/raw/posts.json` (from an API lookup, not retyped).
2. Add a row to `EVENTS` in `scripts/build_dataset.py`.
3. Run `python scripts/build_dataset.py && python scripts/render_timeline.py`.

## License

[Apache-2.0](LICENSE). See [NOTICE](NOTICE). Quoted posts remain the property of their authors and are abbreviated and linked.
