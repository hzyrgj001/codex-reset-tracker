"""Command-line entry point: python -m codex_reset_tracker --help"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .analysis import WEEKDAYS, evaluate_tendencies, likelihood, stats
from .sources import DEFAULT_QUERIES, fetch_x_api, load_files
from .store import Store, append_raw
from .timeutil import fmt_tpe, parse_ts

ROOT = Path(__file__).resolve().parents[2]


def _state(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _tendencies(data_dir: Path) -> list:
    path = data_dir / "tendencies.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["tendencies"] if isinstance(data, dict) else data


def _fmt_p(p) -> str:
    if p is None:
        return "p=—"
    if p < 0.001:
        return "p<0.001"
    return f"p={p:.3f}"


def _print_weekdays(report: dict) -> None:
    print("\nweekday of each reset (announcement time, else confirmation):")
    for zone in ("America/Los_Angeles", "Asia/Taipei"):
        label = "Pacific" if zone == "America/Los_Angeles" else "Taipei"
        print(f"  {label} ({zone})")
        for window, title in (("all_time", "all-time"), ("last_60_days", "last 60 days")):
            block = report["slices"][window]
            since = f" since {block['since'][:10]}" if block.get("since") else ""
            for population, name in (("confirmed", "confirmed"), ("all", "all events")):
                row = block[population]
                counts = "  ".join(f"{d} {row[zone][d]}" for d in WEEKDAYS)
                print(f"    {name:<11} {title}{since} (n={row['n']}): {counts}")
    hours = report["slices"]["all_time"]["confirmed"]["hour_pacific"]
    nonzero = "  ".join(f"{h:02d}h×{v}" for h, v in enumerate(hours) if v)
    print(f"  Pacific hour-of-day, confirmed, all-time (n={sum(hours)}): {nonzero}")


def _print_tendencies(rows: list) -> None:
    if not rows:
        return
    print("\ntendencies (computed; supported only if share > baseline and one-sided binomial p < 0.05; n<10 is insufficient data):")
    for row in rows:
        pct = "—" if row["share"] is None else f"{100 * row['share']:.1f}%"
        base = "—" if row["baseline"] is None else f"{100 * row['baseline']:.1f}%"
        caveat = "  small sample" if row["small_sample"] else ""
        print(f"  [{row['verdict']:<18}] {row['k']}/{row['n']} = {pct} vs {base} ({row['baseline_name']}), "
              f"{_fmt_p(row['p_value'])}{caveat}")
        print(f"      {row['claim']}  [{row['source']}]")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="codex-reset-tracker",
                                 description="Unofficial Codex usage-reset tracker (not affiliated with OpenAI).")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data")
    ap.add_argument("--input", "-i", type=Path, nargs="*", default=[],
                    help="exported posts: X API v2 JSON, JSON list, JSONL, or data/raw/posts.json format")
    ap.add_argument("--x-api", action="store_true", help="fetch via X API v2 recent search (needs X_BEARER_TOKEN)")
    ap.add_argument("--query", action="append", help="override search queries (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="classify and report, but do not write data/")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON instead of the human summary")
    ap.add_argument("--chart", type=Path, nargs="?", const=Path("chart.png"), help="write a PNG (needs matplotlib)")
    ap.add_argument("--chart-since", default="2026-09-20T00:00:00Z")
    ap.add_argument("--now", help="override 'now' (ISO-8601) for reproducible summaries")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    store = Store(args.data_dir)
    posts = load_files(args.input)
    state_path = args.data_dir / "state.json"
    state = _state(state_path)
    if args.x_api:
        if not os.environ.get("X_BEARER_TOKEN"):
            print("X_BEARER_TOKEN not set; skipping X API fetch.", file=sys.stderr)
        else:
            fetched = fetch_x_api(args.query or DEFAULT_QUERIES, since_id=state.get("since_id"))
            posts.extend(fetched)
            if fetched:
                state["since_id"] = max(fetched, key=lambda p: int(p["id"]))["id"]
    changes = store.ingest(posts)
    if not args.dry_run:
        store.save()
        append_raw(args.data_dir, posts)
        if args.x_api and state:
            state_path.write_text(json.dumps(state, indent=2) + "\n")
    now = parse_ts(args.now) if args.now else None
    st = stats(store.resets, store.signals, now)
    tendencies = evaluate_tendencies(_tendencies(args.data_dir), store.resets, store.signals, now)
    st["tendencies"] = tendencies
    lk = likelihood(store.resets, store.signals, now, tendencies)
    if args.chart:
        from .chart import write_png
        write_png(store.resets, store.signals, args.chart, args.chart_since)
    alert = [c for c in changes if c["change"] in ("reset_announced", "reset_confirmed")
             or (c["change"] == "signal" and c["label"] == "reset_hint")]
    if args.json:
        print(json.dumps({"changes": changes, "alert": bool(alert), "stats": st, "likelihood": lk}, ensure_ascii=False, indent=2))
        return 0
    print(f"codex-reset-tracker {__version__}  (unofficial; not affiliated with OpenAI)")
    print(f"posts read: {len(posts)}   new items: {len(changes)}{'   [dry run]' if args.dry_run else ''}")
    for c in changes:
        kind = c.get("label", c["change"])
        p = c["post"]
        print(f"  [{kind:<18}] {p['taipei'][:16].replace('T', ' ')} TPE  @{p['author']}: {p['text'][:90]}  {p['url']}")
    print(f"\nconfirmed resets in dataset: {st['confirmed']} ({st['confirmed_full']} full)   announced-only: {st['announced_only']}")
    if st["last_confirmed"]:
        lt = parse_ts(st["last_confirmed"]["utc"])
        print(f"last confirmed: {fmt_tpe(lt)[:16].replace('T', ' ')} TPE / {st['last_confirmed']['utc']}  "
              f"({st['days_since_last_confirmed']} days ago)  {st['last_confirmed']['url']}")
    L = st["lag_hours"]
    if L["n"]:
        print(f"announce→confirm lag: median {L['median']} h (min {L['min']}, max {L['max']}, n={L['n']})")
    print(f"reset likelihood (heuristic, not a promise): {lk['level'].upper()} {lk['score']}"
          + (f"   campaign Day {lk['campaign_day']}" if lk["campaign_day"] else ""))
    for f in lk["factors"]:
        print(f"   {f['weight']:+.2f}  {f['factor']}")
    _print_weekdays(st["weekday"])
    _print_tendencies(tendencies)
    if alert:
        print("\nALERT: reset-related activity detected (see above).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
