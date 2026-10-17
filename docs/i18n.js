"use strict";
/* Language switch for the static visualizer. No dependencies.
   Manual choice in localStorage overrides ?lang= and navigator.languages. */
(function (root) {
  var STORAGE_KEY = "codexResetTracker.lang";

  function preferredLang(opts) {
    opts = opts || {};
    var stored = opts.stored;
    var query = opts.query;
    if (stored === "en" || stored === "zh") return stored;
    if (query === "en" || query === "zh") return query;
    var languages = opts.languages;
    if (!languages || !languages.length) languages = ["en"];
    for (var i = 0; i < languages.length; i++) {
      if (String(languages[i] || "").toLowerCase().indexOf("zh") === 0) return "zh";
    }
    return "en";
  }

  function readStored() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }
  function readQuery() {
    try { return new URLSearchParams(location.search).get("lang"); } catch (e) { return null; }
  }
  function browserLanguages() {
    if (typeof navigator === "undefined") return ["en"];
    if (navigator.languages && navigator.languages.length) return Array.prototype.slice.call(navigator.languages);
    return [navigator.language || "en"];
  }

  var dicts = { en: null, zh: null };
  var lang = "en";
  var listeners = [];

  function t(key, vars) {
    var primary = dicts[lang] || {};
    var fallback = dicts.en || {};
    var s = primary[key] != null ? primary[key] : (fallback[key] != null ? fallback[key] : key);
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        s = String(s).split("{" + k + "}").join(String(vars[k]));
      });
    }
    return s;
  }

  function locale() { return lang === "zh" ? "zh-CN" : "en-US"; }

  function applyDom() {
    if (typeof document === "undefined") return;
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    document.documentElement.dataset.lang = lang;
    if (dicts.en && dicts.zh) {
      document.title = t("pageTitle");
      var meta = document.querySelector('meta[name="description"]');
      if (meta) meta.setAttribute("content", t("metaDescription"));
    }
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(",").forEach(function (part) {
        var bits = part.split(":");
        el.setAttribute(bits[0].trim(), t(bits[1].trim()));
      });
    });
    document.querySelectorAll(".lang-btn").forEach(function (btn) {
      var on = btn.getAttribute("data-set-lang") === lang;
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.classList.toggle("active", on);
    });
  }

  function setLang(next, persist) {
    if (next !== "en" && next !== "zh") return;
    lang = next;
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, next); } catch (e) {}
    }
    applyDom();
    listeners.forEach(function (fn) { fn(lang); });
  }

  function onChange(fn) { listeners.push(fn); }

  function loadDicts() {
    lang = preferredLang({ stored: readStored(), query: readQuery(), languages: browserLanguages() });
    return Promise.all([fetch("locales/en.json"), fetch("locales/zh.json")]).then(function (res) {
      if (!res[0].ok || !res[1].ok) throw new Error("locales");
      return Promise.all([res[0].json(), res[1].json()]);
    }).then(function (pair) {
      dicts.en = pair[0];
      dicts.zh = pair[1];
      applyDom();
      return true;
    }).catch(function (err) {
      if (typeof console !== "undefined") console.error(err);
      return false;
    });
  }

  function ready() { return !!(dicts.en && dicts.zh); }

  root.I18N = {
    STORAGE_KEY: STORAGE_KEY,
    preferredLang: preferredLang,
    t: t,
    locale: locale,
    setLang: setLang,
    onChange: onChange,
    loadDicts: loadDicts,
    ready: ready,
    get lang() { return lang; }
  };
})(typeof window !== "undefined" ? window : globalThis);
