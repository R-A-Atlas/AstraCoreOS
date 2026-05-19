const chatHistory = document.getElementById("chat-history");
const input = document.getElementById("directive-input");
const sendBtn = document.getElementById("send-btn");
const displayArea = document.getElementById("active-display-area");
const activitySteps = document.getElementById("activity-steps");
const providerStatus = document.getElementById("provider-status");
const memoryBtn = document.getElementById("memory-btn");
const commandCenterBtn = document.getElementById("command-center-btn");
const captureBtn = document.getElementById("capture-btn");
const deepResearchToggle = document.getElementById("deep-research-toggle");
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
setInterval(tickClock, 1000);
tickClock();

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `
    <div class="msg-name">${role === "user" ? "You" : "AstraCore"}</div>
    <div class="msg-bubble">${escapeHtml(text)}</div>
  `;
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function renderSteps(steps) {
  activitySteps.innerHTML = "";
  for (const step of steps || []) {
    const div = document.createElement("div");
    div.className = "step";
    div.textContent = `${step.label}: ${step.detail}`;
    activitySteps.appendChild(div);
  }
}

function renderArtifacts(artifacts) {
  for (const artifact of artifacts || []) {
    const card = document.createElement("div");
    card.className = "artifact-card";
    card.innerHTML = `
      <div class="artifact-kind">${escapeHtml(artifact.kind || "artifact")}</div>
      <div class="artifact-title">${escapeHtml(artifact.title || "Untitled")}</div>
      <div class="artifact-summary">${escapeHtml(artifact.summary || "")}</div>
      <div class="artifact-path">${escapeHtml(artifact.path || "")}</div>
      ${artifact.download_url ? `<a class="download-btn" href="${escapeHtml(artifact.download_url)}" download>Download ${escapeHtml((artifact.kind || "file").toUpperCase())}</a>` : `<div class="artifact-summary">No downloadable file was created for this output.</div>`}
    `;
    displayArea.prepend(card);
  }
}

