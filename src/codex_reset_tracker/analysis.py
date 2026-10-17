"""Statistics and the transparent 'reset likelihood' heuristic.

The same formula is implemented in docs/index.html and docs/tendency.js.
Keep them in sync. It is a heuristic over public posts, NOT a prediction service
and NOT a promise.

Weekday counts and tendency verdicts are computed here. Verdicts are never
stored in data/tendencies.json. A claim is:

* insufficient data — fewer than MIN_TRIALS events in the test
* supported — share strictly above the baseline and one-sided binomial
  P(X >= k) < ALPHA
* not supported — otherwise

`small_sample` is a caveat (n < 30 or expected count under the null < 5).
It does not change the verdict.
"""
from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from .timeutil import PACIFIC, TAIPEI, campaign_day, fmt_utc, now_utc, parse_ts

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_LONG = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday",
    "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
}
ZONES = {"America/Los_Angeles": PACIFIC, "Asia/Taipei": TAIPEI}
ZONE_FACTOR_LABEL = {
    "America/Los_Angeles": "Pacific time",
    "Asia/Taipei": "Taipei time",
}
MIN_TRIALS = 10
ALPHA = 0.05
SMALL_N = 30

WEIGHTS = {
    "base": 0.05,
    "time_since_reset_max": 0.30,   # scales linearly to 96 h since the last confirmed reset
    "time_since_reset_full_h": 96,
    "campaign_even_day": 0.20,      # Days 2/6/8/10 reset; halved once the cycle is broken
    "outage_24h": 0.15,
    "hint_24h": 0.10,
    "rivalry_24h": 0.05,
    "day_slot_used": -0.25,         # a non-reset "Day N/" ship already posted for today
    # Added only when a weekday tendency's computed verdict is "supported"
    # and "now" falls on that weekday in the tendency's zone.
    "weekday_supported": 0.10,
}
PENDING_SCORE = 0.95


def _t(ev: dict[str, Any]) -> datetime:
    return parse_ts((ev.get("confirm") or ev.get("announce"))["utc"])


def confirmed(resets: list[dict[str, Any]], include_banked: bool = True) -> list[dict[str, Any]]:
    out = [e for e in resets if e["status"] == "confirmed" and (include_banked or e["kind"] == "full")]
    return sorted(out, key=_t)


