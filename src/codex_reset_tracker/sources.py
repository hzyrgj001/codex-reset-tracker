"""Post sources: exported files (no keys needed) or the X API v2 (X_BEARER_TOKEN).

Every source yields normalized posts:
  {"id", "author", "created_at", "text", "referenced": [ids], "url"}
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

DEFAULT_QUERIES = [
    'from:thsottiaux (reset OR "Day" OR propagated OR "It\'s done" OR landing OR down OR capacity OR "back up" OR usage) -is:retweet',
    'from:codex_resets ("reset announced" OR "reset confirmed" OR "Possible Codex reset") -is:retweet',
    "from:poteto (thsottiaux OR reset) -is:retweet",
    '"thsottiaux" ("Codex down" OR "at capacity" OR "random reset" OR "did we just get") -is:retweet',
]

KNOWN_USER_IDS = {
    "1953337039510003712": "thsottiaux",
    "2094439054205157376": "codex_resets",
    "2832427459": "poteto",
}


def _norm_v2(payload: dict[str, Any]) -> list[dict[str, Any]]:
    users = dict(KNOWN_USER_IDS)
    for u in (payload.get("includes") or {}).get("users", []):
        users[u["id"]] = u["username"]
    out = []
    for p in payload.get("data") or []:
        out.append(_norm_one(p, users))
    return out


def _norm_one(p: dict[str, Any], users: dict[str, str] | None = None) -> dict[str, Any]:
    users = users or KNOWN_USER_IDS
    text = (p.get("note_tweet") or {}).get("text") or p.get("text") or p.get("full_text") or ""
    author = p.get("author") or p.get("username") or users.get(str(p.get("author_id", "")), None)
    if not author and p.get("url"):
        parts = urllib.parse.urlparse(p["url"]).path.strip("/").split("/")
        author = parts[0] if parts and parts[0] != "i" else None
    refs = p.get("referenced")
    if refs is None:
        refs = [r["id"] for r in p.get("referenced_tweets") or []]
    created = p.get("created_at")
    if created and created.endswith(".000Z"):
        created = created.replace(".000Z", "Z")
    post = {
        "id": str(p["id"]),
        "author": (author or "unknown").lstrip("@"),
        "created_at": created,
        "text": text,
        "referenced": [str(r) for r in refs],
    }
    post["url"] = p.get("url") or f"https://x.com/{post['author']}/status/{post['id']}"
    return post


def _parse_obj(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, dict):
        if "data" in obj:
            return _norm_v2(obj)
        if "posts" in obj:
            return [_norm_one(p) for p in obj["posts"]]
        return [_norm_one(obj)]
    if isinstance(obj, list):
        return [_norm_one(p) for p in obj]
    return []


def load_file(path: Path) -> list[dict[str, Any]]:
    """Accepts: X API v2 response JSON (also when wrapped in extra text, as agent tools often save it),
    data/raw/posts.json, a JSON list, or JSONL (one post per line)."""
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        return _parse_obj(json.loads(raw))
    except json.JSONDecodeError:
        pass
    lines = [l for l in raw.splitlines() if l.strip()]
    try:
        rows = [json.loads(l) for l in lines]
        if rows and all(isinstance(r, dict) and "id" in r for r in rows):
            return [_norm_one(r) for r in rows]
    except json.JSONDecodeError:
        pass
    dec, out, i = json.JSONDecoder(), [], 0
    while (j := min([k for k in (raw.find("{", i), raw.find("[", i)) if k >= 0], default=-1)) >= 0:
        try:
            obj, end = dec.raw_decode(raw, j)
        except json.JSONDecodeError:
            i = j + 1
            continue
        out.extend(_parse_obj(obj) if isinstance(obj, (dict, list)) and ("data" in obj or "posts" in obj or isinstance(obj, list)) else [])
        i = end
    return out


def load_files(paths: Iterable[Path]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for p in paths:
        for post in load_file(Path(p)):
            if post.get("created_at"):
                seen[post["id"]] = post
    return list(seen.values())


def fetch_x_api(queries: list[str] | None = None, since_id: str | None = None,
                token: str | None = None, max_results: int = 100) -> list[dict[str, Any]]:
    """X API v2 recent search (last 7 days). Requires X_BEARER_TOKEN; tier limits apply."""
    token = token or os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise RuntimeError("X_BEARER_TOKEN is not set")
    posts: dict[str, dict[str, Any]] = {}
    for q in queries or DEFAULT_QUERIES:
        params = {
            "query": q,
            "max_results": str(max(10, min(max_results, 100))),
            "tweet.fields": "created_at,author_id,referenced_tweets,note_tweet",
            "expansions": "author_id",
            "user.fields": "username",
        }
        if since_id:
            params["since_id"] = since_id
        url = "https://api.x.com/2/tweets/search/recent?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "codex-reset-tracker/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        for p in _norm_v2(payload):
            posts[p["id"]] = p
    return list(posts.values())
