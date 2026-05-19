const state = {
  screenStream: null,
  micStream: null,
  mixedStream: null,
  mediaRecorder: null,
  chunks: [],
  recording: false,
  paused: false,
  micEnabled: true,
  seconds: 0,
  timerId: null,
  waveformId: null,
  audioContext: null,
  transcriptFinal: "",
  transcriptInterim: "",
  recognition: null,
};

const els = {
  clock: document.querySelector("#studio-clock"),
  recordingPill: document.querySelector("#recording-pill"),
  previewFrame: document.querySelector("#preview-frame"),
  preview: document.querySelector("#screen-preview"),
  previewEmpty: document.querySelector("#preview-empty"),
  previewHud: document.querySelector("#preview-hud"),
  previewStatus: document.querySelector("#preview-status"),
  liveDot: document.querySelector("#live-dot"),
  sourceLabel: document.querySelector("#source-label"),
  resolutionHud: document.querySelector("#resolution-hud"),
  captionOverlay: document.querySelector("#caption-overlay"),
  stage: document.querySelector("#studio-stage"),
  monitorStrip: document.querySelector("#monitor-strip"),
  connectDisplayBtn: document.querySelector("#connect-display-btn"),
  startSessionBtn: document.querySelector("#start-session-btn"),
  finishSessionBtn: document.querySelector("#finish-session-btn"),
  pauseSessionBtn: document.querySelector("#pause-session-btn"),
  pauseIcon: document.querySelector("#pause-icon"),
  micBtn: document.querySelector("#mic-btn"),
  micIcon: document.querySelector("#mic-icon"),
  transcriptStatus: document.querySelector("#transcript-status"),
  waveform: document.querySelector("#waveform"),
  timer: document.querySelector("#session-timer"),
  tray: document.querySelector("#captures-tray"),
  openTrayBtn: document.querySelector("#open-tray-btn"),
  closeTrayBtn: document.querySelector("#close-tray-btn"),
  capturesList: document.querySelector("#captures-list"),
  strategyDrawer: document.querySelector(".strategy-drawer"),
  openStrategyBtn: document.querySelector("#open-strategy-btn"),
  collapseStrategyBtn: document.querySelector("#collapse-strategy-btn"),
  strategyName: document.querySelector("#strategy-name"),
  strategyNotes: document.querySelector("#strategy-notes"),
  generatePineBtn: document.querySelector("#generate-pine-btn"),
  exportBtns: document.querySelectorAll(".export-btn, #generate-pine-btn"),
  pineResult: document.querySelector("#pine-result"),
};

const icons = {
  pause: '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
  play: '<polygon points="7,4 20,12 7,20"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  micOff: '<path d="M3 3l18 18"/><path d="M9 9v2a3 3 0 0 0 5.12 2.12M15 13.34V6a3 3 0 0 0-5.94-.6"/><path d="M19 11a7 7 0 0 1-.46 2.5M12 18v3"/>',
};

function setClock() {
  els.clock.textContent = new Date().toLocaleTimeString("en-GB");
}

function formatDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function setRecordingUi() {
  els.recordingPill.classList.toggle("hidden", !state.recording);
  els.previewFrame.classList.toggle("recording", state.recording && !state.paused);
  els.startSessionBtn.classList.toggle("hidden", state.recording);
  els.finishSessionBtn.classList.toggle("hidden", !state.recording);
  els.pauseSessionBtn.classList.toggle("hidden", !state.recording);
  els.timer.textContent = formatDuration(state.seconds);
  els.timer.classList.toggle("live", state.recording && !state.paused);
  els.timer.classList.toggle("paused", state.recording && state.paused);
  els.previewStatus.textContent = state.recording ? (state.paused ? "Paused" : "Live") : "Preview";
  els.pauseSessionBtn.setAttribute("aria-label", state.paused ? "Resume recording" : "Pause recording");
  els.pauseIcon.innerHTML = state.paused ? icons.play : icons.pause;
}

function setMicUi() {
  els.micBtn.classList.toggle("muted", !state.micEnabled);
  els.micIcon.innerHTML = state.micEnabled ? icons.mic : icons.micOff;
  updateTranscriptStatus();
}