function renderContextPackets(contextPackets) {
  for (const packet of contextPackets || []) {
    const data = packet.data || {};
    const card = document.createElement("div");
    card.className = "packet-card";
    const sections = (data.recommended_sections || []).slice(0, 8);
    const sources = packet.sources || [];
    const warnings = packet.warnings || [];
    card.innerHTML = `
      <div class="packet-head">
        <div>
          <div class="packet-kind">Source Packet</div>
          <div class="artifact-title">${escapeHtml(packet.agent || "agent")}</div>
        </div>
        <div class="confidence">${Math.round(Number(packet.confidence || 0) * 100)}%</div>
      </div>
      <div class="artifact-summary">${escapeHtml(packet.summary || "")}</div>
      <div class="packet-meta">
        <span>${escapeHtml(data.document_type || "task")}</span>
        <span>${escapeHtml(data.business || "topic")}</span>
        <span>${escapeHtml(data.format || "chat")}</span>
      </div>
      ${sections.length ? `<div class="packet-list"><b>Sections</b>${sections.map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
      ${sources.length ? `<div class="packet-list"><b>Sources</b>${sources.map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
      ${warnings.length ? `<div class="packet-warnings">${warnings.map(item => `<div>${escapeHtml(item)}</div>`).join("")}</div>` : ""}
    `;
    displayArea.prepend(card);
  }
}

function renderMemory(items) {
  const card = document.createElement("div");
  card.className = "memory-card";
  const rows = (items || []).slice().reverse();
  card.innerHTML = `
    <div class="packet-kind">Memory</div>
    <div class="artifact-title">Recent Agent Runs</div>
    ${
      rows.length
        ? rows.map(item => {
            const packets = item.context_packets || [];
            const agentNames = packets.map(packet => packet.agent).filter(Boolean).join(", ");
            return `
              <div class="memory-row">
                <div class="memory-directive">${escapeHtml(item.directive || "No directive")}</div>
                <div class="artifact-summary">${escapeHtml((item.memory || []).join(" "))}</div>
                ${agentNames ? `<div class="artifact-path">agents: ${escapeHtml(agentNames)}</div>` : ""}
                ${item.artifact_path ? `<div class="artifact-path">${escapeHtml(item.artifact_path)}</div>` : ""}
              </div>
            `;
          }).join("")
        : `<div class="artifact-summary">No memory has been written yet.</div>`
    }
  `;
  displayArea.prepend(card);
}

function renderCaptureStudio(captures = []) {
  const card = document.createElement("div");
  card.className = "command-center-card";
  card.innerHTML = `
    <div class="packet-kind">Trade Capture Studio</div>
    <div class="artifact-title">Record screen + voice</div>
    <div class="artifact-summary">
      Explain your chart, entry model, invalidation, and trade management out loud while AstraCore records the screen.
      The saved session becomes the source material for strategy extraction.
    </div>
    <div class="capture-actions">
      <button class="download-btn" id="start-capture-btn" type="button">Start Capture</button>
      <button class="inline-action" id="stop-capture-btn" type="button" disabled>Stop</button>
      <span id="capture-state" class="artifact-path">idle</span>
    </div>
    <video id="capture-preview" class="capture-preview" controls muted></video>
    <div class="packet-list">
      <b>Recent captures</b>
      ${
        captures.length
          ? captures.map(item => `<span>${escapeHtml(item.filename)} · ${Math.round(Number(item.size_bytes || 0) / 1024)} KB · ${escapeHtml(item.transcript_status || "pending")}</span>`).join("")
          : "<span>No capture sessions saved yet.</span>"
      }
    </div>
  `;
  displayArea.prepend(card);
  card.querySelector("#start-capture-btn").addEventListener("click", () => startCapture(card));
  card.querySelector("#stop-capture-btn").addEventListener("click", () => stopCapture(card));
}

async function loadCaptureStudio() {
  renderSteps([{ label: "Capture studio", detail: "Loading recent capture sessions." }]);
  try {
    const response = await fetch("/api/captures?limit=8");
    const data = await response.json();
    renderCaptureStudio(data.captures || []);
    renderSteps([{ label: "Capture studio loaded", detail: "Screen and microphone recording is available from the browser." }]);
  } catch (error) {
    renderSteps([{ label: "Capture studio error", detail: error.message || "Failed to load capture studio." }]);
  }
}

async function startCapture(card) {
  const state = card.querySelector("#capture-state");
  const startBtn = card.querySelector("#start-capture-btn");
  const stopBtn = card.querySelector("#stop-capture-btn");
  const preview = card.querySelector("#capture-preview");
  try {
    state.textContent = "requesting screen and microphone permission";
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
    captureRecorder.onstop = () => uploadCapture(card);
    captureRecorder.start(1000);
    preview.srcObject = captureStream;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    state.textContent = "recording";
    renderSteps([{ label: "Capture started", detail: "Explain your trading process out loud while showing the chart." }]);
  } catch (error) {
    state.textContent = `capture blocked: ${error.message || error}`;
    renderSteps([{ label: "Capture blocked", detail: "Browser permission was denied or screen capture is unavailable." }]);
  }
}

function stopCapture(card) {
  const state = card.querySelector("#capture-state");
  if (captureRecorder && captureRecorder.state !== "inactive") {
    state.textContent = "saving";
    captureRecorder.stop();
  }
  if (captureStream) {
    captureStream.getTracks().forEach(track => track.stop());
  }
}

async function uploadCapture(card) {
  const state = card.querySelector("#capture-state");
  const startBtn = card.querySelector("#start-capture-btn");
  const stopBtn = card.querySelector("#stop-capture-btn");
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
    state.innerHTML = `saved · <a href="${escapeHtml(data.capture.download_url)}" download>download</a>`;
    renderSteps([{ label: "Capture saved", detail: data.capture.filename }]);
  } catch (error) {
    state.textContent = `save failed: ${error.message || error}`;
    renderSteps([{ label: "Capture save failed", detail: error.message || "Upload failed." }]);
  } finally {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    captureRecorder = null;
    captureStream = null;
    captureChunks = [];
  }
}

function renderCommandCenter(state) {
  const card = document.createElement("div");
  card.className = "command-center-card";
  const prep = state.market_prep || {};
  const watchlist = state.watchlist || [];
  const tradePlans = state.trade_plans || [];
  const journal = state.journal || [];
  const tasks = state.agent_tasks || [];
  const intelTasks = state.intel_tasks || [];
  const notificationChannels = state.notification_channels || [];
  const integrations = state.integrations || [];
  const tradingViewAlerts = state.tradingview_alerts || [];
  const notes = state.workflow_notes || [];
  card.innerHTML = `
    <div class="packet-kind">Command Center</div>
    <div class="artifact-title">${escapeHtml(state.title || "AstraCore Trading Command Center")}</div>
    <div class="packet-meta">
      <span>${escapeHtml(state.session_date || "today")}</span>
      <span>trading focused</span>
      <span>live data pending</span>
    </div>
    <div class="command-grid">
      <section>
        <b>Market Prep</b>
        <p>Bias: ${escapeHtml(prep.bias || "unset")}</p>
        <p>Risk: ${escapeHtml(prep.risk_mode || "unset")}</p>
        <p>News: ${escapeHtml(prep.news || "pending")}</p>
      </section>
      <section>
        <b>Watchlist</b>
        ${watchlist.map(item => `<p>${escapeHtml(item.symbol)} · ${escapeHtml(item.status)} · ${escapeHtml(item.note)}</p>`).join("") || "<p>No symbols yet.</p>"}
      </section>
      <section>
        <b>Trade Plans</b>
        ${tradePlans.length ? tradePlans.map(item => `<p>${escapeHtml(item.symbol)} · ${escapeHtml(item.status)}</p>`).join("") : "<p>No saved trade plans yet.</p>"}
      </section>
      <section>
        <b>Journal</b>
        ${journal.length ? journal.map(item => `<p>${escapeHtml(item.symbol)} · ${escapeHtml(item.result)}</p>`).join("") : "<p>No journal entries yet.</p>"}
      </section>
      <section>
        <b>Agent Work</b>
        ${tasks.map(task => `<p>${escapeHtml(task.owner)} · ${escapeHtml(task.status)} · ${escapeHtml(task.task)}</p>`).join("")}
      </section>
      <section>
        <b>Intel Skills</b>
        ${intelTasks.map(task => `
          <p>
            <span class="skill-status ${escapeHtml(task.status)}">${escapeHtml(task.status)}</span>
            ${escapeHtml(task.title)} · ${escapeHtml(task.cadence)}
            <button class="inline-action run-skill-btn" data-skill-id="${escapeHtml(task.skill_id)}" type="button">Run</button>
          </p>
        `).join("") || "<p>No intel skills registered.</p>"}
      </section>
      <section>
        <b>Update Channels</b>
        ${notificationChannels.map(channel => `
          <p>
            <span class="skill-status ${channel.configured ? "configured" : "off"}">${escapeHtml(channel.status)}</span>
            ${escapeHtml(channel.title)}
          </p>
        `).join("") || "<p>No update channels configured.</p>"}
      </section>
      <section>
        <b>Integrations</b>
        ${integrations.map(item => `
          <p>
            <span class="skill-status ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span>
            ${escapeHtml(item.title)} · ${escapeHtml(item.local_url)}
          </p>
        `).join("") || "<p>No integrations registered.</p>"}
      </section>
      <section>
        <b>TradingView Alerts</b>
        ${tradingViewAlerts.map(alert => `
          <p>
            <span class="skill-status ready">${escapeHtml(alert.action || "alert")}</span>
            ${escapeHtml(alert.symbol || "UNKNOWN")} · ${escapeHtml(alert.timeframe || "")} · ${escapeHtml(alert.price || "")}
          </p>
        `).join("") || "<p>No TradingView alerts received yet.</p>"}
      </section>
      <section>
        <b>Workflow Rules</b>
        ${notes.map(note => `<p>${escapeHtml(note)}</p>`).join("")}
      </section>
    </div>
  `;
  displayArea.prepend(card);
}

async function loadCommandCenter() {
  renderSteps([{ label: "Command center", detail: "Loading trading workspace." }]);
  try {
    const response = await fetch("/api/command-center");
    const data = await response.json();
    renderCommandCenter(data.state || {});
    renderSteps([{ label: "Command center loaded", detail: "Market prep, watchlist, journal, and agent task lanes are visible." }]);
  } catch (error) {
    renderSteps([{ label: "Command center error", detail: error.message || "Failed to load command center." }]);
  }
}

async function runIntelSkill(skillId) {
  renderSteps([{ label: "Intel skill", detail: `Running ${skillId}.` }]);
  try {
    const response = await fetch("/api/intel/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill_id: skillId, directive: input.value.trim() })
    });
    const data = await response.json();
    if (data.packet) renderContextPackets([data.packet]);
    renderSteps([
      { label: "Intel skill complete", detail: data.message || "Skill packet created." },
      { label: "Missing tools", detail: (data.missing_tools || []).join(", ") || "none" }
    ]);
  } catch (error) {
    renderSteps([{ label: "Intel skill error", detail: error.message || "Failed to run skill." }]);
  }
}

