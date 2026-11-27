"use strict";

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const historyEntries = [];
const downloads = { analysis: "", fullReport: "", match: "", letter: "", tool: "" };

function activateView(name, moveFocus = false) {
  document.querySelectorAll("[data-view]").forEach((tab) => {
    const active = tab.dataset.view === name;
    tab.classList.toggle("is-active", active);
    if (active) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
    tab.tabIndex = active || name === "home" ? 0 : -1;
    if (active && moveFocus) tab.focus();
  });
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    const active = panel.dataset.viewPanel === name;
    panel.hidden = !active;
    panel.classList.toggle("is-visible", active);
  });
  if (name === "history") renderHistory();
  if (name !== "home") selectEngineCapability(name, false);
  else selectEngineCapability(activeCapability, true);
  revealView(name);
}

document.querySelectorAll("[data-view]").forEach((tab) => {
  tab.addEventListener("click", () => activateView(tab.dataset.view));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...document.querySelectorAll("[data-view]")];
    const current = tabs.indexOf(tab);
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 :
      (current + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
    activateView(tabs[next].dataset.view, true);
  });
});

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
  history: { title: "History", copy: "Keep recent reviews together while this browser tab stays open.", action: "View session history" },
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
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

function updateUsage(usage) {
  if (!usage) return;
  const targets = {
    resume_analysis: "usage-resume",
    job_match: "usage-match",
    cover_letter: "usage-letter",
  };
  Object.entries(targets).forEach(([key, id]) => {
    const element = document.getElementById(id);
    if (element && Object.hasOwn(usage, key)) element.textContent = usage[key];
  });
}

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

function animateScore(score) {
  const scoreValue = document.getElementById("score-value");
  const progress = document.getElementById("score-progress");
  const scoreCard = document.querySelector(".score-card");
  const scoreVisual = document.querySelector(".score-visual");
  const marker = document.querySelector(".score-orbit-dot");
  const circumference = 301.6;
  const band = score >= 80 ? "strong" : score >= 60 ? "developing" : "early";
  const setProgress = (value) => {
    progress.style.strokeDasharray = String(circumference);
    progress.style.strokeDashoffset = String(circumference * (1 - value / 100));
  };
  const markerRadius = scoreVisual.clientWidth * (48 / 120);
  const markerAngle = (score / 100) * Math.PI * 2 - Math.PI / 2;
  marker.style.left = `${scoreVisual.clientWidth / 2 + Math.cos(markerAngle) * markerRadius - marker.offsetWidth / 2}px`;
  marker.style.top = `${scoreVisual.clientHeight / 2 + Math.sin(markerAngle) * markerRadius - marker.offsetHeight / 2}px`;
  marker.style.right = "auto";

  scoreCard.dataset.band = band;
  scoreCard.hidden = false;
  scoreCard.classList.remove("score-reveal");
  void scoreCard.offsetWidth;
  scoreCard.classList.add("score-reveal");

  if (prefersReducedMotion() || !window.gsap) {
    scoreValue.textContent = String(score);
    setProgress(score);
    marker.style.opacity = "1";
    marker.style.transform = "scale(1)";
    return;
  }

  scoreValue.textContent = "0";
  setProgress(0);
  const counter = { value: 0 };
  window.gsap.to(counter, {
    value: score,
    duration: 1.55,
    ease: "power3.out",
    onUpdate: () => {
      scoreValue.textContent = String(Math.round(counter.value));
      setProgress(counter.value);
    },
  });
  window.gsap.fromTo(marker, { scale: 0.25, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.48, delay: 0.9, ease: "back.out(2.2)", clearProps: "transform,opacity" });
}

function renderResumeResult(result) {
  document.getElementById("analysis-results").hidden = false;
  const scoreResults = document.getElementById("score-results");
  const score = result.score;
  const stats = result.stats;
  document.querySelector(".score-card").hidden = score === null;
  scoreResults.hidden = score === null && !stats;
  const filename = stripEmoji(result.filename || "");
  const analysis = stripEmoji(result.analysis || "");
  const fullReport = stripEmoji(result.full_report || "");
  document.getElementById("analysis-filename").textContent = filename;
  if (score !== null) {
    const label = score >= 80 ? "Strong foundations" : score >= 60 ? "Room to strengthen" : score >= 40 ? "Several opportunities" : "A useful starting point";
    document.getElementById("score-label").textContent = label;
    document.getElementById("score-svg-desc").textContent = `Heuristic score: ${score} out of 100.`;
    animateScore(score);
  }
  const metrics = document.getElementById("resume-metrics");
  metrics.replaceChildren();
  if (stats) {
    addMetric(metrics, "Word count", String(stats.word_count), "Current resume text");
    addMetric(metrics, "Action verbs", String(stats.action_verb_count), "Detected by the existing word list");
    addMetric(metrics, "Numbers detected", String(stats.quantifiable_achievements), "Numeric entries in extracted text");
    addMetric(metrics, "Contact details", stats.has_email && stats.has_phone ? "Email and phone found" : "Some details not found", "Detection uses the app’s existing patterns");
    addMetric(metrics, "Sentence count", String(stats.sentence_count));
    addMetric(metrics, "Avg. sentence length", `${Number(stats.avg_sentence_length).toFixed(1)} words`);
  }
  const atsSection = document.getElementById("ats-results");
  atsSection.hidden = !result.ats;
  if (result.ats) {
    document.getElementById("ats-status").textContent = stripEmoji(result.ats.status);
    document.getElementById("ats-score").textContent = `${result.ats.score}/100 text-check score`;
    const issues = document.getElementById("ats-issues");
    issues.replaceChildren();
    issues.className = "ats-issues";
    if (result.ats.issues.length) {
      result.ats.issues.forEach((issue) => {
        const chip = document.createElement("span");
        chip.className = "keyword-chip missing";
        chip.textContent = stripEmoji(issue);
        issues.append(chip);
      });
    } else {
      issues.textContent = "No major issues found by these text checks.";
    }
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
  addHistoryEntry({
    filename,
    score: result.score,
    stats: result.stats,
    analysis,
    fullReport,
    date: new Date().toLocaleString(),
  });
}

function addHistoryEntry(entry) {
  historyEntries.unshift({ ...entry, filename: stripEmoji(entry.filename || ""), analysis: stripEmoji(entry.analysis || ""), fullReport: stripEmoji(entry.fullReport || "") });
  if (historyEntries.length > 3) historyEntries.pop();
  renderHistory();
}

function renderHistory() {
  const list = document.getElementById("history-list");
  const empty = document.getElementById("history-empty");
  const compare = document.getElementById("comparison-panel");
  const clear = document.getElementById("clear-history");
  list.replaceChildren();
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
    date.textContent = entry.date;
    main.append(title, date);
    const score = document.createElement("span");
    score.className = "history-entry-score";
    score.textContent = entry.score === null ? "Score not shown" : `${entry.score}/100`;
    const actions = document.createElement("div");
    actions.className = "history-actions";
    const download = document.createElement("button");
    download.type = "button";
    download.className = "button button-secondary button-small";
    download.textContent = "Download";
    download.addEventListener("click", () => downloadText(entry.fullReport || entry.analysis, `resume-analysis-${index + 1}.txt`));
    actions.append(download);
    row.append(main, score, actions);
    list.append(row);
  });
  if (historyEntries.length >= 2) populateCompareSelects();
}

