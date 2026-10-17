"""Rule-based post classifier.

Labels (one primary label per post, plus all matching labels):

  reset_confirmed    trusted author says a reset was executed / propagated
  reset_announced    trusted author says a reset is coming (with or without a time)
  reset_hint         strong but non-committal hint (vote, "break the cycle",
                     "possible reset" alerts, community "did we just get a reset?")
  outage             service down / at capacity / incident
  recovery           service back / mitigated / capacity added
  rivalry_hint       Tibo <-> @poteto banter (historically co-occurs with reset days)
  usage_improvement  a Day-N ship or other "more usage" change that is NOT a reset
  other              nothing matched

Rules are deliberately simple and transparent. See docs/patterns.md for the evidence
behind each rule and docs/schema.md for the output format.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TRUSTED_RESET_AUTHORS = {"thsottiaux"}          # can announce/confirm a global reset
MIRROR_AUTHORS = {"codex_resets"}               # third-party mirror; formatted alerts
RIVAL_AUTHORS = {"poteto"}

PRIORITY = [
    "reset_confirmed",
    "reset_announced",
    "reset_hint",
    "outage",
    "recovery",
    "rivalry_hint",
    "usage_improvement",
]


def _rx(*parts: str) -> re.Pattern[str]:
    return re.compile("|".join(parts), re.IGNORECASE)


# Executed-language patterns (stand-alone, no context needed).
CONFIRM_RX = _rx(
    r"\b(resets?|all) (all )?propagated\b",
    r"\ball propagated\b",
    r"put the reset in the bag",
    r"\b(have|has) (now )?(been )?reset(ed)?\b.*\b(usage|limits|rate|everyone|subscriptions)",
    r"\b(i|we)( have|'ve) (now )?reset\b",
    r"\busage limits (have|have now) been reset\b",
    r"\b(usage|rate) limits have (now )?been reset\b",
    r"\bthe reset has been (processed|propagated)",
    r"\breset button pressed\b",
    r"\b(banked )?reset has landed\b",
    r"\ball reset for everyone\b",
    r"\bconfirmed landed\b",
    r"\bdid a sneaky double reset\b",
    r"\bbrand new usage for all\b",
    r"\breset has been propagated\b",
    r"\breset its own rate limits\b",
    r"\b(have )?added a banked reset\b",
    r"\benjoy reset usage limits\b",
    r"\bbutton was already pressed\b",
    r"\bdecision of resetting\b",
)
# Short confirmations that only count when replying to / quoting a known announcement.
CONTEXT_CONFIRM_RX = _rx(
    r"\bit'?s done\b", r"\bdone and dusted\b", r"\ball fixed\b", r"\bnot so random, but yes\b",
    r"^\s*done\b", r"\blanded\b",
)
ANNOUNCE_RX = _rx(
    r"\bglobal reset\b",
    r"\bday \d+\s*/\s*reset\b",
    r"\b(will|we'll|we will|going to|team will)( also)? (do (a|the) )?(full |global )?(banked )?reset",
    r"\breset (will )?land(s|ing)?\b",
    r"\b(we are|we're|are) (once again )?reset(t)?ing\b",
    r"\breset(t)?ing (the )?(usage|rate) limits\b",
    r"\breset incoming\b",
    r"\bloading a banked reset\b",
    r"\bcredit .{0,80}banked reset\b",
    r"\breset will be there\b",
    r"\bwill give (one|a) banked reset\b",
    r"\ba reset and a\b",
    r"\bfull reset of your usage\b",
    r"\busage limit reset for all\b",
    r"\bnew usage reset\b",
    r"\banother reset for\b",
    r"\benjoy a nice reset\b",
    r"\bpromised a reset\b",
    r"\busage reset on the house\b",
    r"\bfully reset again\b",
    r"\bperformative reset\b",
)
CONTEXT_ANNOUNCE_RX = _rx(r"^\s*landing (within|in) (the )?next\b")
NEGATION_RX = _rx(
    r"can'?t (really )?give a reset",
    r"\bno reset\b",
    r"didn'?t get the reset",
    r"not fully applying",
)
HINT_RX = _rx(
    r"\bor a reset\b",
    r"\bbreak the cycle\b",
    r"\bpossible codex reset\b",
    r"\b(random|surprise) (codex )?reset\?",
    r"\bdid (we|i) just get a\b.*reset",
    r"\bneed more resets\b",
    r"\bout of ideas or we are cooking\b",
    r"\bcommunity demands a reset\b",
    r"\bor ship a full reset\b",
)
OUTAGE_RX = _rx(
    r"\b(codex|service|prod) (is |went )?down\b",
    r"\boutage\b",
    r"\bat capacity\b",
    r"\bunder heavy load\b",
    r"\bincident\b",
    r"\bdisruption\b",
    r"^\s*o no\b",
    r"\bdrain(ed|ing)? faster\b",
    r"\bhigh latenc",
    r"didn'?t get the reset",
)
RECOVERY_RX = _rx(
    r"\bback (up|online|in action|and stable)\b",
    r"\bfully resolved\b",
    r"\bmitigated\b",
    r"\brecovered\b",
    r"\bseeing recovery\b",
    r"\bmore capacity online\b",
    r"\bmore compute\b",
    r"\bback to running at expected speeds\b",
)
IMPROVEMENT_RX = _rx(
    r"^\s*day \d+\s*/",
    r"\beffective usage\b",
    r"\bmore usage\b",
    r"\b2x\b",
    r"\b5h limits?\b",
    r"\bgood plans are simple\b",
    r"\bwould you rather have\b",
    r"\bfaster\b.*\bsubscription\b",
)
CODEX_RESETS_ANNOUNCED = re.compile(r"codex reset announced", re.I)
CODEX_RESETS_CONFIRMED = re.compile(r"codex reset confirmed", re.I)
CODEX_RESETS_POSSIBLE = re.compile(r"possible codex reset", re.I)
DAY_N_RX = re.compile(r"^\s*day (\d+)\s*/\s*(reset)?", re.I)


def normalize(text: str) -> str:
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'").replace("&amp;", "&")
    return text.replace("**", "")


@dataclass
class Classification:
    label: str
    labels: list[str] = field(default_factory=list)
    day_n: int | None = None
    day_is_reset: bool = False
    reasons: list[str] = field(default_factory=list)


def classify(
    text: str,
    author: str,
    referenced_ids: list[str] | None = None,
    known_reset_ids: set[str] | None = None,
) -> Classification:
    """Classify one post.

    referenced_ids  ids the post replies to / quotes
    known_reset_ids ids already classified as reset_announced/Day-N-reset (context for
                    short confirmations like "It's done" or "Landing within the next 2 hours")
    """
    author = (author or "").lstrip("@").lower()
    text = normalize(text)
    refs = set(referenced_ids or [])
    ctx = bool(refs & (known_reset_ids or set()))
    labels: set[str] = set()
    reasons: list[str] = []

    def hit(label: str, why: str) -> None:
        labels.add(label)
        reasons.append(f"{label}: {why}")

    m = DAY_N_RX.match(text)
    day_n = int(m.group(1)) if m else None
    day_is_reset = bool(m and m.group(2))

    negated = bool(NEGATION_RX.search(text))

    if author in TRUSTED_RESET_AUTHORS:
        if not negated:
            if (mm := CONFIRM_RX.search(text)):
                hit("reset_confirmed", mm.group(0))
            elif ctx and (mm := CONTEXT_CONFIRM_RX.search(text)):
                hit("reset_confirmed", f"{mm.group(0)!r} replying to a known announcement")
            if (mm := ANNOUNCE_RX.search(text)):
                hit("reset_announced", mm.group(0))
            elif ctx and (mm := CONTEXT_ANNOUNCE_RX.search(text)):
                hit("reset_announced", f"{mm.group(0)!r} in a reset thread")
        if day_n is not None and not day_is_reset:
            hit("usage_improvement", f"Day {day_n}/ ship without 'Reset'")
    elif author in MIRROR_AUTHORS:
        if CODEX_RESETS_CONFIRMED.search(text):
            hit("reset_confirmed", "codex_resets ✅ alert (mirror)")
        elif CODEX_RESETS_ANNOUNCED.search(text):
            hit("reset_announced", "codex_resets 🗓️ alert (mirror)")
        elif CODEX_RESETS_POSSIBLE.search(text):
            hit("reset_hint", "codex_resets ⚠️ possible-reset alert")
    # Hints from anyone (non-trusted authors can never confirm/announce).
    if author not in RIVAL_AUTHORS and (mm := HINT_RX.search(text)):
        hit("reset_hint", mm.group(0))
    if (mm := OUTAGE_RX.search(text)):
        hit("outage", mm.group(0))
    if (mm := RECOVERY_RX.search(text)):
        hit("recovery", mm.group(0))
    if author in RIVAL_AUTHORS and re.search(r"thsottiaux|reset|tibo", text, re.I):
        hit("rivalry_hint", "poteto -> Tibo/reset")
    elif author in TRUSTED_RESET_AUTHORS and re.search(r"@poteto\b", text, re.I):
        hit("rivalry_hint", "Tibo -> @poteto")
    elif re.search(r"poteto", text, re.I) and re.search(r"thsottiaux|tibo", text, re.I):
        hit("rivalry_hint", "third party on the Tibo/poteto beef")
    if author in TRUSTED_RESET_AUTHORS and not labels & {"reset_confirmed", "reset_announced"}:
        if (mm := IMPROVEMENT_RX.search(text)):
            hit("usage_improvement", mm.group(0))
    if negated:
        reasons.append("negation guard matched: " + NEGATION_RX.search(text).group(0))

    ordered = [l for l in PRIORITY if l in labels]
    # A post that reports both a problem and its fix is primarily a recovery post.
    if "outage" in labels and "recovery" in labels and ordered[0] == "outage":
        ordered.remove("recovery")
        ordered.insert(0, "recovery")
    return Classification(
        label=ordered[0] if ordered else "other",
        labels=ordered,
        day_n=day_n,
        day_is_reset=day_is_reset,
        reasons=reasons,
    )