def stats(resets: list[dict[str, Any]], signals: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    now = now or now_utc()
    conf = confirmed(resets)
    lags = [e["lag_hours"] for e in resets if e.get("lag_hours") is not None]
    intervals = [round((_t(b) - _t(a)).total_seconds() / 86400, 2) for a, b in zip(conf, conf[1:])]
    ann_hours_utc: Counter[int] = Counter()
    ann_hours_tpe: Counter[int] = Counter()
    for e in resets:
        a = e.get("announce") or e.get("confirm")
        dt = parse_ts(a["utc"])
        ann_hours_utc[dt.hour] += 1
        ann_hours_tpe[dt.astimezone(TAIPEI).hour] += 1
    total = sum(ann_hours_tpe.values()) or 1
    morning = sum(v for h, v in ann_hours_tpe.items() if 6 <= h < 13)
    last = conf[-1] if conf else None
    return {
        "events_total": len(resets),
        "confirmed": len(conf),
        "confirmed_full": len([e for e in conf if e["kind"] == "full"]),
        "announced_only": len([e for e in resets if e["status"] == "announced"]),
        "lag_hours": {"n": len(lags), "median": median(lags) if lags else None,
                      "min": min(lags) if lags else None, "max": max(lags) if lags else None},
        "interval_days": {"n": len(intervals), "median": median(intervals) if intervals else None},
        "first_post_hour_utc": dict(sorted(ann_hours_utc.items())),
        "first_post_hour_taipei": dict(sorted(ann_hours_tpe.items())),
        "morning_window_taipei_06_13": {"count": morning, "of": total, "share": round(morning / total, 2)},
        "last_confirmed": last and {"event_id": last["event_id"], "utc": _t(last).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "url": (last.get("confirm") or last["announce"])["url"]},
        "days_since_last_confirmed": last and round((now - _t(last)).total_seconds() / 86400, 2),
        "day_n_series": day_series(resets, signals),
        "weekday": weekday_breakdown(resets, now),
    }


def day_series(resets: list[dict[str, Any]], signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    days: dict[int, dict[str, Any]] = {}
    for e in resets:
        if e.get("day_n"):
            d = days.setdefault(e["day_n"], {"day": e["day_n"], "reset": False, "kinds": [], "posts": []})
            if e["status"] == "confirmed":
                d["reset"] = True
            d["kinds"].append(e["kind"])
            d["posts"].append((e.get("confirm") or e["announce"])["url"])
    for s in signals:
        if s.get("author") == "thsottiaux" and "usage_improvement" in s.get("labels", [s.get("label")]) and s.get("text", "").lower().startswith("day "):
            n = s.get("day_n")
            if n:
                d = days.setdefault(n, {"day": n, "reset": False, "kinds": [], "posts": []})
                d["kinds"].append("improvement")
                d["posts"].append(s["url"])
    return [days[k] for k in sorted(days)]


def anchor_dt(ev: dict[str, Any]) -> datetime | None:
    """Announcement time, or the confirmation time when the event was never announced."""
    ref = ev.get("announce") or ev.get("confirm")
    if not ref or not ref.get("utc"):
        return None
    return parse_ts(ref["utc"])


def _weekday(dt: datetime, zone_name: str) -> str:
    return WEEKDAYS[dt.astimezone(ZONES[zone_name]).weekday()]


def _hour(dt: datetime, zone_name: str) -> int:
    return dt.astimezone(ZONES[zone_name]).hour


def _select(resets: list[dict[str, Any]], population: str, window: str, now: datetime) -> list[dict[str, Any]]:
    rows = resets if population == "all" else [e for e in resets if e.get("status") == "confirmed"]
    if window == "last_60_days":
        since = now - timedelta(days=60)
        rows = [e for e in rows if (t := anchor_dt(e)) is not None and t >= since]
    return rows


def _counts(resets: list[dict[str, Any]], zone_name: str) -> dict[str, int]:
    counts = {d: 0 for d in WEEKDAYS}
    for ev in resets:
        dt = anchor_dt(ev)
        if dt is not None:
            counts[_weekday(dt, zone_name)] += 1
    return counts


def _hours(resets: list[dict[str, Any]], zone_name: str) -> list[int]:
    hours = [0] * 24
    for ev in resets:
        dt = anchor_dt(ev)
        if dt is not None:
            hours[_hour(dt, zone_name)] += 1
    return hours


def weekday_breakdown(resets: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    """Day-of-week (and Pacific hour-of-day) from announce UTC, else confirm UTC."""
    now = now or now_utc()
    slices: dict[str, Any] = {}
    for window in ("all_time", "last_60_days"):
        block: dict[str, Any] = {}
        if window == "last_60_days":
            block["since"] = fmt_utc(now - timedelta(days=60))
        for population in ("confirmed", "all"):
            rows = _select(resets, population, window, now)
            block[population] = {
                "n": len(rows),
                "America/Los_Angeles": _counts(rows, "America/Los_Angeles"),
                "Asia/Taipei": _counts(rows, "Asia/Taipei"),
                "hour_pacific": _hours(rows, "America/Los_Angeles"),
            }
        slices[window] = block
    return {
        "anchor": "announce_utc_else_confirm_utc",
        "weekdays": WEEKDAYS,
        "slices": slices,
    }


def binomial_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). One-sided upper tail."""
    if n <= 0 or k <= 0:
        return 1.0
    if k > n or p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    logs = []
    for i in range(k, n + 1):
        logs.append(
            math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + i * math.log(p) + (n - i) * math.log(1 - p)
        )
    top = max(logs)
    return min(1.0, math.exp(top) * sum(math.exp(x - top) for x in logs))


def judge(k: int, n: int, p0: float, baseline_name: str) -> dict[str, Any]:
    """Turn a binomial comparison into a verdict. p0 is the null share."""
    raw_p = None if n == 0 else binomial_sf(k, n, p0)
    share = None if n == 0 else k / n
    if n < MIN_TRIALS:
        verdict = "insufficient data"
    elif share is not None and share > p0 and raw_p is not None and raw_p < ALPHA:
        verdict = "supported"
    else:
        verdict = "not supported"
    return {
        "verdict": verdict,
        "k": k,
        "n": n,
        "share": None if share is None else round(share, 4),
        "baseline": round(p0, 4),
        "baseline_name": baseline_name,
        "p_value": None if raw_p is None else round(raw_p, 6),
        "small_sample": n < SMALL_N or (n * p0 < 5),
    }


def _labels(sig: dict[str, Any]) -> list[str]:
    labs = sig.get("labels")
    if labs:
        return list(labs)
    if sig.get("label"):
        return [sig["label"]]
    return []


def _matching_signals(signals: list[dict[str, Any]], labels: list[str], authors: list[str] | None) -> list[dict[str, Any]]:
    want = set(labels)
    out = []
    for sig in signals:
        if sig.get("false_positive"):
            continue
        if authors and sig.get("author") not in set(authors):
            continue
        if want.intersection(_labels(sig)):
            out.append(sig)
    return out


def reset_instants(resets: list[dict[str, Any]]) -> list[datetime]:
    out: list[datetime] = []
    for ev in resets:
        for key in ("announce", "confirm"):
            ref = ev.get(key)
            if ref and ref.get("utc"):
                out.append(parse_ts(ref["utc"]))
    return out


def coverage_share(windows: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> float:
    """Fraction of [start, end] covered by the union of windows."""
    span = (end - start).total_seconds()
    if span <= 0:
        return 0.0
    clipped: list[tuple[datetime, datetime]] = []
    for a, b in windows:
        a, b = max(a, start), min(b, end)
        if b > a:
            clipped.append((a, b))
    clipped.sort()
    merged: list[list[datetime]] = []
    for a, b in clipped:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    covered = sum((b - a).total_seconds() for a, b in merged)
    return covered / span


def _cluster(signals: list[dict[str, Any]], cluster_hours: float) -> list[dict[str, Any]]:
    ordered = sorted(signals, key=lambda s: parse_ts(s["utc"]))
    episodes: list[dict[str, Any]] = []
    gap = timedelta(hours=cluster_hours)
    for sig in ordered:
        t = parse_ts(sig["utc"])
        rel = sig.get("related_event")
        if episodes:
            prev = episodes[-1]
            same = bool(rel) and rel == prev["related"]
            if same or t - prev["last"] <= gap:
                prev["last"] = t
                prev["signals"].append(sig)
                if rel:
                    prev["related"] = rel
                continue
        episodes.append({"start": t, "last": t, "related": rel, "signals": [sig]})
    return episodes


def _span(points: list[datetime]) -> tuple[datetime, datetime] | None:
    if not points:
        return None
    return min(points), max(points)


def _test_weekday(spec: dict[str, Any], resets: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    rows = _select(resets, spec.get("population", "confirmed"), spec.get("window", "all_time"), now)
    counts = _counts(rows, spec["zone"])
    day = spec["weekday"]
    return judge(counts[day], len(rows), 1 / 7, "1/7")


def _test_even_day(resets: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [e for e in resets if e.get("status") == "confirmed" and e.get("day_n")]
    k = sum(1 for e in rows if int(e["day_n"]) % 2 == 0)
    return judge(k, len(rows), 0.5, "1/2")


def _test_hour_window(spec: dict[str, Any], resets: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    rows = _select(resets, spec.get("population", "all"), spec.get("window", "all_time"), now)
    start, end = int(spec["start_hour"]), int(spec["end_hour"])
    zone = spec["zone"]
    k = 0
    for ev in rows:
        dt = anchor_dt(ev)
        if dt is not None and start <= _hour(dt, zone) < end:
            k += 1
    width = (end - start) % 24
    return judge(k, len(rows), width / 24, f"{width}/24")


def _test_signal_then_reset(spec: dict[str, Any], resets: list[dict[str, Any]], signals: list[dict[str, Any]]) -> dict[str, Any]:
    hours = float(spec.get("within_hours", 48))
    matched = _matching_signals(signals, spec["labels"], spec.get("authors"))
    episodes = _cluster(matched, float(spec.get("cluster_hours", 6)))
    instants = reset_instants(resets)
    k = 0
    for ep in episodes:
        end = ep["start"] + timedelta(hours=hours)
        if any(ep["start"] <= t <= end for t in instants):
            k += 1
    points = instants + [ep["start"] for ep in episodes]
    span = _span(points)
    if span is None:
        p0 = 0.0
    else:
        windows = [(t - timedelta(hours=hours), t) for t in instants]
        p0 = coverage_share(windows, span[0], span[1])
    return judge(k, len(episodes), p0, "timeline")


def _test_signal_near_reset(spec: dict[str, Any], resets: list[dict[str, Any]], signals: list[dict[str, Any]]) -> dict[str, Any]:
    hours = float(spec.get("within_hours", 2))
    matched = _matching_signals(signals, spec["labels"], spec.get("authors"))
    instants = reset_instants(resets)
    k = 0
    trial_times: list[datetime] = []
    window = timedelta(hours=hours)
    for sig in matched:
        t = parse_ts(sig["utc"])
        trial_times.append(t)
        if any(abs((t - r).total_seconds()) <= window.total_seconds() for r in instants):
            k += 1
    span = _span(instants + trial_times)
    if span is None:
        p0 = 0.0
    else:
        windows = [(t - window, t + window) for t in instants]
        p0 = coverage_share(windows, span[0], span[1])
    return judge(k, len(matched), p0, "timeline")


def evaluate_tendencies(
    tendencies: list[dict[str, Any]],
    resets: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fill each claim with a computed verdict. Does not read or write verdicts on disk."""
    now = now or now_utc()
    out = []
    for item in tendencies:
        spec = item.get("test") or {}
        kind = spec.get("kind")
        if kind == "weekday":
            judged = _test_weekday(spec, resets, now)
        elif kind == "even_campaign_day":
            judged = _test_even_day(resets)
        elif kind == "hour_window":
            judged = _test_hour_window(spec, resets, now)
        elif kind == "signal_then_reset":
            judged = _test_signal_then_reset(spec, resets, signals)
        elif kind == "signal_near_reset":
            judged = _test_signal_near_reset(spec, resets, signals)
        else:
            raise ValueError(f"unknown tendency test: {kind}")
        out.append({
            "id": item["id"],
            "claim": item["claim"],
            "source": item["source"],
            "test": spec,
            **judged,
        })
    return out


def _add_weekday_factor(factors: list[tuple[str, float]], tendencies: list[dict[str, Any]], now: datetime) -> None:
    """Use a weekday prior only when that tendency's verdict is supported."""
    for item in tendencies:
        spec = item.get("test") or {}
        if spec.get("kind") != "weekday" or item.get("verdict") != "supported":
            continue
        zone_name = spec.get("zone")
        if zone_name not in ZONES:
            continue
        if WEEKDAYS[now.astimezone(ZONES[zone_name]).weekday()] != spec.get("weekday"):
            continue
        day = WEEKDAY_LONG.get(spec["weekday"], spec["weekday"])
        place = ZONE_FACTOR_LABEL.get(zone_name, zone_name)
        factors.append((f"{day} in {place} (weekday tendency supported)", WEIGHTS["weekday_supported"]))
        return


def likelihood(
    resets: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    now: datetime | None = None,
    tendencies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = now or now_utc()
    w = WEIGHTS
    factors: list[tuple[str, float]] = [("base rate", w["base"])]
    pending = [e for e in resets if e["status"] == "announced" and e.get("announce")
               and (now - parse_ts(e["announce"]["utc"])) < timedelta(hours=48)]
    conf = confirmed(resets)
    last_t = _t(conf[-1]) if conf else None
    if last_t:
        h = (now - last_t).total_seconds() / 3600
        v = round(w["time_since_reset_max"] * min(1.0, h / w["time_since_reset_full_h"]), 3)
        factors.append((f"{h:.0f} h since last confirmed reset", v))
    day = campaign_day(now)
    if day:
        broken = any("break the cycle" in s.get("text", "").lower() and (not last_t or parse_ts(s["utc"]) > last_t)
                     for s in signals)
        if day % 2 == 0:
            v = w["campaign_even_day"] * (0.5 if broken else 1.0)
            factors.append((f"Day {day} is even" + (" (cycle declared broken: halved)" if broken else ""), v))
        today_pt = now.astimezone(PACIFIC).date()
        used = any("usage_improvement" in s.get("labels", [s.get("label")]) and s.get("author") == "thsottiaux"
                   and s.get("text", "").lower().startswith(f"day {day}")
                   and parse_ts(s["utc"]).astimezone(PACIFIC).date() == today_pt for s in signals)
        if used:
            factors.append((f"Day {day}/ already shipped an improvement", w["day_slot_used"]))
    recent = [s for s in signals if timedelta(0) <= now - parse_ts(s["utc"]) <= timedelta(hours=24) and not s.get("false_positive")]
    for label, key, name in (("outage", "outage_24h", "outage/capacity signal in last 24 h"),
                             ("reset_hint", "hint_24h", "strong hint in last 24 h"),
                             ("rivalry_hint", "rivalry_24h", "Tibo/poteto banter in last 24 h")):
        if any(label in s.get("labels", [s.get("label")]) for s in recent):
            factors.append((name, w[key]))
    if tendencies:
        _add_weekday_factor(factors, tendencies, now)
    score = max(0.0, min(1.0, sum(v for _, v in factors)))
    if pending:
        factors.append(("announced reset not yet confirmed", PENDING_SCORE - score if PENDING_SCORE > score else 0))
        score = max(score, PENDING_SCORE)
    level = "pending" if pending else ("high" if score >= 0.5 else "medium" if score >= 0.25 else "low")
    return {"score": round(score, 2), "level": level, "campaign_day": day,
            "factors": [{"factor": n, "weight": round(v, 3)} for n, v in factors],
            "disclaimer": "Heuristic over public posts. Not a prediction or a promise; resets are at OpenAI's discretion."}