async function loadMemory() {
  renderSteps([{ label: "Memory", detail: "Loading recent local memory." }]);
  try {
    const response = await fetch("/api/memory?limit=8");
    const data = await response.json();
    renderMemory(data.items || []);
    renderSteps([{ label: "Memory loaded", detail: `${(data.items || []).length} records found.` }]);
  } catch (error) {
    renderSteps([{ label: "Memory error", detail: error.message || "Failed to load memory." }]);
  }
}

function renderConfigStatus(status) {
  const providers = status.providers || [];
  const card = document.createElement("div");
  card.className = "memory-card";
  card.innerHTML = `
    <div class="packet-kind">Config Status</div>
    <div class="artifact-title">${escapeHtml(status.project || "AstraCoreOS")}</div>
    <div class="packet-meta">
      <span>${escapeHtml(status.active_provider || "local")}</span>
      <span>${status.paid_models_enabled ? "paid on" : "paid off"}</span>
      <span>${escapeHtml(status.environment || "development")}</span>
    </div>
    <div class="packet-list">
      <b>Providers</b>
      ${providers.map(provider => `<span>${escapeHtml(provider.provider)}: ${provider.configured ? "configured" : "missing key"} / ${escapeHtml(provider.default_model)}</span>`).join("")}
    </div>
    <div class="packet-list">
      <b>Services</b>
      <span>supabase: ${status.supabase_configured ? "configured" : "missing"}</span>
      <span>google oauth: ${status.google_oauth_configured ? "configured" : "missing"}</span>
      <span>github token: ${status.github_token_configured ? "configured" : "not needed"}</span>
      <span>email: ${status.email_configured ? "configured" : "off"}</span>
    </div>
  `;
  displayArea.prepend(card);
}

