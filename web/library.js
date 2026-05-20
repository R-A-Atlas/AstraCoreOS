const state = {
  captures: [],
  selected: null,
  query: "",
  aiBrain: {
    enabled: false,
    exportsEnabled: false,
    reviewsEnabled: false,
  },
  memorySummary: null,
};

const els = {
  list: document.querySelector("#library-list"),
  search: document.querySelector("#capture-search"),
  refresh: document.querySelector("#refresh-captures-btn"),
  empty: document.querySelector("#empty-detail"),
  detail: document.querySelector("#capture-detail"),
  video: document.querySelector("#detail-video"),
  title: document.querySelector("#detail-title"),
  meta: document.querySelector("#detail-meta"),
  aiStatus: document.querySelector("#ai-status"),
  setupType: document.querySelector("#setup-type"),
  tradeGrade: document.querySelector("#trade-grade"),
  displayName: document.querySelector("#display-name"),
  saveName: document.querySelector("#save-name-btn"),
  deleteCapture: document.querySelector("#delete-capture-btn"),
  transcriptView: document.querySelector("#transcript-view"),
  transcriptDownload: document.querySelector("#transcript-download"),
  exportBtns: document.querySelectorAll(".library-export-btn"),
  exportResult: document.querySelector("#library-export-result"),
  generatedExports: document.querySelector("#generated-exports"),
  localTemplateMode: document.querySelector("#local-template-mode"),
  runReview: document.querySelector("#run-review-btn"),
  reviewStatus: document.querySelector("#review-status"),
  reviewOutput: document.querySelector("#review-output"),
  memoryInsight: document.querySelector("#memory-insight"),
  voiceRing: document.querySelector("#voice-ring"),
  voiceRingLabel: document.querySelector("#voice-ring-label"),
  voiceRingSubtitle: document.querySelector("#voice-ring-subtitle"),
};

function setVoiceRing(mode = "idle", label = "Idle", subtitle = "AI coach standing by") {
  if (!els.voiceRing) {
    return;
  }
  els.voiceRing.dataset.state = mode;
  els.voiceRingLabel.textContent = label;
  els.voiceRingSubtitle.textContent = subtitle;
}

async function loadConfigStatus() {
  try {
    const response = await fetch("/api/config/status");
    const data = await response.json();
    const aiBrain = data.status?.ai_brain || {};
    state.aiBrain.enabled = Boolean(aiBrain.enabled);
    state.aiBrain.exportsEnabled = Boolean(aiBrain.exports_enabled);
    state.aiBrain.reviewsEnabled = Boolean(aiBrain.reviews_enabled);
  } catch {
    state.aiBrain.enabled = false;
    state.aiBrain.exportsEnabled = false;
    state.aiBrain.reviewsEnabled = false;
  }
  setVoiceRing(
    state.aiBrain.enabled ? "idle" : "error",
    state.aiBrain.enabled ? "Idle" : "AI disabled",
    state.aiBrain.enabled ? "Select a capture" : "Enable AI flags in .env",
  );
  renderExportLabels();
}

async function loadMemorySummary() {
  try {
    const response = await fetch("/api/trading-memory/summary");
    const data = await response.json();
    state.memorySummary = data.summary || null;
  } catch {
    state.memorySummary = null;
  }
  renderMemoryInsight();
}

async function loadCaptures() {
  els.list.innerHTML = '<div class="result-box">Loading captures...</div>';
  try {
    const response = await fetch("/api/captures?limit=50&offset=0");
    const data = await response.json();
    state.captures = data.captures || [];
    renderList();
    if (!state.selected && state.captures.length) {
      selectCapture(state.captures[0].id);
    } else if (state.selected) {
      const stillExists = state.captures.find((capture) => capture.id === state.selected.id);
      if (stillExists) {
        selectCapture(stillExists.id);
      } else {
        clearDetail();
      }
    }
  } catch {
    els.list.innerHTML = '<div class="result-box">Could not load captures.</div>';
  }
}

function renderList() {
  const filtered = state.captures.filter((capture) => {
    const haystack = [
      capture.display_name,
      capture.filename,
      capture.transcript_status,
      capture.analysis_status,
      ...(capture.tags || []),
    ].join(" ").toLowerCase();
    return haystack.includes(state.query.toLowerCase());
  });
  if (!filtered.length) {
    els.list.innerHTML = '<div class="result-box">No captures match this search.</div>';
    return;
  }
  els.list.innerHTML = filtered.map((capture) => `
    <button class="library-row ${state.selected?.id === capture.id ? "active" : ""}" type="button" data-capture-id="${capture.id}">
      <span class="capture-thumb"></span>
      <span>
        <span class="capture-name">${escapeHtml(capture.display_name || capture.filename)}</span>
        <span class="capture-meta">${formatBytes(capture.size_bytes)} - ${new Date(capture.created_at).toLocaleString()}</span>
      </span>
    </button>
  `).join("");
  els.list.querySelectorAll("[data-capture-id]").forEach((button) => {
    button.addEventListener("click", () => selectCapture(button.dataset.captureId));
  });
}

