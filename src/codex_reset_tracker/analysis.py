"""Statistics and the transparent 'reset likelihood' heuristic.

The same formula is implemented in docs/index.html (JavaScript). Keep them in sync.
It is a heuristic over public posts, NOT a prediction service and NOT a promise.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from .timeutil import PACIFIC, TAIPEI, campaign_day, now_utc, parse_ts

WEIGHTS = {
    "base": 0.05,
    "time_since_reset_max": 0.30,   # scales linearly to 96 h since the last confirmed reset
    "time_since_reset_full_h": 96,
    "campaign_even_day": 0.20,      # Days 2/6/8/10 reset; halved once the cycle is broken
    "outage_24h": 0.15,
    "hint_24h": 0.10,
    "rivalry_24h": 0.05,
    "day_slot_used": -0.25,         # a non-reset "Day N/" ship already posted for today
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


def likelihood(resets: list[dict[str, Any]], signals: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
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
    score = max(0.0, min(1.0, sum(v for _, v in factors)))
    if pending:
        factors.append(("announced reset not yet confirmed", PENDING_SCORE - score if PENDING_SCORE > score else 0))
        score = max(score, PENDING_SCORE)
    level = "pending" if pending else ("high" if score >= 0.5 else "medium" if score >= 0.25 else "low")
    return {"score": round(score, 2), "level": level, "campaign_day": day,
            "factors": [{"factor": n, "weight": round(v, 3)} for n, v in factors],
            "disclaimer": "Heuristic over public posts. Not a prediction or a promise; resets are at OpenAI's discretion."}
