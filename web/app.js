const providerStatus = document.getElementById("provider-status");
const captureState = document.getElementById("capture-state");
const startCaptureBtn = document.getElementById("start-capture-btn");
const stopCaptureBtn = document.getElementById("stop-capture-btn");
const capturePreview = document.getElementById("capture-preview");
const strategyNotes = document.getElementById("strategy-notes");
const generatePineBtn = document.getElementById("generate-pine-btn");
const pineOutput = document.getElementById("pine-output");
const capturesList = document.getElementById("captures-list");
const alertsList = document.getElementById("alerts-list");
const refreshCapturesBtn = document.getElementById("refresh-captures-btn");
const refreshAlertsBtn = document.getElementById("refresh-alerts-btn");

let captureRecorder = null;
let captureChunks = [];
let captureStream = null;
let captureStartedAt = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function tickClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function setStatus(text, state = "neutral") {
  captureState.textContent = text;
  captureState.dataset.state = state;
}

async function loadConfigStatus() {
  try {
    const response = await fetch("/api/config/status");
    const data = await response.json();
    const status = data.status || {};
    providerStatus.textContent = `model: ${status.active_provider || "local"} / ${status.paid_models_enabled ? "paid on" : "local first"}`;
  } catch {
    providerStatus.textContent = "model: unavailable";
  }
}

async function loadCaptures() {
  capturesList.innerHTML = `<div class="empty-row">Loading captures...</div>`;
  try {
    const response = await fetch("/api/captures?limit=8");
    const data = await response.json();
    const captures = data.captures || [];
    capturesList.innerHTML = captures.length
      ? captures.reverse().map(item => `
          <a class="feed-row" href="${escapeHtml(item.download_url)}" download>
            <b>${escapeHtml(item.filename)}</b>
            <span>${Math.round(Number(item.size_bytes || 0) / 1024)} KB · ${escapeHtml(item.transcript_status || "pending")}</span>
          </a>
        `).join("")
      : `<div class="empty-row">No recordings yet.</div>`;
  } catch (error) {
    capturesList.innerHTML = `<div class="empty-row">Could not load captures.</div>`;
  }
}

async function loadAlerts() {
  alertsList.innerHTML = `<div class="empty-row">Loading alerts...</div>`;
  try {
    const response = await fetch("/api/command-center");
    const data = await response.json();
    const alerts = (data.state && data.state.tradingview_alerts) || [];
    alertsList.innerHTML = alerts.length
      ? alerts.slice().reverse().map(alert => `
          <div class="feed-row">
            <b>${escapeHtml(alert.symbol || "UNKNOWN")} · ${escapeHtml(alert.action || "alert")}</b>
            <span>${escapeHtml(alert.timeframe || "")} · ${escapeHtml(alert.price || "")} · ${escapeHtml(alert.message || "")}</span>
          </div>
        `).join("")
      : `<div class="empty-row">No TradingView alerts received yet.</div>`;
  } catch {
    alertsList.innerHTML = `<div class="empty-row">Could not load TradingView alerts.</div>`;
  }
}

async function startCapture() {
  try {
    setStatus("requesting permission", "working");
    const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
    let micStream = null;
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      micStream = null;
    }

    const tracks = [
      ...screenStream.getVideoTracks(),
      ...screenStream.getAudioTracks(),
      ...(micStream ? micStream.getAudioTracks() : [])
    ];

    captureStream = new MediaStream(tracks);
    captureChunks = [];
    captureStartedAt = new Date();
    captureRecorder = new MediaRecorder(captureStream, { mimeType: "video/webm" });
    captureRecorder.ondataavailable = event => {
      if (event.data && event.data.size) captureChunks.push(event.data);
    };
    captureRecorder.onstop = uploadCapture;
    captureRecorder.start(1000);
    capturePreview.srcObject = captureStream;
    startCaptureBtn.disabled = true;
    stopCaptureBtn.disabled = false;
    setStatus("recording", "live");
  } catch (error) {
    setStatus("blocked", "error");
    pineOutput.textContent = `Capture blocked: ${error.message || error}`;
  }
}

function stopCapture() {
  if (captureRecorder && captureRecorder.state !== "inactive") {
    setStatus("saving", "working");
    captureRecorder.stop();
  }
  if (captureStream) {
    captureStream.getTracks().forEach(track => track.stop());
  }
}

async function uploadCapture() {
  const blob = new Blob(captureChunks, { type: "video/webm" });
  const stamp = (captureStartedAt || new Date()).toISOString().replace(/[:.]/g, "-");
  try {
    const response = await fetch(`/api/captures?filename=trade-capture-${encodeURIComponent(stamp)}.webm`, {
      method: "POST",
      headers: { "Content-Type": "video/webm" },
      body: blob
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.detail || "Capture upload failed.");
    setStatus("saved", "ready");
    pineOutput.innerHTML = `Recording saved: <a href="${escapeHtml(data.capture.download_url)}" download>${escapeHtml(data.capture.filename)}</a>`;
    await loadCaptures();
  } catch (error) {
    setStatus("save failed", "error");
    pineOutput.textContent = `Capture save failed: ${error.message || error}`;
  } finally {
    startCaptureBtn.disabled = false;
    stopCaptureBtn.disabled = true;
    captureRecorder = null;
    captureStream = null;
    captureChunks = [];
  }
}

async function generatePineStrategy() {
  const notes = strategyNotes.value.trim();
  pineOutput.textContent = "Generating Pine strategy...";
  try {
    const response = await fetch("/api/strategies/pine", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "AstraCore Scalp Assist",
        notes
      })
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.detail || "Pine generation failed.");
    pineOutput.innerHTML = `Generated: <a href="${escapeHtml(data.strategy.download_url)}" download>${escapeHtml(data.strategy.filename)}</a>`;
  } catch (error) {
    pineOutput.textContent = `Generation failed: ${error.message || error}`;
  }
}

tickClock();
setInterval(tickClock, 1000);
startCaptureBtn.addEventListener("click", startCapture);
stopCaptureBtn.addEventListener("click", stopCapture);
generatePineBtn.addEventListener("click", generatePineStrategy);
refreshCapturesBtn.addEventListener("click", loadCaptures);
refreshAlertsBtn.addEventListener("click", loadAlerts);
loadConfigStatus();
loadCaptures();
loadAlerts();
