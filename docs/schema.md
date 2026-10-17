# Data schema

Both files are [JSON Lines](https://jsonlines.org/): one object per line, UTF-8, sorted by time.
All timestamps are ISO-8601. `utc` ends in `Z`; `taipei` carries `+08:00` (Asia/Taipei).
**IDs are X post IDs**, so re-ingesting the same posts never creates duplicates.

## Post reference (`PostRef`)

| field | type | description |
|---|---|---|
| `post_id` | string | X post id (string, not int — they exceed 2^53) |
| `url` | string | `https://x.com/<author>/status/<post_id>` |
| `author` | string | handle without `@` |
| `utc` | string | post time, UTC |
| `taipei` | string | post time, UTC+8 |
| `text` | string | abbreviated post text (≤200 chars, whitespace collapsed) |

## `data/resets.jsonl`: one reset event per line

| field | type | description |
|---|---|---|
| `event_id` | string | `x:<id>` of the first post (the announcement, or the confirmation if there was no announcement) |
| `kind` | enum | `full` (global refill) · `banked` (credit you redeem yourself) · `makeup` (fix for accounts that missed one) |
| `status` | enum | `confirmed` (executed-language post exists) · `announced` (promised/imminent, no completion post found) |
| `scope` | string\|null | who it applies to, as stated in the post |
| `triggers` | string[] | e.g. `campaign_day`, `outage`, `recovery`, `capacity`, `milestone`, `launch`, `weekend`, `investigation`, `rivalry`, `vote`, `silent`, `makeup`, `promise` |
| `day_n` | int\|null | Day N of the 28-day series (Pacific calendar), when part of it |
| `announce` | PostRef\|null | first announcing post |
| `confirm` | PostRef\|null | completion post |
| `lag_hours` | number\|null | `confirm.utc − announce.utc` in hours |
| `first_post_hour_taipei` | int | 0–23 (curated rows) |
| `weekday_taipei` | string | `Mon`…`Sun` (curated rows) |
| `posts` | string[] | **all** post ids belonging to this event (dedup key) |
| `extra_posts` | PostRef[] | follow-ups (window replies, corrections) |
| `co_signals` | string[] | `signal_id`s of related signals (outage, rivalry, hints) |
| `mirror` | object | `{announced, confirmed}` post ids from the third-party @codex_resets mirror |
| `source` | enum | `curated` (human-reviewed) · `detector` (auto; review before trusting) |
| `notes` | string | free text |

## `data/signals.jsonl`: non-reset (or mirror) posts

| field | type | description |
|---|---|---|
| `signal_id` | string | `x:<post_id>` |
| …PostRef fields | | `post_id`, `url`, `author`, `utc`, `taipei`, `text` |
| `label` | enum | primary label (see below) |
| `labels` | string[] | all matching labels, priority order |
| `day_n` | int\|null | Day N from the text (`Day 7/`) or posting date for Tibo posts |
| `related_event` | string\|null | `event_id` this signal belongs to |
| `false_positive` | bool | hint that did **not** lead to a reset |
| `source` | enum | `curated` · `detector` |
| `notes` | string | |
| `reasons` | string[] | (detector rows) which rule fired |

### Labels

| label | meaning |
|---|---|
| `reset_announced` | trusted author (Tibo) promises a reset; or @codex_resets 🗓️ mirror alert |
| `reset_confirmed` | trusted author says it happened; or @codex_resets ✅ mirror alert |
| `reset_hint` | strong non-committal hint ("or a reset", "break the cycle", ⚠️ possible-reset alert, "did we just get a random reset?") |
| `outage` | down / at capacity / incident / heavy load / missed reset |
| `recovery` | back up / mitigated / more capacity online (wins over `outage` when a post has both) |
| `rivalry_hint` | Tibo ↔ @poteto banter |
| `usage_improvement` | a non-reset "Day N/" ship, polls about 2X usage, "more usage" plans |
| `other` | kept only when curated for context |

Only `thsottiaux` can create `reset_*` **events**. Mirror and community posts become signals that link to an event.

## `data/raw/posts.json`

Verbatim cache of X API results (`id`, `author_id`, `author`, `created_at`, `text`, `referenced`, `url`).
`scripts/build_dataset.py` regenerates both JSONL files from this cache plus the curation table in that script.

## `data/tendencies.json`

Claims to test. **Verdicts are not stored here.** `evaluate_tendencies` (and `docs/tendency.js`) fill them at read time.

| field | type | description |
|---|---|---|
| `id` | string | stable id |
| `claim` | string | plain sentence, not a verdict |
| `source` | enum | `community observation` · `data` |
| `test` | object | how to count trials. `kind` is `weekday`, `even_campaign_day`, `hour_window`, `signal_then_reset`, or `signal_near_reset` |

A computed result adds `verdict` (`supported` · `not supported` · `insufficient data`), `k`, `n`, `share`, `baseline`, `baseline_name` (`1/7`, `1/2`, `7/24`, or `timeline`), `p_value`, and `small_sample`. Supported means the share is above the baseline and the one-sided binomial p-value is under 0.05. Fewer than 10 trials is insufficient data.

Weekday and hour counts use each event's `announce.utc`, or `confirm.utc` when there was no announcement.

## `data/state.json` (optional, git-ignored by default)

`{"since_id": "<last seen post id>"}` for incremental X API polling.