async function selectCapture(captureId) {
  const capture = state.captures.find((item) => item.id === captureId);
  if (!capture) {
    clearDetail();
    return;
  }
  state.selected = capture;
  els.empty.classList.add("hidden");
  els.detail.classList.remove("hidden");
  els.video.src = capture.download_url;
  els.title.textContent = capture.display_name || capture.filename;
  els.meta.textContent = `${capture.filename} - ${formatBytes(capture.size_bytes)} - ${new Date(capture.created_at).toLocaleString()}`;
  els.aiStatus.textContent = capture.ai_review_status || "not_started";
  els.setupType.textContent = capture.setup_type || "unset";
  els.tradeGrade.textContent = capture.trade_grade || "unset";
  els.displayName.value = capture.display_name || capture.filename;
  setVoiceRing(
    capture.has_ai_review ? "complete" : "idle",
    capture.has_ai_review ? "Review saved" : "Capture selected",
    capture.ready_for_ai ? "Ready for AI coach" : "Needs video + voice context",
  );
  renderTranscript(capture);
  renderGeneratedExports(capture);
  renderAiReadiness(capture);
  renderReview(capture.review || null);
  renderReviewReadiness(capture);
  renderList();
}

function clearDetail() {
  state.selected = null;
  els.empty.classList.remove("hidden");
  els.detail.classList.add("hidden");
  els.video.removeAttribute("src");
  els.video.load();
  setVoiceRing("idle", "Idle", "Select a capture");
  renderList();
}

async function renderTranscript(capture) {
  if (!capture.transcript_download_url) {
    els.transcriptDownload.classList.add("hidden");
    els.transcriptView.textContent = "No transcript saved for this capture.";
    return;
  }
  els.transcriptDownload.classList.remove("hidden");
  els.transcriptDownload.href = capture.transcript_download_url;
  try {
    const response = await fetch(capture.transcript_download_url);
    els.transcriptView.textContent = await response.text();
  } catch {
    els.transcriptView.textContent = "Could not load transcript.";
  }
}

function renderGeneratedExports(capture) {
  const exports = capture.generated_exports || [];
  if (!exports.length) {
    els.generatedExports.innerHTML = "";
    return;
  }
  els.generatedExports.innerHTML = exports.slice().reverse().map((item) => `
    <div class="export-history-row">
      <span>${escapeHtml(item.type || "export")} - ${escapeHtml(item.source || "local_template")} - ${escapeHtml(item.filename || "output")}</span>
      <span>${item.created_at ? new Date(item.created_at).toLocaleString() : ""}</span>
    </div>
  `).join("");
}

function renderReview(review) {
  if (!review) {
    els.reviewOutput.innerHTML = "";
    return;
  }
  const notes = Array.isArray(review.timestamped_notes) ? review.timestamped_notes : [];
  els.reviewOutput.innerHTML = `
    <div class="review-grid">
      <div class="review-pill"><strong>${escapeHtml(review.trade_grade || "Ungraded")}</strong><span>Trade grade</span></div>
      <div class="review-pill"><strong>${escapeHtml(review.setup_type || "Unclassified")}</strong><span>Setup type</span></div>
      <div class="review-pill"><strong>${escapeHtml(review.source || "ai_multimodal_review")}</strong><span>Source</span></div>
    </div>
    <div class="result-box">${escapeHtml(review.summary || "No summary returned.")}</div>
    ${renderReviewList("Strengths", review.strengths)}
    ${renderReviewList("Mistakes", review.mistakes)}
    ${renderReviewList("Strategy rules", review.strategy_rules)}
    <div class="result-box"><strong>Next focus</strong><br>${escapeHtml(review.next_practice_focus || "No practice focus returned.")}</div>
    ${notes.map((note) => `
      <div class="timestamp-note">
        <b>${escapeHtml(note.timecode || "00:00")} - ${escapeHtml(note.severity || "medium")}</b>
        <strong>${escapeHtml(note.label || "Observation")}</strong>
        <span>${escapeHtml(note.observation || "")}</span><br>
        <span>${escapeHtml(note.coaching_note || "")}</span>
      </div>
    `).join("")}
  `;
}