function setPreview(stream) {
  state.screenStream = stream;
  els.preview.srcObject = stream;
  els.previewEmpty.classList.add("hidden");
  els.previewHud.classList.remove("hidden");
  els.resolutionHud.classList.remove("hidden");

  const track = stream.getVideoTracks()[0];
  const settings = track.getSettings();
  els.sourceLabel.textContent = track.label || "Screen";
  els.resolutionHud.textContent = `${settings.width || 0}x${settings.height || 0} · ${Math.round(settings.frameRate || 0)}fps`;
  track.onended = stopSession;
  els.preview.play().catch(() => {});
}

async function requestDisplay() {
  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: {
      frameRate: { ideal: 30, max: 60 },
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    },
    audio: false,
  });
  setPreview(stream);
  return stream;
}

async function requestMic() {
  if (!state.micEnabled) {
    return null;
  }
  try {
    state.micStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
      video: false,
    });
    startWaveform();
    return state.micStream;
  } catch {
    state.micEnabled = false;
    setMicUi();
    return null;
  }
}

function buildMixedStream() {
  const tracks = [];
  if (state.screenStream) {
    tracks.push(...state.screenStream.getVideoTracks());
  }
  if (state.micStream && state.micEnabled) {
    tracks.push(...state.micStream.getAudioTracks());
  }
  state.mixedStream = new MediaStream(tracks);
  return state.mixedStream;
}

async function startSession() {
  try {
    if (!state.screenStream) {
      await requestDisplay();
    }
    if (state.micEnabled && !state.micStream) {
      await requestMic();
    }

    const stream = buildMixedStream();
    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
      ? "video/webm;codecs=vp9,opus"
      : "video/webm";
    state.chunks = [];
    state.transcriptFinal = "";
    state.transcriptInterim = "";
    updateCaptionOverlay();
    state.mediaRecorder = new MediaRecorder(stream, { mimeType });
    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        state.chunks.push(event.data);
      }
    };
    state.mediaRecorder.onstop = saveRecording;
    state.mediaRecorder.start(1000);
    state.recording = true;
    state.paused = false;
    state.seconds = 0;
    startTimer();
    startSpeechRecognition();
    setRecordingUi();
  } catch (error) {
    els.pineResult.textContent = error.message || "Could not start recording.";
  }
}

function startTimer() {
  window.clearInterval(state.timerId);
  state.timerId = window.setInterval(() => {
    if (state.recording && !state.paused) {
      state.seconds += 1;
      setRecordingUi();
    }
  }, 1000);
}

function pauseSession() {
  if (!state.mediaRecorder || !state.recording) {
    return;
  }
  if (state.paused) {
    state.mediaRecorder.resume();
    state.paused = false;
  } else {
    state.mediaRecorder.pause();
    state.paused = true;
  }
  setRecordingUi();
}

function stopSession() {
  window.clearInterval(state.timerId);
  stopSpeechRecognition();
  if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
    state.mediaRecorder.stop();
  } else {
    cleanupStreams();
  }
  state.recording = false;
  state.paused = false;
  setRecordingUi();
}

async function saveRecording() {
  const blob = new Blob(state.chunks, { type: "video/webm" });
  const transcript = getTranscriptText();
  cleanupStreams();
  if (!blob.size) {
    els.pineResult.textContent = "Recording stopped, but no video data was captured.";
    return;
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `trade-review-${stamp}.webm`;
  try {
    const params = new URLSearchParams({ filename });
    if (transcript) {
      params.set("transcript", transcript);
    }
    const response = await fetch(`/api/captures?${params.toString()}`, {
      method: "POST",
      headers: { "Content-Type": "video/webm" },
      body: blob,
    });
    if (!response.ok) {
      throw new Error(`Save failed with ${response.status}`);
    }
    const data = await response.json();
    const transcriptLink = data.capture.transcript_download_url
      ? `<br><a href="${data.capture.transcript_download_url}" download>Download transcript</a>`
      : "";
    els.pineResult.innerHTML = `Capture saved: <a href="${data.capture.download_url}" download>${data.capture.filename}</a>${transcriptLink}<br>Choose Pine Script, MT5/MQL5, or Trade Instructions. The latest transcript will be used automatically.`;
    await loadCaptures();
    openTray();
  } catch (error) {
    els.pineResult.textContent = error.message || "Could not save capture.";
  }
}

function cleanupStreams() {
  for (const stream of [state.screenStream, state.micStream]) {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
  }
  state.screenStream = null;
  state.micStream = null;
  state.mixedStream = null;
  els.preview.srcObject = null;
  els.previewEmpty.classList.remove("hidden");
  els.previewHud.classList.add("hidden");
  els.resolutionHud.classList.add("hidden");
  els.captionOverlay.classList.add("hidden");
  stopWaveform();
}

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function startSpeechRecognition() {
  const Recognition = getSpeechRecognitionCtor();
  if (!Recognition || !state.micEnabled) {
    updateTranscriptStatus();
    updateCaptionOverlay();
    return;
  }
  const recognition = new Recognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";
  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const text = event.results[i][0].transcript.trim();
      if (event.results[i].isFinal) {
        state.transcriptFinal = `${state.transcriptFinal} ${text}`.trim();
      } else {
        interim = `${interim} ${text}`.trim();
      }
    }
    state.transcriptInterim = interim;
    updateCaptionOverlay();
    updateTranscriptStatus();
  };
  recognition.onerror = () => updateTranscriptStatus("transcript paused");
  recognition.onend = () => {
    if (state.recording && !state.paused && state.micEnabled) {
      try {
        recognition.start();
      } catch {
        updateTranscriptStatus("transcript paused");
      }
    }
  };
  state.recognition = recognition;
  try {
    recognition.start();
  } catch {
    updateTranscriptStatus("transcript unavailable");
  }
  updateTranscriptStatus();
}

