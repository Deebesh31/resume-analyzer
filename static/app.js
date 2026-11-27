"use strict";

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const historyEntries = [];
let historyLoaded = false;
let historyLoading = false;
const downloads = { analysis: "", fullReport: "", match: "", letter: "", tool: "" };
let activeView = "home";

function syncNavigation(name = activeView) {
  const tabs = [...document.querySelectorAll("[data-view]")];
  const homeTabVisible = tabs.some((tab) => tab.dataset.view === "home" && tab.getClientRects().length > 0);
  const fallbackTab = name === "home" && !homeTabVisible ? tabs.find((tab) => tab.dataset.view === "analyze") : null;
  tabs.forEach((tab) => {
    const active = tab.dataset.view === name;
    tab.classList.toggle("is-active", active);
    if (active) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
    tab.tabIndex = active || tab === fallbackTab ? 0 : -1;
  });
}

function activateView(name, moveFocus = false) {
  activeView = name;
  syncNavigation(name);
  if (moveFocus) document.querySelector(`[data-view="${name}"]`)?.focus();
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    const active = panel.dataset.viewPanel === name;
    panel.hidden = !active;
    panel.classList.toggle("is-visible", active);
  });
  window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
  if (name === "history") {
    if (historyLoaded) renderHistory();
    else loadHistory();
  }
  if (name !== "home") selectEngineCapability(name, false);
  else selectEngineCapability(activeCapability, true);
  revealView(name);
}

document.querySelectorAll("[data-view]").forEach((tab) => {
  tab.addEventListener("click", () => activateView(tab.dataset.view));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...document.querySelectorAll("[data-view]")].filter((candidate) => candidate.getClientRects().length > 0);
    const current = tabs.indexOf(tab);
    if (current < 0 || !tabs.length) return;
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 :
      (current + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
    activateView(tabs[next].dataset.view, true);
  });
});
syncNavigation();
window.addEventListener("resize", () => syncNavigation());

document.querySelectorAll("[data-switch-view]").forEach((button) => {
  button.addEventListener("click", (event) => {
    if (button.tagName === "A") event.preventDefault();
    activateView(button.dataset.switchView);
  });
});

const engineCapabilities = {
  analyze: { title: "Resume review", copy: "A clear view of the strengths and opportunities in your experience.", action: "Open resume review" },
  match: { title: "Job match", copy: "Bring a job description alongside your experience to see useful overlap.", action: "Explore a job match" },
  letter: { title: "Cover letter", copy: "Shape a relevant first draft around your experience and the role.", action: "Draft a cover letter" },
  history: { title: "History", copy: "Keep resume reviews saved to your account.", action: "View saved history" },
  tools: { title: "Resume tools", copy: "Make focused edits to bullets, achievements, sections, and interview prep.", action: "Explore resume tools" },
};
const engineNodes = [...document.querySelectorAll("[data-engine-view]")];
const engineHighlight = document.querySelector(".engine-selection-highlight");
let activeCapability = "analyze";
if (window.gsap && window.Flip) window.gsap.registerPlugin(window.Flip);
function selectEngineCapability(name, animate = true) {
  if (!engineCapabilities[name]) return;
  const selected = engineNodes.find((node) => node.dataset.engineView === name);
  if (!selected) return;
  activeCapability = name;
  engineNodes.forEach((node) => {
    const active = node === selected;
    node.classList.toggle("is-selected", active);
    node.setAttribute("aria-pressed", String(active));
  });
  const capability = engineCapabilities[name];
  document.getElementById("engine-live-title").textContent = capability.title;
  document.getElementById("engine-live-copy").textContent = capability.copy;
  const open = document.getElementById("engine-open");
  open.dataset.switchView = name;
  open.innerHTML = `${capability.action} <span class="button-icon" aria-hidden="true"><img src="/static/icons/arrow-right.svg" alt=""></span>`;
  const homeView = document.getElementById("view-home");
  if (engineHighlight && window.Flip && !homeView.hidden) {
    const duration = animate && !prefersReducedMotion() ? 0.42 : 0;
    window.Flip.fit(engineHighlight, selected, { duration, ease: "power2.inOut", scale: true });
  }
}
if (engineHighlight && window.Flip) {
  document.querySelector(".engine-stage").append(engineHighlight);
  window.Flip.fit(engineHighlight, engineNodes[0], { duration: 0, scale: true });
}
engineNodes.forEach((node) => {
  node.addEventListener("mouseenter", () => selectEngineCapability(node.dataset.engineView));
  node.addEventListener("focus", () => selectEngineCapability(node.dataset.engineView));
  node.addEventListener("click", () => activateView(node.dataset.engineView));
});

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function revealView(name) {
  if (prefersReducedMotion() || !window.gsap) return;
  const view = document.querySelector(`[data-view-panel="${name}"]`);
  if (!view) return;
  const targets = [...view.querySelectorAll(":scope > [data-reveal], :scope > .workspace-head, :scope > .workspace-content > .module-heading")];
  if (!targets.length) return;
  window.gsap.fromTo(targets, { autoAlpha: 0, y: 12 }, { autoAlpha: 1, y: 0, duration: 0.52, stagger: 0.07, ease: "power3.out", clearProps: "all" });
}