function renderReviewList(title, items) {
  if (!Array.isArray(items) || !items.length) {
    return "";
  }
  return `
    <div>
      <strong>${escapeHtml(title)}</strong>
      <ul class="review-list">
        ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderExportLabels() {
  const localMode = Boolean(els.localTemplateMode?.checked);
  els.exportBtns.forEach((button) => {
    const exportType = button.dataset.exportType || "pine";
    const label = exportType === "mt5" ? "MT5 / MQL5" : exportType === "instructions" ? "Visual Playbook" : "Pine Export";
    button.textContent = localMode ? `Local Template ${label}` : `AI ${label}`;
  });
  if (state.selected) {
    renderAiReadiness(state.selected);
  }
}

function renderAiReadiness(capture) {
  if (els.localTemplateMode?.checked) {
    els.exportResult.textContent = "Local Template mode uses the selected transcript only. It is not AI chart analysis.";
    return;
  }
  if (!state.aiBrain.enabled || !state.aiBrain.exportsEnabled) {
    els.exportResult.textContent = "AI Brain disabled. Enable ASTRA_AI_BRAIN_ENABLED and ASTRA_AI_EXPORTS_ENABLED in .env, then restart the server.";
    return;
  }
  if (!capture.ready_for_ai) {
    els.exportResult.textContent = "This capture is not ready for AI export. It needs a saved video plus mic audio or transcript context.";
    return;
  }
  els.exportResult.textContent = "Ready for AI export. AstraCore will send the selected video plus voice/transcript context to the multimodal AI Brain.";
}

function renderReviewReadiness(capture) {
  els.runReview.disabled = true;
  if (!state.aiBrain.enabled || !state.aiBrain.reviewsEnabled) {
    els.reviewStatus.textContent = "AI reviews disabled. Enable ASTRA_AI_BRAIN_ENABLED and ASTRA_AI_REVIEWS_ENABLED in .env, then restart the server.";
    return;
  }
  if (!capture.ready_for_ai) {
    els.reviewStatus.textContent = "This capture is not ready for AI review. It needs saved video plus mic audio or transcript context.";
    return;
  }
  els.runReview.disabled = false;
  els.reviewStatus.textContent = capture.has_ai_review
    ? "AI review saved. Run again to refresh the coaching memory."
    : "Ready for AI review. AstraCore will analyze the selected video plus voice/transcript context.";
}

function renderMemoryInsight() {
  const summary = state.memorySummary;
  if (!summary || !summary.total_reviews) {
    els.memoryInsight.textContent = "No AI-reviewed trading sessions yet.";
    return;
  }
  els.memoryInsight.innerHTML = `
    <div class="result-box">${escapeHtml(summary.coach_summary || "")}</div>
    <div class="review-grid">
      ${renderMemoryPill("Reviews", summary.total_reviews)}
      ${renderMemoryPill("Top setup", summary.common_setups?.[0]?.setup_type || "none")}
      ${renderMemoryPill("Main mistake", summary.repeated_mistakes?.[0]?.mistake || "none")}
    </div>
    ${renderMemoryRows("Rules to keep", summary.rules_to_keep, "rule")}
    ${renderMemoryRows("Rules to avoid", summary.rules_to_avoid, "rule")}
  `;
}

function renderMemoryPill(label, value) {
  return `<div class="memory-pill"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`;
}

function renderMemoryRows(title, rows, key) {
  if (!Array.isArray(rows) || !rows.length) {
    return "";
  }
  return `
    <div>
      <strong>${escapeHtml(title)}</strong>
      <ul class="review-list">
        ${rows.slice(0, 5).map((row) => `<li>${escapeHtml(row[key] || "")} (${escapeHtml(row.count || 1)})</li>`).join("")}
      </ul>
    </div>
  `;
}

async function saveName() {
  if (!state.selected) {
    return;
  }
  els.saveName.disabled = true;
  setVoiceRing("reviewing", "Saving", "Updating capture name");
  try {
    const response = await fetch(`/api/captures/${state.selected.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: els.displayName.value.trim() }),
    });
    if (!response.ok) {
      throw new Error("Rename failed.");
    }
    const data = await response.json();
    state.captures = state.captures.map((capture) => capture.id === data.capture.id ? data.capture : capture);
    selectCapture(data.capture.id);
    setVoiceRing("complete", "Saved", "Capture name updated");
  } catch (error) {
    els.exportResult.textContent = error.message || "Could not rename capture.";
    setVoiceRing("error", "Save failed", error.message || "Could not rename capture");
  } finally {
    els.saveName.disabled = false;
  }
}

