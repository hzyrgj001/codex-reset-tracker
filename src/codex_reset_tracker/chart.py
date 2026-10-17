"""Optional PNG chart (requires matplotlib; everything else is stdlib)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .timeutil import parse_ts

COLORS = {"reset_confirmed": "#16a34a", "reset_announced": "#f59e0b", "reset_hint": "#a855f7",
          "outage": "#dc2626", "recovery": "#0ea5e9", "rivalry_hint": "#ec4899", "usage_improvement": "#64748b", "other": "#cbd5e1"}


def write_png(resets: list[dict[str, Any]], signals: list[dict[str, Any]], out: Path, since: str | None = None) -> Path:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("--chart needs matplotlib: pip install matplotlib") from exc
    lo = parse_ts(since) if since else None
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.5), gridspec_kw={"height_ratios": [3, 2]})
    rows = list(COLORS)
    for s in signals:
        t = parse_ts(s["utc"])
        if lo and t < lo:
            continue
        label = s["label"] if s["label"] in rows else "other"
        ax1.scatter(t, rows.index(label), color=COLORS[label], s=22,
                    facecolors="none" if s.get("false_positive") else COLORS[label])
    for e in resets:
        for key, label in (("announce", "reset_announced"), ("confirm", "reset_confirmed")):
            if e.get(key):
                t = parse_ts(e[key]["utc"])
                if lo and t < lo:
                    continue
                ax1.scatter(t, rows.index(label), color=COLORS[label], s=60, marker="D", edgecolor="black")
    ax1.set_yticks(range(len(rows)), rows)
    ax1.set_title("Codex reset tracker (unofficial): resets and signals")
    lags = [(parse_ts(e["confirm"]["utc"]), e["lag_hours"]) for e in resets if e.get("lag_hours") is not None]
    lags = [(t, l) for t, l in lags if not lo or t >= lo]
    if lags:
        ax2.bar([t for t, _ in lags], [l for _, l in lags], width=0.6, color="#16a34a")
    ax2.set_ylabel("announce→confirm (h)")
    fig.autofmt_xdate()
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    return out