function stopSpeechRecognition() {
  if (state.recognition) {
    state.recognition.onend = null;
    try {
      state.recognition.stop();
    } catch {}
  }
  state.recognition = null;
  state.transcriptInterim = "";
  updateTranscriptStatus();
  updateCaptionOverlay();
}

function getTranscriptText() {
  return `${state.transcriptFinal} ${state.transcriptInterim}`.trim();
}

function updateCaptionOverlay() {
  const transcript = getTranscriptText();
  if (!transcript) {
    els.captionOverlay.classList.add("hidden");
    els.captionOverlay.textContent = "Live transcript will appear here.";
    return;
  }
  els.captionOverlay.classList.remove("hidden");
  els.captionOverlay.textContent = transcript.slice(-220);
}

function updateTranscriptStatus(forcedText = "") {
  if (forcedText) {
    els.transcriptStatus.textContent = forcedText;
  } else if (!state.micEnabled) {
    els.transcriptStatus.textContent = "mic muted";
  } else if (!getSpeechRecognitionCtor()) {
    els.transcriptStatus.textContent = "browser transcript off";
  } else if (state.recording) {
    els.transcriptStatus.textContent = "live transcript";
  } else {
    els.transcriptStatus.textContent = "transcript ready";
  }
}

function startWaveform() {
  stopWaveform();
  if (!state.micStream) {
    return;
  }

  const canvas = els.waveform;
  const context = canvas.getContext("2d");
  state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = state.audioContext.createMediaStreamSource(state.micStream);
  const analyser = state.audioContext.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);
  const data = new Uint8Array(analyser.fftSize);

  function draw() {
    const width = canvas.width;
    const height = canvas.height;
    context.clearRect(0, 0, width, height);
    analyser.getByteTimeDomainData(data);
    const bars = 26;
    const step = Math.floor(data.length / bars);
    const barWidth = width / bars - 2;
    for (let i = 0; i < bars; i += 1) {
      let sum = 0;
      for (let j = 0; j < step; j += 1) {
        const value = (data[i * step + j] - 128) / 128;
        sum += value * value;
      }
      const amp = Math.sqrt(sum / step);
      const barHeight = Math.max(2, amp * height * 2.8);
      context.fillStyle = "#a78bfa";
      context.globalAlpha = 0.35 + amp * 2;
      context.fillRect(i * (barWidth + 2), (height - barHeight) / 2, barWidth, barHeight);
    }
    state.waveformId = window.requestAnimationFrame(draw);
  }
  draw();
}

function stopWaveform() {
  window.cancelAnimationFrame(state.waveformId);
  state.waveformId = null;
  const context = els.waveform.getContext("2d");
  context.clearRect(0, 0, els.waveform.width, els.waveform.height);
  if (state.audioContext) {
    state.audioContext.close();
    state.audioContext = null;
  }
}

function toggleMic() {
  state.micEnabled = !state.micEnabled;
  if (!state.micEnabled && state.micStream) {
    state.micStream.getTracks().forEach((track) => track.stop());
    state.micStream = null;
    stopWaveform();
  }
  setMicUi();
}