async function deleteCapture() {
  if (!state.selected) {
    return;
  }
  const name = state.selected.display_name || state.selected.filename;
  if (!window.confirm(`Delete "${name}" permanently? This removes the video and transcript.`)) {
    return;
  }
  try {
    setVoiceRing("reviewing", "Deleting", "Removing capture");
    const response = await fetch(`/api/captures/${state.selected.id}`, { method: "DELETE" });
    if (!response.ok) {
      throw new Error("Delete failed.");
    }
    state.captures = state.captures.filter((capture) => capture.id !== state.selected.id);
    clearDetail();
    if (state.captures.length) {
      selectCapture(state.captures[0].id);
    } else {
      setVoiceRing("idle", "Idle", "No captures saved");
    }
  } catch (error) {
    els.exportResult.textContent = error.message || "Could not delete capture.";
    setVoiceRing("error", "Delete failed", error.message || "Could not delete capture");
  }
}

async function exportSelected(exportType) {
  if (!state.selected) {
    return;
  }
  const exportMode = els.localTemplateMode?.checked ? "local" : "ai";
  els.exportBtns.forEach((button) => {
    button.disabled = true;
  });
  els.exportResult.textContent = exportMode === "ai"
    ? "Building AI export from selected video plus voice/transcript context..."
    : "Building Local Template export from selected capture transcript...";
  setVoiceRing(
    exportMode === "ai" ? "exporting" : "reviewing",
    exportMode === "ai" ? "AI exporting" : "Local export",
    exportMode === "ai" ? "Video + transcript in use" : "Transcript template in use",
  );
  try {
    const response = await fetch(`/api/captures/${state.selected.id}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: els.displayName.value.trim() || "AstraCore Scalp Assist",
        export_type: exportType,
        export_mode: exportMode,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Export failed.");
    }
    state.captures = state.captures.map((capture) => capture.id === data.capture.id ? data.capture : capture);
    state.selected = data.capture;
    els.exportResult.innerHTML = `
      <strong>${escapeHtml(data.strategy.title)}</strong><br>
      ${escapeHtml(data.strategy.summary)}<br>
      Source: ${escapeHtml(data.strategy.source || exportMode)}<br>
      <a href="${data.strategy.download_url}" download>Download ${escapeHtml(data.strategy.filename)}</a>
    `;
    renderGeneratedExports(data.capture);
    renderList();
    setVoiceRing("complete", "Export ready", data.strategy?.source || exportMode);
  } catch (error) {
    els.exportResult.textContent = error.message || "Could not generate export.";
    setVoiceRing("error", "Export failed", error.message || "Could not generate export");
  } finally {
    els.exportBtns.forEach((button) => {
      button.disabled = false;
    });
  }
}

async function runAiReview() {
  if (!state.selected) {
    return;
  }
  els.runReview.disabled = true;
  els.reviewStatus.textContent = "Running AI review from selected video plus voice/transcript context...";
  setVoiceRing("reviewing", "Reviewing", "Watching capture + transcript");
  try {
    const response = await fetch(`/api/captures/${state.selected.id}/review`, { method: "POST" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "AI review failed.");
    }
    state.captures = state.captures.map((capture) => capture.id === data.capture.id ? data.capture : capture);
    state.selected = data.capture;
    state.memorySummary = data.memory || state.memorySummary;
    els.aiStatus.textContent = data.capture.ai_review_status || "complete";
    els.setupType.textContent = data.capture.setup_type || "unset";
    els.tradeGrade.textContent = data.capture.trade_grade || "unset";
    els.reviewStatus.textContent = "AI review complete. Coaching memory updated.";
    renderReview(data.review);
    renderMemoryInsight();
    renderList();
    setVoiceRing("complete", "Review complete", "Trading memory updated");
  } catch (error) {
    els.reviewStatus.textContent = error.message || "Could not run AI review.";
    setVoiceRing("error", "Review failed", error.message || "Could not run AI review");
  } finally {
    renderReviewReadiness(state.selected);
  }
}

function formatBytes(bytes) {
  if (!bytes) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

els.search.addEventListener("input", () => {
  state.query = els.search.value;
  renderList();
});
els.refresh.addEventListener("click", loadCaptures);
els.saveName.addEventListener("click", saveName);
els.deleteCapture.addEventListener("click", deleteCapture);
els.exportBtns.forEach((button) => {
  button.addEventListener("click", () => exportSelected(button.dataset.exportType || "pine"));
});
els.localTemplateMode?.addEventListener("change", renderExportLabels);
els.runReview.addEventListener("click", runAiReview);

loadConfigStatus();
loadMemorySummary();
loadCaptures();