function populateCompareSelects() {
  ["version-a", "version-b"].forEach((id, selectIndex) => {
    const select = document.getElementById(id);
    const previous = select.value;
    select.replaceChildren();
    historyEntries.forEach((entry, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `${stripEmoji(entry.filename || "Resume")} · ${entry.date}`;
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
  if (first.score !== null && second.score !== null) addMetric(results, "Structure score", `${second.score}/100`, `${second.score - first.score >= 0 ? "+" : ""}${second.score - first.score} points`);
  addMetric(results, "Word count", String(secondStats.word_count ?? "—"), `${(secondStats.word_count ?? 0) - (firstStats.word_count ?? 0) >= 0 ? "+" : ""}${(secondStats.word_count ?? 0) - (firstStats.word_count ?? 0)}`);
  addMetric(results, "Action verbs", String(secondStats.action_verb_count ?? "—"), `${(secondStats.action_verb_count ?? 0) - (firstStats.action_verb_count ?? 0) >= 0 ? "+" : ""}${(secondStats.action_verb_count ?? 0) - (firstStats.action_verb_count ?? 0)}`);
  addMetric(results, "Numbers detected", String(secondStats.quantifiable_achievements ?? "—"), `${(secondStats.quantifiable_achievements ?? 0) - (firstStats.quantifiable_achievements ?? 0) >= 0 ? "+" : ""}${(secondStats.quantifiable_achievements ?? 0) - (firstStats.quantifiable_achievements ?? 0)}`);
  results.hidden = false;
}

function renderKeywords(keywords) {
  const panel = document.getElementById("keyword-results");
  panel.replaceChildren();
  panel.hidden = !keywords;
  if (!keywords) return;
  const title = document.createElement("div");
  title.className = "eyebrow";
  title.textContent = "Simple word overlap";
  const summary = document.createElement("div");
  summary.className = "keyword-summary";
  const percentage = document.createElement("strong");
  percentage.textContent = `${Number(keywords.match_percentage).toFixed(1)}%`;
  const description = document.createElement("span");
  description.className = "muted";
  description.textContent = "of distinct job-description terms also found in the resume text";
  summary.append(percentage, description);
  const columns = document.createElement("div");
  columns.className = "keyword-columns";
  [["Terms found in both texts", keywords.matching_keywords, "match"], ["Terms not found in resume text", keywords.missing_keywords, "missing"]].forEach(([label, values, className]) => {
    const group = document.createElement("div");
    const heading = document.createElement("h4");
    heading.textContent = label;
    const chips = document.createElement("div");
    chips.className = "keyword-list";
    if (!values.length) chips.textContent = "None detected";
    values.forEach((value) => {
      const chip = document.createElement("span");
      chip.className = `keyword-chip ${className}`;
      chip.textContent = stripEmoji(value);
      chips.append(chip);
    });
    group.append(heading, chips);
    columns.append(group);
  });
  panel.append(title, summary, columns);
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
  render: (result) => { const analysis = stripEmoji(result.analysis || ""); renderKeywords(result.keywords); setProse("match-body", analysis); downloads.match = analysis; },
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
    "Achievement Quantifier": ["Achievements to improve", "AI may suggest illustrative numbers; replace them with verified results."],
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
document.getElementById("clear-history").addEventListener("click", () => {
  if (!historyEntries.length || !window.confirm("Clear the resume reviews held in this browser tab? This cannot be undone.")) return;
  historyEntries.length = 0;
  renderHistory();
});

if (window.gsap && !prefersReducedMotion()) {
  window.gsap.fromTo(".hero-copy-block", { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 0.65, ease: "power3.out", clearProps: "all" });
  window.gsap.fromTo(".engine-card", { autoAlpha: 0, y: 20, scale: 0.985 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.72, delay: 0.1, ease: "power3.out", clearProps: "all" });
}

