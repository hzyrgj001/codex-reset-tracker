"use strict";
/* Weekday counts and tendency verdicts for the static visualizer.
   Same rules as src/codex_reset_tracker/analysis.py. Keep them in sync.
   A claim is "supported" only when its share beats the baseline and the
   one-sided binomial p-value is under 0.05. Fewer than 10 trials is
   "insufficient data". Verdicts are computed, never read from tendencies.json. */
(function (root) {
  var WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  var MIN_TRIALS = 10;
  var ALPHA = 0.05;
  var SMALL_N = 30;
  var DAY_MS = 86400000;

  function binomialSf(k, n, p) {
    if (n <= 0 || k <= 0) return 1;
    if (k > n || p <= 0) return 0;
    if (p >= 1) return 1;
    var logs = [];
    for (var i = k; i <= n; i++) {
      logs.push(logChoose(n, i) + i * Math.log(p) + (n - i) * Math.log(1 - p));
    }
    var top = Math.max.apply(null, logs);
    var sum = 0;
    for (var j = 0; j < logs.length; j++) sum += Math.exp(logs[j] - top);
    return Math.min(1, Math.exp(top) * sum);
  }

  function logChoose(n, k) {
    var s = 0;
    var i;
    for (i = 1; i <= k; i++) s += Math.log(n - k + i) - Math.log(i);
    return s;
  }

  function roundTo(value, digits) {
    var f = Math.pow(10, digits);
    return Math.round((value + Number.EPSILON) * f) / f;
  }

  function judge(k, n, p0, baselineName) {
    var rawP = n === 0 ? null : binomialSf(k, n, p0);
    var share = n === 0 ? null : k / n;
    var verdict;
    if (n < MIN_TRIALS) verdict = "insufficient data";
    else if (share !== null && share > p0 && rawP !== null && rawP < ALPHA) verdict = "supported";
    else verdict = "not supported";
    return {
      verdict: verdict,
      k: k,
      n: n,
      share: share === null ? null : roundTo(share, 4),
      baseline: roundTo(p0, 4),
      baseline_name: baselineName,
      p_value: rawP === null ? null : roundTo(rawP, 6),
      small_sample: n < SMALL_N || (n * p0 < 5)
    };
  }

  function anchorMs(ev) {
    var ref = ev.announce || ev.confirm;
    if (!ref || !ref.utc) return null;
    var ms = Date.parse(ref.utc);
    return isNaN(ms) ? null : ms;
  }

  function zonedParts(ms, timeZone) {
    if (timeZone === "local") {
      var d = new Date(ms);
      return { weekday: WEEKDAYS[(d.getDay() + 6) % 7], hour: d.getHours() };
    }
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: timeZone, weekday: "short", hour: "2-digit", hourCycle: "h23"
    }).formatToParts(new Date(ms));
    var bag = {};
    for (var i = 0; i < parts.length; i++) bag[parts[i].type] = parts[i].value;
    var hour = parseInt(bag.hour, 10);
    if (hour === 24) hour = 0;
    return { weekday: bag.weekday, hour: hour };
  }

  function select(resets, population, window, nowMs) {
    var rows = population === "all" ? resets.slice() : resets.filter(function (e) { return e.status === "confirmed"; });
    if (window === "last_60_days") {
      var since = nowMs - 60 * DAY_MS;
      rows = rows.filter(function (e) {
        var t = anchorMs(e);
        return t !== null && t >= since;
      });
    }
    return rows;
  }

  function weekdayCounts(resets, opts) {
    var nowMs = opts.now || Date.now();
    var zone = opts.zone || "America/Los_Angeles";
    var rows = select(resets, opts.population || "confirmed", opts.window || "all_time", nowMs);
    var counts = {};
    WEEKDAYS.forEach(function (d) { counts[d] = 0; });
    rows.forEach(function (e) {
      var t = anchorMs(e);
      if (t === null) return;
      var wd = zonedParts(t, zone).weekday;
      if (counts[wd] === undefined) counts[wd] = 0;
      counts[wd] += 1;
    });
    return { n: rows.length, counts: counts };
  }

  function labelsOf(sig) {
    if (sig.labels && sig.labels.length) return sig.labels;
    return sig.label ? [sig.label] : [];
  }

  function matchingSignals(signals, labels, authors) {
    var want = {};
    (labels || []).forEach(function (l) { want[l] = true; });
    var authorSet = null;
    if (authors && authors.length) {
      authorSet = {};
      authors.forEach(function (a) { authorSet[a] = true; });
    }
    return signals.filter(function (s) {
      if (s.false_positive) return false;
      if (authorSet && !authorSet[s.author]) return false;
      return labelsOf(s).some(function (l) { return want[l]; });
    });
  }

  function resetInstants(resets) {
    var out = [];
    resets.forEach(function (e) {
      ["announce", "confirm"].forEach(function (key) {
        if (e[key] && e[key].utc) {
          var ms = Date.parse(e[key].utc);
          if (!isNaN(ms)) out.push(ms);
        }
      });
    });
    return out;
  }

  function coverageShare(windows, start, end) {
    var span = end - start;
    if (span <= 0) return 0;
    var clipped = [];
    windows.forEach(function (w) {
      var a = Math.max(w[0], start);
      var b = Math.min(w[1], end);
      if (b > a) clipped.push([a, b]);
    });
    clipped.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [];
    clipped.forEach(function (w) {
      if (merged.length && w[0] <= merged[merged.length - 1][1]) {
        merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], w[1]);
      } else merged.push([w[0], w[1]]);
    });
    var covered = 0;
    merged.forEach(function (w) { covered += w[1] - w[0]; });
    return covered / span;
  }

  function cluster(signals, clusterHours) {
    var ordered = signals.slice().sort(function (a, b) { return Date.parse(a.utc) - Date.parse(b.utc); });
    var gap = clusterHours * 3600000;
    var episodes = [];
    ordered.forEach(function (sig) {
      var t = Date.parse(sig.utc);
      var rel = sig.related_event || null;
      if (episodes.length) {
        var prev = episodes[episodes.length - 1];
        var same = !!(rel && rel === prev.related);
        if (same || t - prev.last <= gap) {
          prev.last = t;
          prev.signals.push(sig);
          if (rel) prev.related = rel;
          return;
        }
      }
      episodes.push({ start: t, last: t, related: rel, signals: [sig] });
    });
    return episodes;
  }

  function spanOf(points) {
    if (!points.length) return null;
    return [Math.min.apply(null, points), Math.max.apply(null, points)];
  }

  function testWeekday(spec, resets, nowMs) {
    var got = weekdayCounts(resets, {
      zone: spec.zone, population: spec.population || "confirmed",
      window: spec.window || "all_time", now: nowMs
    });
    return judge(got.counts[spec.weekday] || 0, got.n, 1 / 7, "1/7");
  }

  function testEvenDay(resets) {
    var rows = resets.filter(function (e) { return e.status === "confirmed" && e.day_n; });
    var k = rows.filter(function (e) { return Number(e.day_n) % 2 === 0; }).length;
    return judge(k, rows.length, 0.5, "1/2");
  }

  function testHourWindow(spec, resets, nowMs) {
    var rows = select(resets, spec.population || "all", spec.window || "all_time", nowMs);
    var start = Number(spec.start_hour), end = Number(spec.end_hour);
    var k = 0;
    rows.forEach(function (e) {
      var t = anchorMs(e);
      if (t === null) return;
      var hour = zonedParts(t, spec.zone).hour;
      if (hour >= start && hour < end) k += 1;
    });
    var width = ((end - start) % 24 + 24) % 24;
    return judge(k, rows.length, width / 24, width + "/24");
  }

  function testSignalThenReset(spec, resets, signals) {
    var hours = Number(spec.within_hours === undefined ? 48 : spec.within_hours);
    var matched = matchingSignals(signals, spec.labels, spec.authors);
    var episodes = cluster(matched, Number(spec.cluster_hours === undefined ? 6 : spec.cluster_hours));
    var instants = resetInstants(resets);
    var k = 0;
    episodes.forEach(function (ep) {
      var end = ep.start + hours * 3600000;
      if (instants.some(function (t) { return t >= ep.start && t <= end; })) k += 1;
    });
    var points = instants.concat(episodes.map(function (ep) { return ep.start; }));
    var span = spanOf(points);
    var p0 = 0;
    if (span) {
      var windows = instants.map(function (t) { return [t - hours * 3600000, t]; });
      p0 = coverageShare(windows, span[0], span[1]);
    }
    return judge(k, episodes.length, p0, "timeline");
  }

  function testSignalNearReset(spec, resets, signals) {
    var hours = Number(spec.within_hours === undefined ? 2 : spec.within_hours);
    var matched = matchingSignals(signals, spec.labels, spec.authors);
    var instants = resetInstants(resets);
    var window = hours * 3600000;
    var k = 0;
    var trialTimes = [];
    matched.forEach(function (sig) {
      var t = Date.parse(sig.utc);
      trialTimes.push(t);
      if (instants.some(function (r) { return Math.abs(t - r) <= window; })) k += 1;
    });
    var span = spanOf(instants.concat(trialTimes));
    var p0 = 0;
    if (span) {
      var windows = instants.map(function (t) { return [t - window, t + window]; });
      p0 = coverageShare(windows, span[0], span[1]);
    }
    return judge(k, matched.length, p0, "timeline");
  }

  function evaluateTendencies(tendencies, resets, signals, nowMs) {
    nowMs = nowMs || Date.now();
    return (tendencies || []).map(function (item) {
      var spec = item.test || {};
      var judged;
      if (spec.kind === "weekday") judged = testWeekday(spec, resets, nowMs);
      else if (spec.kind === "even_campaign_day") judged = testEvenDay(resets);
      else if (spec.kind === "hour_window") judged = testHourWindow(spec, resets, nowMs);
      else if (spec.kind === "signal_then_reset") judged = testSignalThenReset(spec, resets, signals);
      else if (spec.kind === "signal_near_reset") judged = testSignalNearReset(spec, resets, signals);
      else throw new Error("unknown tendency test: " + spec.kind);
      var row = { id: item.id, claim: item.claim, source: item.source, test: spec };
      Object.keys(judged).forEach(function (key) { row[key] = judged[key]; });
      return row;
    });
  }

  function weekdayOf(ms, zone) { return zonedParts(ms, zone).weekday; }

  root.Tendency = {
    WEEKDAYS: WEEKDAYS,
    MIN_TRIALS: MIN_TRIALS,
    ALPHA: ALPHA,
    binomialSf: binomialSf,
    weekdayOf: weekdayOf,
    weekdayCounts: weekdayCounts,
    evaluateTendencies: evaluateTendencies
  };
})(typeof window !== "undefined" ? window : globalThis);