async function loadConfigStatus() {
  try {
    const response = await fetch("/api/config/status");
    const data = await response.json();
    renderConfigStatus(data.status || {});
    if (data.status) {
      providerStatus.textContent = `model: ${data.status.active_provider} / paid ${data.status.paid_models_enabled ? "on" : "off"}`;
    }
  } catch {
    providerStatus.textContent = "model: config unavailable";
  }
}

async function sendDirective() {
  const directive = input.value.trim();
  if (!directive) return;

  appendMessage("user", directive);
  input.value = "";
  sendBtn.disabled = true;
  const deepResearch = Boolean(deepResearchToggle && deepResearchToggle.checked);
  renderSteps([{ label: "Thinking", detail: deepResearch ? "Deep research requested. Routing directive." : "Routing directive through automatic tier selection." }]);
  burstNetwork();

  try {
    const started = Date.now();
    const response = await fetch("/api/operator", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directive, deep_research: deepResearch })
    });
    const data = await response.json();
    const elapsed = Date.now() - started;
    if (elapsed < 550) await new Promise(resolve => setTimeout(resolve, 550 - elapsed));

    appendMessage("agent", data.message || "Done.");
    renderSteps(data.steps || []);
    renderContextPackets(data.context_packets || []);
    renderArtifacts(data.artifacts || []);
    if (data.model) {
      providerStatus.textContent = `model: ${data.model.provider}/${data.model.model}`;
    }
  } catch (error) {
    appendMessage("agent", `Request failed: ${error.message || error}`);
    renderSteps([{ label: "Error", detail: "Backend request failed." }]);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

sendBtn.addEventListener("click", sendDirective);
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendDirective();
  }
});
document.getElementById("clear-visor").addEventListener("click", () => {
  displayArea.innerHTML = "";
  renderSteps([{ label: "Cleared", detail: "Primary visor is empty." }]);
});
memoryBtn.addEventListener("click", loadMemory);
commandCenterBtn.addEventListener("click", loadCommandCenter);
captureBtn.addEventListener("click", loadCaptureStudio);
displayArea.addEventListener("click", event => {
  const button = event.target.closest(".run-skill-btn");
  if (!button) return;
  runIntelSkill(button.dataset.skillId);
});
loadCommandCenter();
loadConfigStatus();