async function loadCaptures() {
  els.capturesList.innerHTML = '<div class="result-box">Loading captures...</div>';
  try {
    const response = await fetch("/api/captures?limit=4");
    const data = await response.json();
    const captures = data.captures || [];
    if (!captures.length) {
      els.capturesList.innerHTML = '<div class="result-box">No captures saved yet.</div>';
      return;
    }
    els.capturesList.innerHTML = captures.map((capture) => {
      const transcriptLink = capture.transcript_download_url
        ? `<a class="transcript-link" href="${capture.transcript_download_url}" download>Transcript</a>`
        : "";
      return `
      <div class="capture-item-wrap">
      <a class="capture-item" href="${capture.download_url}" download>
        <span class="capture-thumb"></span>
        <span>
          <span class="capture-name">${escapeHtml(capture.display_name || capture.filename)}</span>
          <span class="capture-meta">${formatBytes(capture.size_bytes)} · ${new Date(capture.created_at).toLocaleString()}</span>
        </span>
      </a>
      ${transcriptLink}
      </div>
    `;
    }).join("");
  } catch {
    els.capturesList.innerHTML = '<div class="result-box">Could not load captures.</div>';
  }
}

function openTray() {
  els.tray.classList.add("open");
  loadCaptures();
}

function closeTray() {
  els.tray.classList.remove("open");
}

async function generateStrategyExport(exportType = "pine") {
  const name = els.strategyName.value.trim() || "AstraCore Scalp Assist";
  const notes = els.strategyNotes.value.trim();
  els.exportBtns.forEach((button) => {
    button.disabled = true;
  });
  const label = exportType === "mt5" ? "MT5/MQL5 Expert Advisor" : exportType === "instructions" ? "visual trade playbook" : "Pine Script";
  els.pineResult.textContent = `Building ${label} from ${notes ? "typed notes" : "latest capture transcript"}...`;
  try {
    const response = await fetch("/api/strategies/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, notes, export_type: exportType }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Generation failed with ${response.status}`);
    }
    const data = await response.json();
    els.pineResult.innerHTML = `
      <strong>${escapeHtml(data.strategy.title)}</strong><br>
      ${escapeHtml(data.strategy.summary)}<br>
      Source: ${escapeHtml(data.strategy.source)}<br>
      <a href="${data.strategy.download_url}" download>Download ${escapeHtml(data.strategy.filename)}</a>
    `;
  } catch (error) {
    els.pineResult.textContent = error.message || "Could not generate export.";
  } finally {
    els.exportBtns.forEach((button) => {
      button.disabled = false;
    });
  }
}

function renderMonitorStrip() {
  const screens = [{
    label: "This display",
    width: window.screen.width,
    height: window.screen.height,
  }];
  els.monitorStrip.innerHTML = screens.map((screen) => `
    <button class="monitor-chip" type="button">
      <span class="ready-dot"></span>
      <span>${screen.label}</span>
      <small>${screen.width}x${screen.height}</small>
    </button>
  `).join("") + '<button class="monitor-chip" type="button" id="pick-window-btn">Pick window...</button>';
  els.monitorStrip.querySelectorAll(".monitor-chip").forEach((button) => {
    button.addEventListener("click", requestDisplay);
  });
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

function wireEvents() {
  els.connectDisplayBtn.addEventListener("click", requestDisplay);
  els.startSessionBtn.addEventListener("click", startSession);
  els.finishSessionBtn.addEventListener("click", stopSession);
  els.pauseSessionBtn.addEventListener("click", pauseSession);
  els.micBtn.addEventListener("click", toggleMic);
  els.openTrayBtn.addEventListener("click", openTray);
  els.closeTrayBtn.addEventListener("click", closeTray);
  els.exportBtns.forEach((button) => {
    button.addEventListener("click", () => generateStrategyExport(button.dataset.exportType || "pine"));
  });
  els.openStrategyBtn.addEventListener("click", () => {
    els.stage.classList.remove("drawer-collapsed");
    els.strategyDrawer.classList.add("open");
  });
  els.collapseStrategyBtn.addEventListener("click", () => {
    els.stage.classList.add("drawer-collapsed");
    els.strategyDrawer.classList.remove("open");
  });
  window.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r" && !event.shiftKey) {
      event.preventDefault();
      if (state.recording) {
        stopSession();
      } else {
        startSession();
      }
    }
  });
}

setClock();
window.setInterval(setClock, 1000);
renderMonitorStrip();
setMicUi();
setRecordingUi();
wireEvents();
loadCaptures();