if (window.gsap) {
  const engineCore = document.querySelector(".engine-core");
  if (engineCore && !prefersReducedMotion()) {
    window.gsap.to(engineCore, { y: -5, duration: 2.4, repeat: -1, yoyo: true, ease: "sine.inOut" });
  }
}
if ("IntersectionObserver" in window && window.gsap && !prefersReducedMotion()) {
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      window.gsap.fromTo(entry.target, { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: 0.62, ease: "power3.out", clearProps: "all" });
      revealObserver.unobserve(entry.target);
    });
  }, { threshold: 0.12 });
  document.querySelectorAll(".capability-card[data-reveal], .workflow-note[data-reveal], .home-trust-row[data-reveal]").forEach((node) => revealObserver.observe(node));
}

function setError(id, message) {
  const element = document.getElementById(id);
  element.textContent = stripEmoji(message);
  element.hidden = !message;
}

function setLoading(form, loadingId, resultId, errorId, busy) {
  document.getElementById(loadingId).hidden = !busy;
  if (busy) setError(errorId, "");
  const submit = form.querySelector('button[type="submit"]');
  if (submit) {
    submit.disabled = busy;
    submit.setAttribute("aria-busy", String(busy));
  }
}

async function postForm(form, endpoint) {
  const response = await fetch(endpoint, {
    method: "POST",
    body: new FormData(form),
    credentials: "same-origin",
    headers: { "X-CSRF-Token": csrfToken, "Accept": "application/json" },
  });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Your session has expired. Sign in again.");
  }
  let payload;
  try { payload = await response.json(); }
  catch { throw new Error("The server returned an unreadable response."); }
  if (payload.remaining_usage) updateUsage(payload.remaining_usage);
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

function updateUsage(usage) {
  if (!usage) return;
  const targets = {
    resume_analysis: "usage-resume",
    job_match: "usage-match",
    cover_letter: "usage-letter",
    resume_tools: "usage-tools",
  };
  Object.entries(targets).forEach(([key, id]) => {
    if (!Object.hasOwn(usage, key)) return;
    const element = document.getElementById(id);
    if (element) element.textContent = usage[key];
    document.querySelectorAll(`[data-account-usage="${key}"]`).forEach((counter) => {
      counter.textContent = usage[key];
    });
  });
}