const canvas = document.getElementById("orbitalBrainCanvas");
const ctx = canvas.getContext("2d");
let width = 0;
let height = 0;
let activityBurst = 0;
const nodes = [];
const edges = [];
let packets = [];

function resizeCanvas() {
  width = canvas.width = canvas.parentElement.offsetWidth;
  height = canvas.height = canvas.parentElement.offsetHeight;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

for (let ring = 1; ring <= 4; ring++) {
  const radius = ring * 86;
  const count = ring * 6;
  for (let i = 0; i < count; i++) {
    nodes.push({
      ring,
      radius,
      angle: (Math.PI * 2 / count) * i,
      baseAngle: (Math.PI * 2 / count) * i,
      spinSpeed: (0.001 / ring) * (ring % 2 === 0 ? 1 : -1)
    });
  }
}
const core = { ring: 0, radius: 0, angle: 0, x: 0, y: 0 };
nodes.filter(n => n.ring === 1).forEach(n => edges.push({ source: core, target: n }));
nodes.forEach(n => {
  if (n.ring < 4) {
    const outer = nodes.filter(o => o.ring === n.ring + 1);
    outer.sort((a, b) => Math.abs(a.baseAngle - n.baseAngle) - Math.abs(b.baseAngle - n.baseAngle));
    edges.push({ source: n, target: outer[0] });
  }
});

function burstNetwork() {
  activityBurst = 1;
}

function animate() {
  ctx.clearRect(0, 0, width, height);
  const cx = width / 2;
  const cy = height / 2;
  activityBurst = Math.max(0, activityBurst - 0.01);
  const multiplier = 1 + activityBurst * 4;

  core.x = cx;
  core.y = cy;
  for (const node of nodes) {
    node.angle += node.spinSpeed * multiplier;
    node.x = cx + Math.cos(node.angle) * node.radius;
    node.y = cy + Math.sin(node.angle) * node.radius;
  }

  for (const edge of edges) {
    ctx.beginPath();
    ctx.moveTo(edge.source.x, edge.source.y);
    ctx.lineTo(edge.target.x, edge.target.y);
    ctx.strokeStyle = `rgba(251, 191, 36, ${0.045 + activityBurst * 0.16})`;
    ctx.lineWidth = 1 + activityBurst;
    ctx.stroke();
  }

  if (Math.random() < 0.08 + activityBurst * 0.42) {
    const edge = edges[Math.floor(Math.random() * Math.min(edges.length, 12))];
    packets.push({ edge, progress: 0, speed: 0.012 + Math.random() * 0.026 + activityBurst * 0.02 });
  }

  packets = packets.filter(packet => {
    packet.progress += packet.speed;
    const p = Math.min(packet.progress, 1);
    const x = packet.edge.source.x + (packet.edge.target.x - packet.edge.source.x) * p;
    const y = packet.edge.source.y + (packet.edge.target.y - packet.edge.source.y) * p;
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fillStyle = "#fff7cc";
    ctx.shadowColor = "#fbbf24";
    ctx.shadowBlur = 14 + activityBurst * 18;
    ctx.fill();
    ctx.shadowBlur = 0;
    return packet.progress < 1;
  });

  for (const node of nodes) {
    ctx.beginPath();
    ctx.arc(node.x, node.y, 1.4 + activityBurst, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(251, 191, 36, ${0.35 + activityBurst * 0.55})`;
    ctx.fill();
  }

  ctx.beginPath();
  ctx.arc(cx, cy, 10 + activityBurst * 5, 0, Math.PI * 2);
  ctx.fillStyle = "#050505";
  ctx.strokeStyle = "#fbbf24";
  ctx.lineWidth = 2 + activityBurst * 2;
  ctx.shadowColor = "#fbbf24";
  ctx.shadowBlur = 22 + activityBurst * 32;
  ctx.fill();
  ctx.stroke();
  ctx.shadowBlur = 0;

  requestAnimationFrame(animate);
}
animate();
