# Pattern catalogue

Patterns observed in public X posts that predict or coincide with **global Codex / ChatGPT Work
usage resets** announced by Tibo ([@thsottiaux](https://x.com/thsottiaux)). Every number below is computed
from [`data/resets.jsonl`](../data/resets.jsonl) and [`data/signals.jsonl`](../data/signals.jsonl)
(snapshot: **2026-10-17 18:30 Taipei / 10:30 UTC**). The full dated table is in [timeline.md](timeline.md).

> Unofficial and unaffiliated with OpenAI or SpaceXAI. These are correlations in public posts,
> not insider knowledge. Resets are entirely at OpenAI's discretion.

**Dataset at a glance**: 62 reset events from 2025-09-17 to 2026-10-15, of which **45 are confirmed**
(40 full, 5 banked or make-up) and 17 are announced only. The announced-only ones are mostly
"landing in the next hour" posts with no separate completion post. 9 events fall since 2026-09-20,
and 8 of those are confirmed. Median gap between confirmed resets: **4.8 days** (n=44 gaps).

Evidence strength: ●●● strong (repeated and still holding) · ●● moderate · ● weak or coincidental.

---

## P1. Every-other-day "Day N/ Reset" cadence ●●● (broken on Day 12)

Tibo started a 28-day series on 2026-10-04 ([post](https://x.com/thsottiaux/status/2106845241357824205)):
*"each day we'll either ship one thing that is a clear improvement … or ship a full reset."*
Day N is counted on the **Pacific** calendar (Day 1 = Oct 5 PT; Day 28 = Nov 1 PT).

| Day | Result | Post |
|---|---|---|
| 1 | improvement (≈50% faster default speed) | [x](https://x.com/thsottiaux/status/2107158998495748264) |
| **2** | **full reset** after the community vote | [x](https://x.com/thsottiaux/status/2107676072871600470) |
| **3** | **banked reset** (40M users) + GPT-6 in Chat | [x](https://x.com/thsottiaux/status/2107913674593644711) |
| 4 | improvement (instant steering) | [x](https://x.com/thsottiaux/status/2108275041276420573) |
| 5 | improvement (composer predictions) | [x](https://x.com/thsottiaux/status/2108645667451318747) |
| **6** | **full reset**, "Day 6/ Reset" | [x](https://x.com/thsottiaux/status/2109045220411351517) |
| 7 | improvement (500k context) | [x](https://x.com/thsottiaux/status/2109430343346581527) |
| **8** | **full reset**, "Day 8/ Reset" | [x](https://x.com/thsottiaux/status/2109812216212099456) |
| 9 | improvement (disk usage −60%; the post text says "Day 8/") | [x](https://x.com/thsottiaux/status/2110151690641154499) |
| **10** | **full reset**, "Day 10/ Reset" | [x](https://x.com/thsottiaux/status/2110595484180214059) |
| 11 | improvement (fewer "model at capacity" errors) | [x](https://x.com/thsottiaux/status/2110750421367287996) |
| 12 | **improvement, not a reset** (effective usage via caching) | [x](https://x.com/thsottiaux/status/2111244596131111253) |
| 13 | nothing posted as of 2026-10-17 10:30 UTC | — |

* Even days: 4 of 6 were resets (2, 6, 8, 10). Days 6, 8 and 10 ran 3 for 3 in a row; Day 4 and Day 12 were not resets.
* Odd days: no full resets. Day 3 was a banked reset only.
* The tendencies check does **not** call "resets land on even Day numbers" supported. Of confirmed resets that have a Day number, 4 of 5 are even (Days 2, 6, 8, 10; Day 3 is the odd one). Five trials is under the 10-trial line, so the verdict is **insufficient data** (80% vs 50% expected, one-sided p=0.188).
* **Break:** on 2026-10-16 04:30 UTC (12:30 TPE), replying to a parody of him, Tibo wrote *"Can't argue with that, Let's break the cycle."*
  ([post](https://x.com/thsottiaux/status/2110951585983631505); parody: [post](https://x.com/maria_rcks/status/2110880198660882719)).
  Day 12 then shipped a usage improvement, not a reset. The detector halves the even-day weight once "break the cycle" appears after the last reset.

## P2. Two-post announcement format ●●●

Since Day 6, every campaign reset opened with a bare **"Day N/ Reset"** post, followed within a minute by a
**self-reply that gives the window**:

| Day | Day post (UTC) | Window reply | Gap |
|---|---|---|---|
| 6 | 22:15:39 | "Global reset by EOD." | 41 s |
| 8 | 01:03:25 | "Global reset landing by EOD PST time." | 34 s |
| 10 | 04:55:51 | "Landing within the next 2 hours" | 16 s |

Short replies like "Landing within the next 2 hours" contain no reset keyword. The classifier only counts them
when they reply to a known reset post (`CONTEXT_ANNOUNCE_RX`).

## P3. Announce → confirm lag ●●● (getting shorter)

All events with both an announcement and a confirmation (n=14): **median 8.6 h**, min 0.42 h, max 51.9 h.

Since 2026-09-20, excluding the Pro 500 make-up, each lag was shorter than the one before:

| Event | Lag |
|---|---|
| 09-26 outage reset | 18.18 h |
| 10-02 capacity reset | 19.07 h |
| Day 3 banked | 8.43 h |
| Day 6 | 5.76 h |
| Day 8 | 4.04 h |
| Day 10 | 1.54 h |

Promised windows were met. "By EOD" was confirmed before midnight PT on both Day 6 (21:01 PDT) and Day 8 (22:06 PDT).
"Within the next 2 hours" was confirmed after 1 h 32 m. The scheduled reset at "10am PST" on Oct 2 was confirmed at 14:18 PDT.
Note that Tibo writes "PST" but means Pacific time, which is PDT in October.

## P4. Confirmation wording and quote-tweets ●●●

Confirmations are short and usually **quote the announcement**. Since Sep 20, 6 of 7 announced-then-confirmed events
were confirmed by a quote-tweet; the exception is Sep 26.
Phrases seen: "Resets all propagated", "Reset all propagated. Enjoy.", "the reset has been processed",
"Confirmed landed across all accounts", "Put the reset in the bag. All propagated.", "It's done.", "Done and dusted".
Rule: executed-language regexes, and "done/landed/fixed" only when the post quotes or replies to a known announcement.

## P5. Morning announce window in Taipei (≈06:00–13:00 TPE = 22:00–05:00 UTC) ●●●

* Since 2026-09-20, the first post of 8 of 9 events fell between 06:00 and 13:00 TPE. The exception was the Day 3 banked reset at 03:19 TPE.
* All-time: 35 of 62 events (56%) fell in that window. Against a flat 7/24 (29.2%) baseline that is **supported** (56.5% vs 29.2%, one-sided p<0.001, n=62).
* The campaign Day-N reset posts drifted about 3 h later each time: 06:15 → 09:03 → 12:55 TPE (Pacific: 15:15 → 18:03 → 21:55).
* Confirmations since Sep 20 landed between 02:17 and 14:28 TPE.
* See the hour-of-day heatmap in the visualizer, which shows both UTC and your local time.

## P6. @poteto rivalry coincidence ● (it coincides with resets but does not predict them)

There is a running Tibo ↔ lauren ([@poteto](https://x.com/poteto)) "beef". A fan built a battle site for it ([post](https://x.com/RealFlyingHigh/status/2107528151006089600)).

* **Day 8:** confirm at 05:06:06 UTC, then 4 s later *"Mashed @poteto on the house."* ([x](https://x.com/thsottiaux/status/2109873307722121591)).
  poteto replied *"back for more?"* at +14 min ([x](https://x.com/poteto/status/2109876916622872762)) and *"me vs the reset guy"* at +1 h 50 m ([x](https://x.com/poteto/status/2109900862978138370)).
* **Day 10:** this followed more than 24 h of silence from Tibo, which theo pointed out ([x](https://x.com/theo/status/2110580418898780462)).
  poteto posted *"come back"* ([x](https://x.com/poteto/status/2110584758950588537)) and Tibo replied *"I made it alive"* ([x](https://x.com/thsottiaux/status/2110591392691159317)), 16 min before "Day 10/ Reset".
  poteto's *"good"* came 24 min before the confirmation ([x](https://x.com/poteto/status/2110612709423362109)).
* **Day 3:** poteto wrote *"I think we might need more resets"* ([x](https://x.com/poteto/status/2108019899335667799)) 1 h 23 m before the banked-reset confirmation.
* **Day 6:** no poteto exchange was found near the reset.
* **Counter-examples:** banter on non-reset days (Oct 6, Oct 8 = Day 4) and *"Small @poteto speaks big facts"* on Day 13 ([x](https://x.com/thsottiaux/status/2111337472349343856)) with no reset.

Score: banter came within ±2 h of 3 of 5 campaign resets, but it also happens on non-reset days. Weight: 0.05.

The co-occurrence claim "poteto banter tends to land within two hours of a reset" **is supported** on the stored signals: 10 of 14 rivalry posts fall inside ±2 h of an announcement or confirmation, against 3.0% of the timeline (one-sided p<0.001). n=14 is a small sample, and these are the posts the dataset kept, so this is co-occurrence, not a forecast. The likelihood heuristic still uses the 0.05 rivalry weight, not this verdict.

## P7. Outage → recovery → reset ●●●

Outage or recovery is the most common reset trigger: 9 events are tagged `outage`, 7 `recovery`, and 3 more `incident`/`capacity`.
The usual sequence is outage acknowledged → recovery post → reset promised *in the recovery post*.

* 2026-09-25/26: *"We are aware that codex is down"* (22:58 UTC, [x](https://x.com/thsottiaux/status/2103620061156290622)) → *"o no :("* →
  *"o yes… we're back in action and we'll reset usage limits"* (00:07 UTC, +69 min, [x](https://x.com/thsottiaux/status/2103637477760311522)) → *"Resets all propagated"* (+18 h).
* 2026-10-01/02: GPT-6.1 Sol *"under heavy load … more capacity online"* ([x](https://x.com/thsottiaux/status/2105464274747527543)) → global reset scheduled ([x](https://x.com/thsottiaux/status/2105843926221660585)).
* Earlier: 2026-03-03 *"Codex is back up … Team will reset rate limits"*; 2026-03-10/11 *"fully resolved … reseting rate limits in a bit"* → *"Reset button pressed"*;
  2026-04-20 *"incident is mitigated … rate limit reset incoming"*; 2026-07-25 *"almost global outage … We learn. We reset."*
* **Exception:** the Day 11 capacity-error fix ([x](https://x.com/thsottiaux/status/2110750421367287996)) *was* that day's ship. No reset followed.
  A planned capacity improvement is different from an incident recovery.

Separate Tibo outage/recovery posts (clustered within 6 h) are only three episodes. Two were followed by a reset within 48 h (Sep 25, Oct 1); Day 11 was not. 2 of 3 against 28.7% of the timeline is **insufficient data**, so the tracker does not treat "outage → reset" as a supported tendency. Older resets that mention an outage inside the reset post itself are not extra trials.

## P8. "Let's break the cycle" and the missing Day-12 reset ●●

See P1. Hints posted after the break did not lead to a reset:
* "Let's break the cycle." (Oct 16 04:30 UTC)
* codex_resets: *"⚠️ Possible Codex reset by Oct 17, 05:00 UTC"* ([x](https://x.com/codex_resets/status/2110952027505270882)). **False positive.**
* *"Either we are out of ideas or we are cooking. Time will tell"* ([x](https://x.com/thsottiaux/status/2110971985417441512)). No reset within 24 h.

## P9. Personal reset button (banked) vs global reset ●●●

Track these separately (`kind` field):
* **Global/full reset**: OpenAI refills everyone's usage. Phrases: "reset usage limits for all", "Global reset", "Reset button pressed", "all propagated".
* **Banked reset**: a credit goes into your "reset bank" and *you* press a reset button in the desktop app or on the web ([Jul 13 post](https://x.com/thsottiaux/status/2076735790567338203): "You can apply the reset in the desktop app or on web").
  This does **not** refill usage automatically. Banked events in the data: Jul 12 (500k users), Jul 13 (7M), Aug 21 (20M), Sep 3 and Sep 5 (Astra), Sep 22 (GPT-6 Sol/Luna launch) and Day 3 (40M).
  The DevDay on-stage banked reset (Sep 29) is reported by [codexlimits.com](https://codexlimits.com/reset-history), but we found no X post for it, so it is **not** in the data.
* **Make-ups**: Pro 500 accounts missed the Oct 2 reset and Tibo said "All fixed" 25 min later ([x](https://x.com/thsottiaux/status/2106239435461579088)). On Sep 9, failed banked redemptions were replaced.
* "My reset button" in Tibo's posts (e.g. Day 10) refers to *his* global button.

## P10. Milestones, launches, and weekends ●●

* Trigger counts across 62 events: milestone 9, outage 9, investigation 8, launch 7, weekend 7, campaign_day 5, growth 4, make-up 3.
* Milestone resets followed active-user counts: 3M (a promise of a reset every +1M users up to 10M), then 7M, 8M, 9M, 10M, 15M, 20M, 25M and 40M.
* Weekend phrasing ("Enjoy the weekend", "Have a fantastic weekend") appears in 7 events.

## P11. Silent resets that users notice first ●

On 2026-08-25 a user asked *"Did we just get a random Codex reset?"* ([x](https://x.com/s_batzoglou/status/2092256496063033418)).
Tibo replied *"Not so random, but yes"* ([x](https://x.com/thsottiaux/status/2092316228497063958)).
The classifier labels community "did we just get a reset?" posts `reset_hint`, and a short Tibo "yes" reply to one counts as confirmation.

## P12. Polls and "more usage" posts are not resets ●●● (main false-positive risk)

* Oct 11 Pro poll *"5h limits, 2X week usage"* vs *"no 5h limits, same usage"* ([x](https://x.com/thsottiaux/status/2109152716954222849)); his follow-up said the result confused him ([x](https://x.com/thsottiaux/status/2109439315570999598)).
* Oct 13 *"Good plans are simple. I have one that should result in significantly more usage for everyone."* ([x](https://x.com/thsottiaux/status/2109892247580000595)). Not delivered as of Oct 17.
* Day 12 *"increase the effective usage you get"*.
* Oct 1 *"I can't really give a reset"* for dots ([x](https://x.com/thsottiaux/status/2105672058269212820)). This is an explicit negative, and the negation guard catches it.

All of these are labelled `usage_improvement` (or `other`), never `reset_*`.

## P13. Weekday the reset lands on — Monday is not supported

Counts use each event's **announcement** time, or the confirmation time when there was no announcement. Computed for 2026-10-17 10:30 UTC (`weekday` in the CLI JSON). Pacific time is America/Los_Angeles, Tibo's zone.

Confirmed resets, all-time, **Pacific** (n=45):

| Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|
| 6 | 6 | 6 | 5 | 8 | 10 | 4 |

Monday is 6/45 = **13.3%**, against 1/7 = **14.3%** expected if weekdays were flat. One-sided binomial p=0.637. The seeded claim "Tibo tends to reset on Mondays" (a community observation) is **not supported**. Saturday is the busiest day (10/45 = 22.2%) and is still short of p<0.05 (p=0.100), so the spread is compatible with a flat week. The likelihood heuristic adds a weekday weight only when a weekday tendency's verdict is `supported`. On this dataset it does not add one.

The same 45 confirmed resets in **Taipei** (n=45): Mon 3, Tue 6, Wed 7, Thu 6, Fri 5, Sat 7, Sun 11. Sunday leads because a Pacific evening is already the next calendar day in Taipei. That is the zone change, not a second habit.

All events, Pacific, all-time (n=62): Mon 10, Tue 9, Wed 10, Thu 8, Fri 11, Sat 10, Sun 4.

Last 60 days (since 2026-08-18), confirmed, Pacific (n=16): Mon 2, Tue 2, Wed 2, Thu 2, Fri 4, Sat 3, Sun 1. Too few to crown a day.

Pacific hour-of-day for confirmed resets is broad. The busiest hour is 20:00 (6 of 45); 16:00–21:00 holds 21 of 45. There is no single morning-Pacific spike.

Verdict rule used above (and in the visualizer): **supported** only if the share is above its baseline and the one-sided binomial p-value is under 0.05; **insufficient data** when n<10. A small sample (n<30, or fewer than 5 expected under the null) is a caveat and does not by itself change the verdict.

---

## False positives and gotchas

| Post | What it looked like | What happened |
|---|---|---|
| [codex_resets ⚠️ Possible reset by Oct 17 05:00 UTC](https://x.com/codex_resets/status/2110952027505270882) | strong hint | No reset; Day 12 was an improvement |
| ["Let's break the cycle."](https://x.com/thsottiaux/status/2110951585983631505) | hint that a reset was coming | It meant ending the even-day reset cadence |
| ["out of ideas or we are cooking"](https://x.com/thsottiaux/status/2110971985417441512) | teaser | No reset within 24 h |
| [Day 12 effective usage](https://x.com/thsottiaux/status/2111244596131111253) | "more usage" | An improvement, not a reset |
| [Pro poll 2X](https://x.com/thsottiaux/status/2109152716954222849), ["simple plan"](https://x.com/thsottiaux/status/2109892247580000595) | "2X usage", "more usage" | Polls and plans only |
| [Day 11 capacity fix](https://x.com/thsottiaux/status/2110750421367287996) | recovery | That day's ship; no reset |
| ["Small @poteto speaks big facts"](https://x.com/thsottiaux/status/2111337472349343856) | rivalry | No reset (Day 13, so far) |
| [Sep 22 "loading a banked reset"](https://x.com/thsottiaux/status/2102463847714247142) | "reset" | Banked credit, not an automatic refill |
| [Day 9 post titled "Day 8/"](https://x.com/thsottiaux/status/2110151690641154499) | Day numbering | A typo; we store day_n = 9 |
| ["Over 24 hours without posting"](https://x.com/theo/status/2110580418898780462) | nothing | A reset *did* follow about 1 h later (coincidence; weight 0) |

## Uncertainty

* **Day 2** had no explicit announcement; the vote poll ([x](https://x.com/thsottiaux/status/2107578625419866469)) stands in for one. Poll → confirm took 6.45 h.
* **Sep 22 banked** and **17 announced-only events** have no separate completion post. Tibo often wrote "lands in the next hour" and never followed up.
* **Sep 30** *"@kr0der Yes, check email"* ([x](https://x.com/thsottiaux/status/2105173168281506088)) is described by quotaalert.com as a credit-grant and banked-reset confirmation. The post itself has no reset wording, so it is kept as a signal only.
* Posts before 2026-09-20 were found via the public ledgers [quotaalert.com/history](https://quotaalert.com/history) and [codexlimits.com/reset-history](https://codexlimits.com/reset-history). Every ID was then re-fetched from the X API, and all came back. Coverage before Sep 2026 may still be incomplete.
* Post times are announcement times. Delivery to individual accounts can be later, or can fail (Pro 500, Sep 9).
