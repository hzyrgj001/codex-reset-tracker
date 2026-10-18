"""JSONL storage with idempotent IDs (the X post id is the key)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .classifier import TRUSTED_RESET_AUTHORS, MIRROR_AUTHORS, CONTEXT_CONFIRM_RX, Classification, classify
from .timeutil import campaign_day, fmt_tpe, fmt_utc, parse_ts

ABBREV = 200


def abbreviate(text: str, limit: int = ABBREV) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def post_url(post: dict[str, Any]) -> str:
    if post.get("url"):
        return post["url"]
    author = post.get("author") or "i"
    return f"https://x.com/{author}/status/{post['id']}"


def post_ref(post: dict[str, Any]) -> dict[str, Any]:
    dt = parse_ts(post["created_at"])
    return {
        "post_id": post["id"],
        "url": post_url(post),
        "author": post.get("author"),
        "utc": fmt_utc(dt),
        "taipei": fmt_tpe(dt),
        "text": abbreviate(post.get("text", "")),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")
    tmp.replace(path)


def lag_hours(ev: dict[str, Any]) -> float | None:
    a, c = ev.get("announce"), ev.get("confirm")
    if not a or not c:
        return None
    return round((parse_ts(c["utc"]) - parse_ts(a["utc"])).total_seconds() / 3600, 2)


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.resets_path = self.data_dir / "resets.jsonl"
        self.signals_path = self.data_dir / "signals.jsonl"
        self.resets = read_jsonl(self.resets_path)
        self.signals = read_jsonl(self.signals_path)

    # ---- indexes -----------------------------------------------------
    def known_post_ids(self) -> set[str]:
        ids = {s["post_id"] for s in self.signals}
        for ev in self.resets:
            ids.update(ev.get("posts", []))
            ids.update((ev.get("mirror") or {}).values())
        return ids

    def reset_context_ids(self) -> set[str]:
        """Posts a short reply like "It's done" / "Not so random, but yes" can confirm."""
        ids: set[str] = set()
        for ev in self.resets:
            ids.update(ev.get("posts", []))
        ids.update(s["post_id"] for s in self.signals if s.get("label") == "reset_hint")
        return ids

    def _event_for_refs(self, refs: set[str]) -> dict[str, Any] | None:
        for ev in reversed(self.resets):
            if refs & set(ev.get("posts", [])):
                return ev
        return None

    def _open_announcement(self, at, within_h: float) -> dict[str, Any] | None:
        for ev in reversed(self.resets):
            if ev["status"] == "announced" and ev.get("announce"):
                dt = parse_ts(ev["announce"]["utc"])
                if 0 <= (at - dt).total_seconds() / 3600 <= within_h:
                    return ev
        return None

    # ---- ingest ------------------------------------------------------
    def ingest(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Classify and store new posts. Returns a list of change records."""
        changes: list[dict[str, Any]] = []
        known = self.known_post_ids()
        for post in sorted(posts, key=lambda p: p["created_at"]):
            pid = str(post["id"])
            if pid in known:
                continue
            refs = set(post.get("referenced") or [])
            author = (post.get("author") or "").lower()
            c = classify(post.get("text", ""), author, list(refs), self.reset_context_ids())
            at = parse_ts(post["created_at"])
            ref = post_ref(post)
            # Standalone short confirms ("Done") often have no reply refs; attach to an
            # open announcement within 48 h instead of dropping them as "other".
            if (
                author in TRUSTED_RESET_AUTHORS
                and c.label == "other"
                and CONTEXT_CONFIRM_RX.search(post.get("text", "") or "")
                and self._open_announcement(at, 48) is not None
            ):
                c = Classification(
                    label="reset_confirmed",
                    labels=["reset_confirmed"],
                    day_n=c.day_n,
                    day_is_reset=c.day_is_reset,
                    reasons=["reset_confirmed: short confirmation near open announcement"],
                )
            if author in TRUSTED_RESET_AUTHORS and c.label in ("reset_announced", "reset_confirmed"):
                ev = self._event_for_refs(refs)
                if c.label == "reset_confirmed":
                    ev = ev or self._open_announcement(at, 48)
                    if ev and not ev.get("confirm"):
                        ev["confirm"] = ref
                        ev["status"] = "confirmed"
                        ev["posts"].append(pid)
                        ev["lag_hours"] = lag_hours(ev)
                        changes.append({"change": "reset_confirmed", "event_id": ev["event_id"], "post": ref})
                    else:
                        ev = self._new_event(ref, at, c, confirmed=True)
                        changes.append({"change": "reset_confirmed", "event_id": ev["event_id"], "post": ref, "new_event": True})
                else:  # announced
                    ev = ev or self._open_announcement(at, 6)
                    if ev:
                        ev["posts"].append(pid)
                        if ev.get("announce") is None:
                            ev["announce"] = ref
                        ev.setdefault("extra_posts", []).append(ref)
                        changes.append({"change": "reset_announced_followup", "event_id": ev["event_id"], "post": ref})
                    else:
                        ev = self._new_event(ref, at, c, confirmed=False)
                        changes.append({"change": "reset_announced", "event_id": ev["event_id"], "post": ref})
                if c.day_n:
                    ev["day_n"] = c.day_n
            elif c.label != "other":
                related = None
                if author in MIRROR_AUTHORS:
                    ev = self._event_for_refs(refs)
                    if ev:
                        related = ev["event_id"]
                        ev.setdefault("mirror", {})[c.label.replace("reset_", "")] = pid
                sig = {
                    "signal_id": f"x:{pid}",
                    **ref,
                    "label": c.label,
                    "labels": c.labels,
                    "day_n": c.day_n or campaign_day(at) if author in TRUSTED_RESET_AUTHORS else c.day_n,
                    "related_event": related,
                    "false_positive": False,
                    "source": "detector",
                    "reasons": c.reasons,
                }
                self.signals.append(sig)
                changes.append({"change": "signal", "label": c.label, "post": ref})
            known.add(pid)
        return changes

    def _new_event(self, ref, at, c, confirmed: bool) -> dict[str, Any]:
        ev = {
            "event_id": f"x:{ref['post_id']}",
            "kind": "banked" if "banked" in ref["text"].lower() else "full",
            "status": "confirmed" if confirmed else "announced",
            "scope": None,
            "triggers": ["campaign_day"] if c.day_n else [],
            "day_n": c.day_n or campaign_day(at),
            "announce": None if confirmed else ref,
            "confirm": ref if confirmed else None,
            "lag_hours": None,
            "posts": [ref["post_id"]],
            "co_signals": [],
            "mirror": {},
            "source": "detector",
            "notes": "auto-detected; review before relying on it",
        }
        self.resets.append(ev)
        return ev

    def save(self) -> None:
        self.resets.sort(key=lambda e: (e.get("announce") or e.get("confirm"))["utc"])
        self.signals.sort(key=lambda s: s["utc"])
        write_jsonl(self.resets_path, self.resets)
        write_jsonl(self.signals_path, self.signals)


def append_raw(data_dir: Path, posts: list[dict[str, Any]]) -> int:
    """Add verbatim fetched posts to data/raw/posts.json (deduplicated by id)."""
    path = Path(data_dir) / "raw" / "posts.json"
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"_note": "Verbatim cache of X posts.", "posts": []}
    have = {p["id"] for p in doc["posts"]}
    added = 0
    for p in posts:
        if p["id"] not in have and p.get("created_at"):
            doc["posts"].append({k: p.get(k) for k in ("id", "author", "created_at", "text", "referenced", "url")})
            have.add(p["id"])
            added += 1
    if added:
        doc["posts"].sort(key=lambda p: p["created_at"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added