const accountControl = document.querySelector("[data-account-control]");
const accountTrigger = document.querySelector("[data-account-trigger]");
const accountPopover = document.querySelector("[data-account-popover]");
function setAccountPopoverOpen(open) {
  if (!accountTrigger || !accountPopover) return;
  accountTrigger.setAttribute("aria-expanded", String(open));
  accountPopover.hidden = !open;
}
accountTrigger?.addEventListener("click", () => {
  setAccountPopoverOpen(accountTrigger.getAttribute("aria-expanded") !== "true");
});
document.addEventListener("click", (event) => {
  if (accountControl && !accountControl.contains(event.target)) setAccountPopoverOpen(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && accountTrigger?.getAttribute("aria-expanded") === "true") {
    setAccountPopoverOpen(false);
    accountTrigger.focus();
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function stripEmoji(value) {
  return String(value ?? "")
    .replace(/(?:[#*0-9]\uFE0F?\u20E3|[\u{1F1E6}-\u{1F1FF}]{2}|[\p{Emoji_Presentation}\p{Extended_Pictographic}\p{Emoji_Modifier}])/gu, "")
    .replace(/[\uFE0E\uFE0F\u200D\u20E3]/gu, "");
}

function iconForHeading(headingText) {
  const title = stripEmoji(headingText).replace(/\*\*/g, "").toLowerCase();
  if (/recommend|action plan|next step|suggest|priority|advice/.test(title)) return "lightbulb";
  if (/strength|achievement|positive|success|highlight|key win/.test(title)) return "badge-check";
  if (/improv|weakness|gap|opportunit|challenge|risk|develop/.test(title)) return "trending-up";
  if (/ats|format|structure|readab|scann/.test(title)) return "scan-text";
  if (/skill|technical|competenc|tool|stack/.test(title)) return "layers";
  if (/experience|employment|work history|career|project/.test(title)) return "briefcase-business";
  if (/education|academic|qualification|degree/.test(title)) return "graduation-cap";
  if (/conclusion|closing|final thought|wrap.?up|takeaway/.test(title)) return "flag";
  if (/summary|overview|profile/.test(title)) return "file-text";
  return "notebook-pen";
}

// Render only a small Markdown subset after escaping all model-provided text.
function safeMarkdown(markdown) {
  const lines = escapeHtml(stripEmoji(markdown || "")).replace(/\r/g, "").split("\n");
  const output = [];
  let listType = null;
  let paragraph = [];
  const closeList = () => {
    if (listType) output.push(listType === "ul" ? "</ul>" : "</ol>");
    listType = null;
  };
  const flushParagraph = () => {
    if (paragraph.length) {
      const content = paragraph.join(" ").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      output.push(`<p>${content}</p>`);
      paragraph = [];
    }
  };
  for (const line of lines) {
    const heading = line.match(/^\s{0,3}(#{1,3})\s+(.*)$/);
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (!line.trim()) { flushParagraph(); closeList(); continue; }
    if (heading) {
      flushParagraph(); closeList();
      const level = Math.min(3, heading[1].length + 1);
      const headingText = stripEmoji(heading[2]).trim();
      const icon = iconForHeading(headingText);
      const iconMarkup = `<span class="prose-heading-icon" aria-hidden="true"><img src="/static/icons/${icon}.svg" alt=""></span>`;
      const textMarkup = headingText.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      output.push(`<h${level} class="prose-heading prose-heading--${icon}">${iconMarkup}<span class="prose-heading-text">${textMarkup}</span></h${level}>`);
      continue;
    }
    if (bullet || numbered) {
      flushParagraph();
      const nextType = bullet ? "ul" : "ol";
      if (listType !== nextType) { closeList(); output.push(`<${nextType}>`); listType = nextType; }
      const item = (bullet || numbered)[1].replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      output.push(`<li>${item}</li>`);
      continue;
    }
    closeList();
    paragraph.push(line.trim());
  }
  flushParagraph();
  closeList();
  return output.join("");
}

function setProse(id, text) {
  document.getElementById(id).innerHTML = safeMarkdown(stripEmoji(text));
}

function addMetric(container, label, value, detail = "") {
  const card = document.createElement("div");
  card.className = "metric-card";
  const labelNode = document.createElement("div");
  labelNode.className = "metric-label";
  labelNode.textContent = label;
  const valueNode = document.createElement("div");
  valueNode.className = "metric-value";
  valueNode.textContent = value;
  card.append(labelNode, valueNode);
  if (detail) {
    const detailNode = document.createElement("div");
    detailNode.className = "metric-detail";
    detailNode.textContent = detail;
    card.append(detailNode);
  }
  container.append(card);
}

function fillChips(container, values, emptyLabel = "None recognized") {
  container.replaceChildren();
  if (!values?.length) {
    const empty = document.createElement("span");
    empty.className = "muted";
    empty.textContent = emptyLabel;
    container.append(empty);
    return;
  }
  values.forEach((value) => {
    const chip = document.createElement("span");
    chip.className = "readability-chip";
    chip.textContent = value.replaceAll("_", " ");
    container.append(chip);
  });
}

function describeReadability(readability, label, summary, chips) {
  if (!readability) return;
  document.getElementById(label).textContent = readability.status;
  const pageText = readability.page_count ? `${readability.page_count} page${readability.page_count === 1 ? "" : "s"}` : "page count unavailable";
  const qualityText = readability.quality_band ? ` · Affinda extraction quality: ${readability.quality_band}` : "";
  document.getElementById(summary).textContent = `${readability.format} · ${pageText} · ${readability.word_count} words extracted · ${readability.parser || "Basic document checks"}${qualityText}.`;
  fillChips(document.getElementById(chips), readability.sections, "No common section headings recognized");
}

function animateScore(score) {
  const scoreValue = document.getElementById("score-value");
  const progress = document.getElementById("score-progress");
  const scoreCard = document.querySelector(".score-card");
  const scoreVisual = document.querySelector(".score-visual");
  const marker = document.querySelector(".score-orbit-dot");
  if (!scoreValue || !progress || !scoreCard || !scoreVisual || !marker) return;

  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  const circumference = 301.6;
  const band = safeScore >= 80 ? "strong" : safeScore >= 60 ? "developing" : "early";
  const setProgress = (value) => {
    progress.style.strokeDasharray = String(circumference);
    progress.style.strokeDashoffset = String(circumference * (1 - value / 100));
  };
  const markerRadius = scoreVisual.clientWidth * (48 / 120);
  const markerAngle = (safeScore / 100) * Math.PI * 2 - Math.PI / 2;
  marker.style.left = `${scoreVisual.clientWidth / 2 + Math.cos(markerAngle) * markerRadius - marker.offsetWidth / 2}px`;
  marker.style.top = `${scoreVisual.clientHeight / 2 + Math.sin(markerAngle) * markerRadius - marker.offsetHeight / 2}px`;
  marker.style.right = "auto";
  scoreCard.dataset.band = band;
  scoreCard.classList.remove("score-reveal");
  void scoreCard.offsetWidth;
  scoreCard.classList.add("score-reveal");

  if (prefersReducedMotion() || !window.gsap) {
    scoreValue.textContent = String(safeScore);
    setProgress(safeScore);
    marker.style.opacity = "1";
    marker.style.transform = "scale(1)";
    return;
  }

  scoreValue.textContent = "0";
  setProgress(0);
  marker.style.opacity = "0";
  const counter = { value: 0 };
  window.gsap.to(counter, {
    value: safeScore,
    duration: 1.45,
    ease: "power3.out",
    onUpdate: () => {
      scoreValue.textContent = String(Math.round(counter.value));
      setProgress(counter.value);
    },
  });
  window.gsap.fromTo(marker, { scale: 0.25, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.48, delay: 0.82, ease: "back.out(2.2)", clearProps: "transform,opacity" });
}

function renderResumeResult(result, { recordHistory = true } = {}) {
  document.getElementById("analysis-results").hidden = false;
  const overview = document.getElementById("analysis-overview");
  const scoreCard = document.querySelector(".score-card");
  const score = Number.isFinite(result.score) ? result.score : null;
  const stats = result.stats;
  const readability = result.readability;
  overview.hidden = !stats && score === null;
  scoreCard.hidden = score === null;
  document.getElementById("readability-card").hidden = !readability;
  const filename = stripEmoji(result.filename || "");
  const analysis = stripEmoji(result.analysis || "");
  const fullReport = stripEmoji(result.full_report || "");
  document.getElementById("analysis-filename").textContent = filename;
  if (score !== null) {
    document.getElementById("score-label").textContent = result.score_label || (score >= 80 ? "Strong foundations" : score >= 60 ? "Room to strengthen" : score >= 40 ? "Several opportunities" : "A useful starting point");
    document.getElementById("score-svg-desc").textContent = `ResuMate structure score: ${score} out of 100. This is a heuristic, not an employer ATS score.`;
    const breakdown = document.getElementById("score-breakdown");
    breakdown.replaceChildren();
    (result.score_breakdown || []).forEach((factor) => {
      const item = document.createElement("li");
      item.textContent = `${factor.name}: ${factor.score}/${factor.maximum}. ${factor.detail}`;
      breakdown.append(item);
    });
    requestAnimationFrame(() => animateScore(score));
  }
  describeReadability(readability, "readability-label", "readability-summary", "readability-chips");
  const parseSection = document.getElementById("ats-results");
  parseSection.hidden = !readability;
  if (readability) {
    document.getElementById("ats-status").textContent = readability.status;
    const fields = document.getElementById("parse-fields");
    fields.replaceChildren();
    (readability.profile_fields || []).forEach((field) => {
      const term = document.createElement("dt");
      term.textContent = field.label;
      const definition = document.createElement("dd");
      definition.textContent = field.found ? `${field.evidence}${field.note ? ` · ${field.note}` : ""}` : field.note;
      fields.append(term, definition);
    });
    fillChips(document.getElementById("parse-sections"), readability.sections, "No common section headings recognized");
    fillChips(document.getElementById("parse-dates"), readability.date_ranges, "No date ranges recognized");
    const warnings = document.getElementById("ats-issues");
    warnings.replaceChildren();
    (readability.warnings?.length ? readability.warnings : ["No extraction warnings were triggered by these checks."]).forEach((warning) => {
      const item = document.createElement("li");
      item.textContent = warning;
      warnings.append(item);
    });
    const preview = document.getElementById("extracted-text-preview");
    const previewText = result.extracted_text_preview || "The full extracted text is not saved in account history.";
    preview.textContent = `${previewText}${result.text_preview_truncated ? "\n\n[Preview shortened]" : ""}`;
  }
  const metrics = document.getElementById("resume-metrics");
  metrics.replaceChildren();
  if (stats) {
    addMetric(metrics, "Word count", String(stats.word_count), "Words extracted from the file");
    addMetric(metrics, "Action verbs", String(stats.action_verb_count), "Exact matches from a small verb list");
    addMetric(metrics, "Numbers in text", String(stats.quantifiable_achievements), "A count, not a measure of impact");
    const foundContact = [stats.has_email && "Email", stats.has_phone && "Phone"].filter(Boolean).join(" and ");
    addMetric(metrics, "Contact details", foundContact || "None detected");
  }
  const verbSection = document.getElementById("verb-results");
  verbSection.hidden = !result.action_verbs;
  if (result.action_verbs) {
    const list = document.getElementById("verb-list");
    list.replaceChildren();
    if (!result.action_verbs.length) list.textContent = "No phrases from the current weak-verb list were detected.";
    result.action_verbs.forEach((item) => {
      const row = document.createElement("p");
      row.className = "muted";
      row.textContent = stripEmoji(`“${item.weak}” · ${item.count} occurrence${item.count === 1 ? "" : "s"} · Alternatives: ${item.strong.join(", ")}`);
      list.append(row);
    });
  }
  setProse("analysis-body", analysis);
  downloads.analysis = analysis;
  downloads.fullReport = fullReport;
  if (recordHistory) {
    const historyStatus = document.getElementById("analysis-history-status");
    if (result.history_entry) addHistoryEntry(result.history_entry);
    if (historyStatus) {
      historyStatus.textContent = result.history_saved
        ? "Saved to your account history."
        : "This review is available now, but could not be saved to account history.";
      historyStatus.hidden = false;
    }
  }
}

function addHistoryEntry(entry) {
  if (!entry) return;
  const sanitized = { ...entry, filename: stripEmoji(entry.filename || ""), analysis: stripEmoji(entry.analysis || ""), full_report: stripEmoji(entry.full_report || "") };
  const existingIndex = historyEntries.findIndex((item) => item.id && item.id === sanitized.id);
  if (existingIndex >= 0) historyEntries.splice(existingIndex, 1);
  historyEntries.unshift(sanitized);
  if (historyEntries.length > 25) historyEntries.length = 25;
  if (historyLoaded) renderHistory();
}

function formatHistoryDate(entry) {
  if (entry.created_at) return new Date(entry.created_at * 1000).toLocaleString();
  const parsed = Date.parse(entry.date || "");
  return Number.isNaN(parsed) ? "Saved review" : new Date(parsed).toLocaleString();
}

function renderHistory() {
  const list = document.getElementById("history-list");
  const empty = document.getElementById("history-empty");
  const compare = document.getElementById("comparison-panel");
  const clear = document.getElementById("clear-history");
  const status = document.getElementById("history-status");
  const retry = document.getElementById("retry-history");
  list.replaceChildren();
  if (!historyLoaded) {
    empty.hidden = true;
    compare.hidden = true;
    clear.hidden = true;
    status.hidden = false;
    status.textContent = historyLoading ? "Loading saved reviews…" : "Saved history has not loaded yet.";
    retry.hidden = historyLoading;
    return;
  }
  status.hidden = true;
  retry.hidden = true;
  empty.hidden = historyEntries.length > 0;
  compare.hidden = historyEntries.length < 2;
  clear.hidden = historyEntries.length === 0;
  historyEntries.forEach((entry, index) => {
    const row = document.createElement("article");
    row.className = "history-entry surface";
    const main = document.createElement("div");
    main.className = "history-entry-main";
    const title = document.createElement("strong");
    title.textContent = stripEmoji(entry.filename || "Resume review");
    const date = document.createElement("small");
    date.textContent = formatHistoryDate(entry);
    main.append(title, date);
    const score = document.createElement("span");
    score.className = "history-entry-score";
    score.textContent = Number.isFinite(entry.score) ? `${entry.score}/100 structure` : (entry.readability?.status || "Review complete");
    const actions = document.createElement("div");
    actions.className = "history-actions";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "button button-secondary button-small";
    open.textContent = "Open review";
    open.addEventListener("click", () => {
      activateView("analyze");
      renderResumeResult(entry, { recordHistory: false });
      document.getElementById("analysis-results").hidden = false;
      document.getElementById("analysis-history-status").textContent = "Loaded from your saved account history.";
      document.getElementById("analysis-history-status").hidden = false;
      document.getElementById("analysis-results").scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
    });
    const download = document.createElement("button");
    download.type = "button";
    download.className = "button button-secondary button-small";
    download.textContent = "Download";
    download.addEventListener("click", () => downloadText(entry.full_report || entry.analysis, `resume-analysis-${index + 1}.txt`));
    actions.append(open, download);
    row.append(main, score, actions);
    list.append(row);
  });
  if (historyEntries.length >= 2) populateCompareSelects();
}

async function loadHistory() {
  if (historyLoading || historyLoaded) return;
  historyLoading = true;
  renderHistory();
  try {
    const response = await fetch("/api/history", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (response.status === 401) {
      window.location.assign("/login");
      return;
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Saved history could not be loaded.");
    historyEntries.splice(0, historyEntries.length, ...(payload.entries || []));
    historyLoaded = true;
    historyLoading = false;
    renderHistory();
  } catch (error) {
    historyLoading = false;
    const status = document.getElementById("history-status");
    status.textContent = error.message || "Saved history could not be loaded. Try again.";
    status.hidden = false;
    document.getElementById("retry-history").hidden = false;
  }
}

function populateCompareSelects() {
  ["version-a", "version-b"].forEach((id, selectIndex) => {
    const select = document.getElementById(id);
    const previous = select.value;
    select.replaceChildren();
    historyEntries.forEach((entry, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `${stripEmoji(entry.filename || "Resume")} · ${formatHistoryDate(entry)}`;
      select.append(option);
    });
    if ([...select.options].some((option) => option.value === previous)) select.value = previous;
    else select.selectedIndex = Math.min(selectIndex, historyEntries.length - 1);
  });
}

function renderComparison() {
  const first = historyEntries[Number(document.getElementById("version-a").value)];
  const second = historyEntries[Number(document.getElementById("version-b").value)];
  const results = document.getElementById("comparison-results");
  results.replaceChildren();
  if (!first || !second || first === second) {
    results.hidden = false;
    addMetric(results, "Comparison", "Choose two different reviews");
    return;
  }
  const firstStats = first.stats || {};
  const secondStats = second.stats || {};
  if (Number.isFinite(first.score) && Number.isFinite(second.score)) {
    const scoreDelta = second.score - first.score;
    addMetric(results, "Structure score", `${second.score}/100`, `${scoreDelta >= 0 ? "+" : ""}${scoreDelta} points`);
  }
  addMetric(results, "Word count", String(secondStats.word_count ?? "—"), `${(secondStats.word_count ?? 0) - (firstStats.word_count ?? 0) >= 0 ? "+" : ""}${(secondStats.word_count ?? 0) - (firstStats.word_count ?? 0)}`);
  addMetric(results, "Action verbs", String(secondStats.action_verb_count ?? "—"), `${(secondStats.action_verb_count ?? 0) - (firstStats.action_verb_count ?? 0) >= 0 ? "+" : ""}${(secondStats.action_verb_count ?? 0) - (firstStats.action_verb_count ?? 0)}`);
  addMetric(results, "Numbers in text", String(secondStats.quantifiable_achievements ?? "—"), `${(secondStats.quantifiable_achievements ?? 0) - (firstStats.quantifiable_achievements ?? 0) >= 0 ? "+" : ""}${(secondStats.quantifiable_achievements ?? 0) - (firstStats.quantifiable_achievements ?? 0)}`);
  results.hidden = false;
}

function renderKeywords(keywords) {
  const panel = document.getElementById("keyword-results");
  panel.replaceChildren();
  panel.hidden = !keywords;
  if (!keywords) return;
  const title = document.createElement("div");
  title.className = "eyebrow";
  title.textContent = "RECOGNIZED JOB REQUIREMENTS";
  const summary = document.createElement("div");
  summary.className = "keyword-summary";
  const percentage = document.createElement("strong");
  percentage.textContent = keywords.coverage_percent === null ? "—" : `${keywords.coverage_percent}%`;
  const description = document.createElement("span");
  description.className = "muted";
  description.textContent = keywords.coverage_percent === null
    ? "No recognized skill phrases found in the pasted job description."
    : `${keywords.matched_requirement_count} of ${keywords.recognized_requirement_count} recognized skill phrases appear in the resume.`;
  summary.append(percentage, description);
  const basis = document.createElement("p");
  basis.className = "muted keyword-basis";
  basis.textContent = keywords.coverage_basis;
  const columns = document.createElement("div");
  columns.className = "keyword-columns";
  [["Found in resume text", keywords.matching_skills], ["Not found in resume text", keywords.missing_skills]].forEach(([label, values]) => {
    const group = document.createElement("div");
    const heading = document.createElement("h4");
    heading.textContent = label;
    const list = document.createElement("div");
    list.className = "skill-evidence-list";
    if (!values.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No items in this group.";
      list.append(empty);
    }
    values.forEach((skill) => {
      const item = document.createElement("article");
      item.className = "skill-evidence-item";
      const name = document.createElement("strong");
      name.textContent = skill.name;
      const priority = document.createElement("span");
      priority.className = "skill-priority";
      priority.textContent = skill.priority;
      const evidence = document.createElement("p");
      evidence.textContent = skill.matched
        ? `Resume evidence: “${skill.resume_evidence}”`
        : `Not detected in the extracted resume text. Job listing evidence: “${skill.job_evidence}”`;
      item.append(name, priority, evidence);
      list.append(item);
    });
    group.append(heading, list);
    columns.append(group);
  });
  panel.append(title, summary, basis);
  if (keywords.job_title) {
    const titleCheck = document.createElement("p");
    titleCheck.className = "title-match-evidence";
    titleCheck.textContent = keywords.job_title_match === null
      ? `Job title check: ${keywords.job_title}`
      : `Title check for “${keywords.job_title}”: ${keywords.job_title_match ? `found in resume text (“${keywords.job_title_evidence}”)` : "not found as an exact phrase in the resume text"}.`;
    panel.append(titleCheck);
  }
  if (keywords.recognized_requirement_count) panel.append(columns);
  const extraChecks = [
    ["Education requested", keywords.education_checks || []],
    ["Certifications requested", keywords.certification_checks || []],
  ];
  extraChecks.forEach(([headingText, entries]) => {
    if (!entries.length) return;
    const group = document.createElement("section");
    group.className = "other-requirements";
    const heading = document.createElement("h4");
    heading.textContent = headingText;
    group.append(heading);
    const list = document.createElement("div");
    list.className = "skill-evidence-list";
    entries.forEach((entry) => {
      const item = document.createElement("article");
      item.className = "skill-evidence-item";
      const name = document.createElement("strong");
      name.textContent = entry.name;
      const state = document.createElement("span");
      state.className = "skill-priority";
      const educationCheck = headingText === "Education requested";
      state.textContent = `${entry.priority} · ${entry.matched ? (educationCheck ? "degree level met" : "found") : "not found"}`;
      const evidence = document.createElement("p");
      evidence.textContent = entry.matched
        ? `Resume evidence: “${entry.resume_evidence}”${entry.comparison_note ? ` ${entry.comparison_note}` : ""}`
        : `Not detected in the extracted resume text. Job listing evidence: “${entry.job_evidence}”`;
      item.append(name, state, evidence);
      list.append(item);
    });
    group.append(list);
    panel.append(group);
  });
  if (keywords.experience_requirements?.length) {
    const group = document.createElement("section");
    group.className = "other-requirements";
    const heading = document.createElement("h4");
    heading.textContent = "Experience duration to review";
    group.append(heading);
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "These are shown for manual comparison; ResuMate does not calculate total employment duration from dates.";
    group.append(note);
    keywords.experience_requirements.forEach((requirement) => {
      const item = document.createElement("article");
      item.className = "skill-evidence-item";
      item.textContent = requirement;
      group.append(item);
    });
    panel.append(group);
  }
}

function renderMatchReadability(readability) {
  const section = document.getElementById("match-readability");
  section.hidden = !readability;
  if (!readability) return;
  document.getElementById("match-readability-status").textContent = readability.status;
  fillChips(document.getElementById("match-readability-details"), [
    `${readability.format} · ${readability.word_count} words extracted · ${readability.parser || "Basic document checks"}${readability.quality_band ? ` · ${readability.quality_band} extraction` : ""}`,
    ...(readability.sections || []).map((sectionName) => sectionName.replaceAll("_", " ")),
  ], "No common section headings recognized");
  const warnings = document.getElementById("match-readability-warnings");
  warnings.replaceChildren();
  (readability.warnings?.length ? readability.warnings : ["No extraction warnings were triggered by these checks."]).forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = warning;
    warnings.append(item);
  });
}

function downloadText(text, filename) {
  const blob = new Blob([stripEmoji(text || "")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

document.querySelectorAll("[data-download]").forEach((button) => {
  button.addEventListener("click", () => {
    const type = button.dataset.download;
    const names = { analysis: "resume-analysis.txt", fullReport: "resume-analysis-report.txt", match: "job-match-analysis.txt", letter: "cover-letter.txt", tool: "resume-tool-suggestions.txt" };
    downloadText(downloads[type], names[type]);
  });
});

function setupFileInput(inputId, labelId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const label = labelId ? document.getElementById(labelId) : null;
  input.addEventListener("change", () => {
    if (label) label.textContent = stripEmoji(input.files?.[0]?.name || "No file selected");
  });
  const drop = input.closest(".file-drop");
  if (!drop) return;
  ["dragenter", "dragover"].forEach((eventName) => drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.remove("is-dragging");
  }));
  drop.addEventListener("drop", (event) => {
    const files = event.dataTransfer?.files;
    if (!files?.length) return;
    const transfer = new DataTransfer();
    transfer.items.add(files[0]);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

setupFileInput("analysis-resume", "analysis-file-name");
setupFileInput("match-resume", "match-file-name");
setupFileInput("letter-resume", "letter-file-name");
setupFileInput("interview-resume", "interview-file-name");

async function connectForm({ formId, endpoint, loadingId, resultId, errorId, render }) {
  const form = document.getElementById(formId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const processingConsent = form.querySelector('[name="processing_consent"]');
    if (processingConsent && !processingConsent.checked) {
      setError(errorId, "Confirm the data-processing notice before continuing.");
      processingConsent.focus();
      return;
    }
    document.getElementById(resultId).hidden = true;
    setLoading(form, loadingId, resultId, errorId, true);
    try {
      const result = await postForm(form, endpoint);
      updateUsage(result.remaining_usage);
      render(result);
      document.getElementById(resultId).hidden = false;
      document.getElementById(errorId).hidden = true;
      animateResults(resultId);
    } catch (error) {
      setError(errorId, error.message || "The request could not be completed.");
    } finally {
      setLoading(form, loadingId, resultId, errorId, false);
    }
  });
}

document.querySelectorAll(".account-data-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("Delete your saved resume history and trial usage data, then sign out? Provider records are managed separately.")) {
      event.preventDefault();
    }
  });
});

function animateResults(resultId) {
  if (prefersReducedMotion() || !window.gsap) return;
  const root = document.getElementById(resultId);
  const children = [...root.children].filter((child) => !child.hidden);
  window.gsap.fromTo(children, { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, duration: 0.58, stagger: 0.08, ease: "power3.out", clearProps: "all" });
}

connectForm({
  formId: "analysis-form", endpoint: "/api/analyze", loadingId: "analysis-loading", resultId: "analysis-results", errorId: "analysis-error",
  render: (result) => { renderResumeResult(result); },
});

connectForm({
  formId: "match-form", endpoint: "/api/job-match", loadingId: "match-loading", resultId: "match-results", errorId: "match-error",
  render: (result) => { const analysis = stripEmoji(result.analysis || ""); renderKeywords(result.keywords); renderMatchReadability(result.readability); setProse("match-body", analysis); downloads.match = stripEmoji(result.full_report || analysis); },
});

connectForm({
  formId: "letter-form", endpoint: "/api/cover-letter", loadingId: "letter-loading", resultId: "letter-results", errorId: "letter-error",
  render: (result) => { const letter = stripEmoji(result.cover_letter || ""); setProse("letter-body", letter); downloads.letter = letter; },
});

const toolSelect = document.getElementById("tool-name");
const toolTextField = document.getElementById("tool-text-field");
const toolFileField = document.getElementById("tool-file-field");
const toolContextFields = document.getElementById("tool-context-fields");
const toolTextLabel = document.getElementById("tool-text-label");
const toolText = document.getElementById("tool-text");
const toolHelp = document.getElementById("tool-help");
const quantifierWarning = document.getElementById("quantifier-warning");
const toolIntros = {
  "Action Verb Replacer": ["Find sharper ways to describe the work you led.", "01 / 05"],
  "Achievement Quantifier": ["Make outcomes concrete using only numbers you can verify.", "02 / 05"],
  "Bullet Point Improver": ["Give a responsibility or result a clearer shape.", "03 / 05"],
  "Section Reorganizer": ["Make the order of your experience easier to follow.", "04 / 05"],
  "Interview Question Generator": ["Turn your resume and target role into thoughtful practice.", "05 / 05"],
};
function updateToolFields() {
  const selected = toolSelect.value;
  const interview = selected === "Interview Question Generator";
  const section = selected === "Section Reorganizer";
  toolTextField.hidden = interview;
  toolFileField.hidden = !interview;
  toolContextFields.hidden = !section;
  quantifierWarning.hidden = selected !== "Achievement Quantifier";
  const labels = {
    "Action Verb Replacer": ["Resume bullet points", "Review each suggestion and keep the underlying experience accurate."],
    "Achievement Quantifier": ["Achievements to improve", "Suggestions may include illustrative numbers; replace them with verified results."],
    "Bullet Point Improver": ["Resume bullet points", "Review every rewrite to make sure it reflects your actual work."],
    "Section Reorganizer": ["Current resume sections", "Enter your current section names, one per line."],
  };
  if (labels[selected]) {
    toolTextLabel.textContent = labels[selected][0];
    toolHelp.textContent = labels[selected][1];
    toolText.placeholder = selected === "Section Reorganizer" ? "e.g. Summary, Experience, Education, Skills" : "Paste the content you want to work on…";
  }
  const intro = toolIntros[selected];
  if (intro) {
    document.getElementById("tool-selection-title").textContent = selected;
    document.getElementById("tool-selection-description").textContent = intro[0];
    document.querySelector(".tool-accent-count").textContent = intro[1];
  }
}
toolSelect.addEventListener("change", updateToolFields);
updateToolFields();

connectForm({
  formId: "tools-form", endpoint: "/api/tools", loadingId: "tools-loading", resultId: "tools-results", errorId: "tools-error",
  render: (result) => {
    const output = stripEmoji(result.output || "");
    setProse("tools-body", output);
    document.getElementById("tool-result-title").textContent = `${toolSelect.value} suggestions`;
    downloads.tool = output;
  },
});

document.getElementById("compare-button").addEventListener("click", renderComparison);
document.getElementById("retry-history").addEventListener("click", loadHistory);
document.getElementById("clear-history").addEventListener("click", async () => {
  if (!historyEntries.length || !window.confirm("Permanently delete all saved resume reviews for this account? This cannot be undone.")) return;
  const button = document.getElementById("clear-history");
  button.disabled = true;
  try {
    const response = await fetch("/api/history/clear", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRF-Token": csrfToken, Accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Saved history could not be cleared.");
    historyEntries.length = 0;
    renderHistory();
  } catch (error) {
    const status = document.getElementById("history-status");
    status.textContent = error.message || "Saved history could not be cleared. Try again.";
    status.hidden = false;
  } finally {
    button.disabled = false;
  }
});

if (window.gsap && !prefersReducedMotion()) {
  window.gsap.fromTo(".hero-copy-block", { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 0.65, ease: "power3.out", clearProps: "all" });
  window.gsap.fromTo(".engine-card", { autoAlpha: 0, y: 20, scale: 0.985 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.72, delay: 0.1, ease: "power3.out", clearProps: "all" });
}

const requestedView = window.location.hash.match(/^#view-(home|analyze|match|letter|history|tools)$/);
if (requestedView) activateView(requestedView[1]);

