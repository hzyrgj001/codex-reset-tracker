#!/usr/bin/env python3
"""Rebuild data/resets.jsonl and data/signals.jsonl from the verified cache.

Times and texts come ONLY from data/raw/posts.json (verbatim X API results).
This file holds human curation: which posts belong to the same reset event,
kind/scope/trigger labels, and notes. Signals are auto-classified by the same
classifier the detector uses, with a few documented overrides.

    python scripts/build_dataset.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codex_reset_tracker.classifier import classify  # noqa: E402
from codex_reset_tracker.store import lag_hours, post_ref, write_jsonl  # noqa: E402
from codex_reset_tracker.timeutil import TAIPEI, campaign_day, parse_ts  # noqa: E402

POSTS = {p["id"]: p for p in json.loads((ROOT / "data/raw/posts.json").read_text())["posts"]}
for _p in POSTS.values():
    _p.setdefault("author", "unknown")
    _p.setdefault("referenced", [])

# (announce, confirm, extra_posts, kind, scope, triggers, notes, co_signals, mirror)
E = lambda a, c, kind="full", scope=None, triggers=(), notes="", extra=(), co=(), mirror=None: dict(  # noqa: E731
    a=a, c=c, kind=kind, scope=scope, triggers=list(triggers), notes=notes, extra=list(extra), co=list(co), mirror=mirror or {})

EVENTS = [
    # ---- before the 28-day series -------------------------------------------------
    E(None, "1968163721034994139", scope="gpt-5-codex users", triggers=["capacity"], notes="Make-up for slowdowns while provisioning GPUs."),
    E(None, "1986166501435711936", scope="Codex", triggers=["outage", "recovery"], notes="Global outage ~30 min, resolved, then reset."),
    E(None, "1992370994028388670", scope="all Codex users", triggers=["outage"], notes="High latency in/near the US."),
    E(None, "1995988609896513743", scope="everyone in Codex", triggers=["incident"], notes="Reset used as mitigation; 'propagate over the next 10 mins'."),
    E(None, "2001114683047317723", scope="everyone", triggers=["outage"], notes="'you know the drill' after a disruption."),
    E(None, "2002137269134819610", scope="Codex", triggers=["migration"], notes="Usage-tracking/billing rewrite."),
    E(None, "2004100061933064395", scope="Codex users", triggers=["holiday"], notes="Holiday reset + temporary 2X limits until Jan 1."),
    E("2028649088594436225", None, scope="Codex", triggers=["outage", "recovery"], notes="'Team will reset rate limits' after a ~8 min cyber-risk blocking bug. No completion post found."),
    E("2029308599835738218", None, scope="Plus + Pro", triggers=["bug_compensation"], notes="2X promo not applied to ~9% of Plus/Pro; 'are reseting'. No completion post found."),
    E(None, "2030474136024400173", scope="Plus + Pro", triggers=["investigation"], notes="Usage-drain reports."),
    E("2031216405266481489", "2031605592352313567", scope="Codex", triggers=["outage", "recovery"], notes="'You have come to expect it' -> 'Reset button pressed'."),
    E(None, "2037346989244096581", scope="all plans", triggers=["launch"], notes="Plugins launch."),
    E(None, "2039248564967424483", scope="all plans", triggers=["investigation"], notes="Rate-limit hit rate up, cause unknown."),
    E("2041655710346572085", None, scope="Codex", triggers=["milestone"], notes="3M weekly users; promised a reset every +1M users until 10M."),
    E("2042299371602264319", None, scope="Codex", triggers=["launch"], notes="$100 plan; 'resetting the limits again too as I mentioned yesterday'."),
    E(None, "2044943514832871564", scope="all plans", triggers=["anniversary"], notes="Codex 1-year anniversary."),
    E("2046367145588916687", None, scope="Codex", triggers=["outage", "recovery"], notes="'rate limit reset incoming' after ~10 min incident. No completion post found."),
    E(None, "2048997818673537399", scope="all paid plans", triggers=["celebration"], notes="'Don't just reset ... it costs money' then resets."),
    E(None, "2055707616605835333", scope="all paid plans", triggers=["weekend"]),
    E(None, "2058280452851638313", scope="all accounts", triggers=["investigation"], notes="Cache-hit regression rolled back."),
    E(None, "2061106703446450392", scope="all paid ChatGPT subscriptions"),
    E(None, "2062329981548802523", scope="all paid plans", triggers=["outage"], notes="Three small reliability incidents in 24 h."),
    E(None, "2067399435009622521", scope="Codex", triggers=["celebration"], notes="'sneaky double reset': full reset + one banked reset."),
    E("2070653282440405046", None, scope="all Codex users", triggers=["investigation"], notes="'on the house ... in the next few hours'."),
    E(None, "2071381664853319742", scope="everyone (Codex)", triggers=["investigation"], notes="Hard reset; users had stacked banked resets."),
    E("2071740419030053227", None, scope="Codex", triggers=["investigation"], notes="Full reset 'in the next hour' + one banked credit."),
    E("2075330198887940337", None, scope="ChatGPT Work + Codex", triggers=["growth"], notes="'Propagating in the next hour'."),
    E(None, "2075641131002700120", scope="Codex + ChatGPT Work", triggers=["growth"], notes="Also promised 'another one ... later in the day'."),
    E("2075820987833274448", None, scope="ChatGPT Work + Codex", triggers=["growth", "weekend"], notes="Fulfils the same-day promise; 'over next 30 minutes'."),
    E(None, "2076418567143408112", kind="banked", scope="500k users", triggers=["makeup"], notes="Banked reset for users hit by a banked-reset bug."),
    E(None, "2076735790567338203", kind="banked", scope="everyone", triggers=["milestone"], notes="7M active users."),
    E("2077114635308986427", None, scope="all", triggers=["milestone"], notes="8M active users; 'once again resetting'."),
    E("2077607697487188198", None, scope="Codex + ChatGPT Work", triggers=["milestone"], notes="9M; 'back in a few minutes'."),
    E(None, "2078320950488297917", scope="all paid", triggers=["weekend", "growth"], notes="'Oops... I did it again.'"),
    E("2079609157934886975", None, scope="paid Codex + ChatGPT Work", triggers=["milestone"], notes="10M; 'Lands in the next hour'."),
    E(None, "2081096447718723984", scope="all Codex + ChatGPT Work", triggers=["outage", "recovery"], notes="Almost-global outage 2-4am; 'We learn. We reset.'"),
    E(None, "2081940052154933696", scope="all paid", notes="'Back at the laptop.'"),
    E(None, "2082317452755751098", scope="all ChatGPT Work + Codex", triggers=["efficiency"]),
    E(None, "2083395449814229287", scope="Codex + ChatGPT Work", triggers=["weekend", "efficiency"]),
    E(None, "2086188036493344823", scope="all paid", triggers=["launch"], notes="GPT-5.6 Sol everywhere."),
    E("2086189414292865249", "2086972933566857393", scope="all paid", triggers=["promise"], notes="'another performative reset on Monday' -> Monday reset."),
    E("2087706104814023111", None, scope="everyone", triggers=["milestone"], notes="15M; 'Landing in the next hour or so'."),
    E("2090766694897619318", "2090964822422949999", kind="banked", scope="every Codex + ChatGPT Work user", triggers=["milestone", "weekend"], extra=["2090947196107764189"], notes="20M milestone banked reset."),
    E("2091407991736332689", "2091688655828246890", scope="all paid", triggers=["investigation"], extra=["2091412393368945027", "2091413240337326588", "2091709346371838240"], notes="Rate-limit fixes; time corrected to ~2pm PT; Business propagation follow-up."),
    E(None, "2092316228497063958", scope="Codex", triggers=["silent"], co=["2092256496063033418"], notes="Unannounced: a user asked 'random Codex reset?' and Tibo replied 'Not so random, but yes'."),
    E(None, "2093014447833116908", scope="all ChatGPT Work + Codex"),
    E("2093801758665715784", "2093811840258293947", scope="all paid", triggers=["investigation"], notes="Follow-up: 'button was already pressed today' (planned 25M celebration moved to next day)."),
    E(None, "2094252447271366730", scope="all paid", triggers=["milestone"], notes="25M active users; 'The Reset Company'."),
    E("2095651088502591861", None, kind="banked", scope="paid plans without Astra access", triggers=["launch"], notes="One banked reset per day without Astra. Help-center dates (Sep 3 & 4) via codexlimits.com."),
    E("2096035437299237298", None, kind="banked", scope="Plus, Pro, Business", triggers=["launch", "weekend"], notes="Astra rolled out; 'Lands end of day'."),
    E("2097043464538264003", "2097174560412246215", scope="all paid", triggers=["launch"], notes="Astra week."),
    E("2097752790177370535", None, kind="makeup", scope="users whose banked reset failed", triggers=["makeup"], notes="Replacement banked reset + apology email."),
    E("2098612714704891959", "2098685367058612394", scope="Astra users", triggers=["quality_fix"]),
    # ---- since 2026-09-20 ---------------------------------------------------------
    E("2102254445082116335", None, kind="banked", scope="Plus, Pro, Business", triggers=["launch", "promise"], extra=["2102463847714247142"],
      notes="Promised 'a reset for Tuesday'; the GPT-6 Sol/Luna launch post says 'We are loading a banked reset'. No separate completion post found."),
    E("2103637477760311522", "2103911959544610829", scope="all paid Codex + ChatGPT Work", triggers=["outage", "recovery", "weekend"],
      co=["2103620061156290622", "2103622639386574979"], notes="'codex is down' -> 'o no :(' -> 'o yes... back in action and we'll reset'."),
    E("2105843926221660585", "2106131810921136451", scope="all paid ChatGPT accounts", triggers=["capacity", "recovery"], co=["2105464274747527543"],
      notes="GPT-6.1 Sol load spike; scheduled for 10am PT next day."),
    E("2106233145163141249", "2106239435461579088", kind="makeup", scope="Pro 500 accounts that missed the Oct 2 reset", triggers=["makeup"]),
    E(None, "2107676072871600470", scope="Codex + ChatGPT Work", triggers=["campaign_day", "vote"], co=["2107578625419866469", "2107576143285219799"],
      notes="Day 2: four ships, then a community vote ('Four updates or a reset. Or both.') forced a reset. Poll -> confirm 6.45 h."),
    E("2107913674593644711", "2108040921044639779", kind="banked", scope="everyone's paid accounts", triggers=["campaign_day", "milestone"],
      co=["2108019899335667799"], notes="Day 3: GPT-6 in Chat + 40M active users."),
    E("2109045220411351517", "2109132167112782291", scope="Codex + ChatGPT Work", triggers=["campaign_day"], extra=["2109045392684032299"],
      mirror={"announced": "2109045550175687075", "confirmed": "2109132297953853668"}, notes="'Day 6/ Reset' + 'Global reset by EOD' -> 'Put the reset in the bag'."),
    E("2109812216212099456", "2109873287853707513", scope="Codex + ChatGPT Work", triggers=["campaign_day", "rivalry"], extra=["2109812360596865224"],
      co=["2109873307722121591", "2109876916622872762", "2109900862978138370", "2109892247580000595"],
      mirror={"announced": "2109812542822367364", "confirmed": "2109873437149655501"}, notes="Confirm followed 4 s later by 'Mashed @poteto on the house.'"),
    E("2110595484180214059", "2110618732666257557", scope="Codex + ChatGPT Work", triggers=["campaign_day", "rivalry", "silence"], extra=["2110595554036400151"],
      co=["2110580418898780462", "2110584758950588537", "2110591392691159317", "2110612709423362109"],
      mirror={"announced": "2110595789282021677", "confirmed": "2110618853877117162"},
      notes="After >24 h of silence (theo: 'Anyone check in on @thsottiaux'), poteto 'come back', Tibo 'I made it alive', then Day 10/ Reset."),
    E("2111492673890824348", "2111566005684289735", scope="Codex + ChatGPT Work", triggers=["campaign_day"],
      extra=["2111492738025959922"],
      mirror={"announced": "2111492941046771971", "confirmed": "2111566174722941349"},
      notes="'Day 13/ Le limit reset' + 'Landing sometime today by EOD PST' -> standalone 'Done' (~4.85 h later)."),
]

SIGNAL_OVERRIDES = {
    "2110151690641154499": {"day_n": 9, "notes": "Text says 'Day 8/' but it was posted on Day 9 (PT); codex_resets lists it as Day 9."},
    "2110952027505270882": {"false_positive": True, "notes": "Mirror predicted a reset by Oct 17 05:00 UTC after 'break the cycle'. Day 12 shipped improvements instead."},
    "2110951585983631505": {"notes": "Reply to a parody ('I miss the old Tibo, reset the usage Tibo'). The even-day reset cadence broke on Day 12."},
    "2110971985417441512": {"notes": "Ambiguous teaser; no reset followed within 24 h."},
    "2105672058269212820": {"notes": "Negative signal: 'I can't really give a reset' (dots usage is virtually unlimited)."},
    "2107576143285219799": {"label": "reset_hint", "labels": ["reset_hint"], "notes": "Day 2 vote: improvements vs reset; 'reset' won."},
    "2110580418898780462": {"notes": "Tibo silence >24 h; a Day-10 reset followed ~1 h later."},
    "2105173168281506088": {"notes": "Per quotaalert.com this is the credit-grant + extra banked reset confirmation; the post itself has no reset wording. Uncertain."},
    "2106845241357824205": {"notes": "Start of the 28-day series: each day an improvement OR a full reset."},
    "2109152716954222849": {"notes": "Pro poll: '5h limits, 2X week usage' vs 'no 5h limits, same usage'. Not a reset."},
    "2111337472349343856": {"notes": "Tibo -> @poteto banter earlier on Oct 17; Day 13 reset later that UTC evening."},
    "2109892247580000595": {"notes": "'simple plan' for significantly more usage. Not a reset (as of 2026-10-17)."},
}
KEEP_OTHER = {"2105672058269212820", "2110580418898780462", "2105173168281506088", "2110626828260192425", "2110989212686405684", "2111351614170870003", "2106239435461579088"}


def ref(pid):
    return post_ref(POSTS[pid]) if pid else None


def main() -> None:
    resets, used = [], set()
    for ev in EVENTS:
        a, c = ref(ev["a"]), ref(ev["c"])
        anchor = ev["a"] or ev["c"]
        posts = [p for p in [ev["a"], ev["c"], *ev["extra"]] if p]
        used.update(posts)
        used.update(ev["mirror"].values())
        first = parse_ts((a or c)["utc"])
        row = {
            "event_id": f"x:{anchor}",
            "kind": ev["kind"],
            "status": "confirmed" if c else "announced",
            "scope": ev["scope"],
            "triggers": ev["triggers"],
            "day_n": campaign_day(first) if "campaign_day" in ev["triggers"] else None,
            "announce": a,
            "confirm": c,
            "lag_hours": None,
            "first_post_hour_taipei": first.astimezone(TAIPEI).hour,
            "weekday_taipei": first.astimezone(TAIPEI).strftime("%a"),
            "posts": posts,
            "extra_posts": [ref(p) for p in ev["extra"]],
            "co_signals": [f"x:{s}" for s in ev["co"]],
            "mirror": ev["mirror"],
            "source": "curated",
            "notes": ev["notes"],
        }
        row["lag_hours"] = lag_hours(row)
        resets.append(row)
    # Keep events the detector added later that are not curated yet (review, then move them into EVENTS).
    existing = ROOT / "data/resets.jsonl"
    if existing.exists():
        for line in existing.read_text().splitlines():
            if line.strip():
                ev = json.loads(line)
                if ev.get("source") == "detector" and not set(ev.get("posts", [])) & used:
                    resets.append(ev)
                    used.update(ev.get("posts", []))
    resets.sort(key=lambda r: (r["announce"] or r["confirm"])["utc"])
    related = {s: r["event_id"] for r in resets for s in [x[2:] for x in r["co_signals"]] + list(r["mirror"].values())}
    signals, ctx = [], set(used)
    for pid, post in sorted(POSTS.items(), key=lambda kv: kv[1]["created_at"]):
        if pid in used and pid not in related:
            continue
        cl = classify(post["text"], post["author"], post["referenced"], ctx)
        if cl.label in ("reset_hint",):
            ctx.add(pid)
        sig = {"signal_id": f"x:{pid}", **ref(pid), "label": cl.label, "labels": cl.labels,
               "day_n": cl.day_n or (campaign_day(parse_ts(post["created_at"])) if post["author"] == "thsottiaux" else None),
               "related_event": related.get(pid), "false_positive": False, "source": "curated", "notes": ""}
        sig.update(SIGNAL_OVERRIDES.get(pid, {}))
        if sig["label"] == "other" and pid not in KEEP_OTHER and pid not in related:
            continue
        if pid in used and sig["label"] in ("reset_announced", "reset_confirmed") and post["author"] == "codex_resets":
            sig["notes"] = sig["notes"] or "codex_resets mirror alert (third party)."
        signals.append(sig)
    write_jsonl(ROOT / "data/resets.jsonl", resets)
    write_jsonl(ROOT / "data/signals.jsonl", signals)
    print(f"resets: {len(resets)} ({sum(r['status'] == 'confirmed' for r in resets)} confirmed)  signals: {len(signals)}")
    missing = set(POSTS) - used - {s['post_id'] for s in signals}
    print("cached posts not used:", sorted(missing))


if __name__ == "__main__":
    main()
