#!/usr/bin/env bash
# Fetch recent posts and run the detector.
#
#   With a key:    X_BEARER_TOKEN=... scripts/fetch_sample.sh          (X API v2 recent search, last 7 days)
#   Without a key: scripts/fetch_sample.sh path/to/export.json ...    (any exported X results)
#                  scripts/fetch_sample.sh                            (replays the bundled verified cache, dry run)
#
# Ways to get posts without a paid API key:
#   * A Grok Bot (or other agent) with an X connector: see skills/codex-reset-tracker/SKILL.md.
#     Save the raw JSON result to a file and pass it here.
#   * Copy a post's JSON from your browser's developer tools (x.com GraphQL responses) and
#     reduce it to {"id","author","created_at","text"} objects, one per line (JSONL).
#   * Hand-made JSONL is fine too: {"id":"<post id>","author":"thsottiaux","created_at":"2026-10-15T04:55:51Z","text":"Day 10/ Reset"}
#     The post id must be real. The URL is derived as https://x.com/<author>/status/<id>.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src

if [[ $# -gt 0 ]]; then
  python3 -m codex_reset_tracker --input "$@"
elif [[ -n "${X_BEARER_TOKEN:-}" ]]; then
  python3 -m codex_reset_tracker --x-api
else
  echo "No X_BEARER_TOKEN and no input files: replaying data/raw/posts.json (dry run)." >&2
  python3 -m codex_reset_tracker --input data/raw/posts.json --dry-run
fi
