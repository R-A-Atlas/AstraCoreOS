(() => {
  const canvas = document.getElementById("liveChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const phase = document.getElementById("liveScenePhase");
  const phaseText = document.getElementById("liveScenePhaseText");
  const priceVal = document.getElementById("livePriceVal");
  const priceDelta = document.getElementById("livePriceDelta");
  const badgeEntry = document.getElementById("badgeEntry");
  const badgeR1 = document.getElementById("badgeR1");
  const badgeR2 = document.getElementById("badgeR2");
  const alertToast = document.getElementById("alertToast");
  const pineLines = document.getElementById("pineLines");
  const voiceBars = Array.from(document.querySelectorAll(".voice-bar"));
  const recLed = document.getElementById("recLed");

  const colors = {
    text: "#f5f6fb",
    muted: "rgba(199, 202, 216, 0.5)",
    brand: "#a78bfa",
    brand2: "#7c3aed",
    record: "#ff4f58",
    good: "#45f28a",
    warn: "#f9ca4d",
  };

  const states = ["WATCHING", "SETUP", "TRIGGER", "FILL_R1", "FILL_R2", "ALERT"];
  const durations = {
    WATCHING: 3200,
    SETUP: 1600,
    TRIGGER: 1200,
    FILL_R1: 1500,
    FILL_R2: 1600,
    ALERT: 1600,
  };

  const candles = [];
  const maxCandles = 22;
  let state = "WATCHING";
  let stateStarted = performance.now();
  let nextCandleIn = 0;
  let lastPrice = 100;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function seed() {
    candles.length = 0;
    let price = 100;
    for (let i = 0; i < maxCandles; i += 1) {
      const open = price;
      const close = open + (Math.random() - 0.46) * 0.6;
      const high = Math.max(open, close) + Math.random() * 0.45;
      const low = Math.min(open, close) - Math.random() * 0.45;
      candles.push({ open, high, low, close });
      price = close;
    }
    lastPrice = price;
  }

  function addCandle() {
    const previous = candles[candles.length - 1];
    const open = previous.close;
    let move = (Math.random() - 0.5) * 0.38;

    if (state === "SETUP") move = -0.25 + Math.random() * 0.12;
    if (state === "TRIGGER") move = 1.05 + Math.random() * 0.35;
    if (state === "FILL_R1") move = 0.35 + Math.random() * 0.34;
    if (state === "FILL_R2") move = 0.18 + Math.random() * 0.28;
    if (state === "ALERT") move = (Math.random() - 0.2) * 0.25;

    const close = open + move + (100 - open) * 0.012;
    const wick = 0.22 + Math.random() * 0.38;
    const high = Math.max(open, close) + wick;
    const low = Math.min(open, close) - wick;
    candles.push({ open, high, low, close });
    while (candles.length > maxCandles) candles.shift();
    lastPrice = close;
  }

  function setState(next) {
    state = next;
    stateStarted = performance.now();

    const labels = {
      WATCHING: "WATCHING",
      SETUP: "PULLBACK",
      TRIGGER: "TRIGGER",
      FILL_R1: "TARGET ONE",
      FILL_R2: "TARGET TWO",
      ALERT: "EXPORT READY",
    };

    if (phaseText) phaseText.textContent = labels[next];
    if (phase) phase.dataset.state = next.toLowerCase();

    if (next === "WATCHING") {
      badgeEntry?.classList.remove("on");
      badgeR1?.classList.remove("on");
      badgeR2?.classList.remove("on");
    }
    if (next === "TRIGGER") badgeEntry?.classList.add("on");
    if (next === "FILL_R1") badgeR1?.classList.add("on");
    if (next === "FILL_R2") badgeR2?.classList.add("on");
    if (next === "ALERT" && alertToast) {
      alertToast.classList.add("on");
      window.setTimeout(() => alertToast.classList.remove("on"), 1200);
    }
  }

  function advanceState(now) {
    if (now - stateStarted < durations[state]) return;
    const index = states.indexOf(state);
    setState(states[(index + 1) % states.length]);
  }

  function draw() {
    const width = canvas.width / dpr;
    const height = canvas.height / dpr;
    ctx.clearRect(0, 0, width, height);

    const lows = candles.map((item) => item.low);
    const highs = candles.map((item) => item.high);
    let min = Math.min(...lows);
    let max = Math.max(...highs);
    const pad = Math.max(0.6, (max - min) * 0.2);
    min -= pad;
    max += pad;
    const span = max - min || 1;
    const xFor = (index) => 18 + (index / (maxCandles - 1)) * (width - 36);
    const yFor = (value) => height - 20 - ((value - min) / span) * (height - 40);
    const bodyWidth = Math.max(4, (width - 36) / maxCandles * 0.55);

    ctx.strokeStyle = "rgba(167, 139, 250, 0.12)";
    ctx.lineWidth = 1;
    for (let i = 1; i < 4; i += 1) {
      const y = (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    const ema = [];
    let lastEma = candles[0].close;
    candles.forEach((item) => {
      lastEma = item.close * 0.26 + lastEma * 0.74;
      ema.push(lastEma);
    });

    ctx.strokeStyle = "rgba(167, 139, 250, 0.66)";
    ctx.lineWidth = 1.4;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ema.forEach((value, index) => {
      const x = xFor(index);
      const y = yFor(value);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    candles.forEach((item, index) => {
      const x = xFor(index);
      const up = item.close >= item.open;
      const hot = index > candles.length - 4 && ["TRIGGER", "FILL_R1", "FILL_R2"].includes(state);
      const color = hot ? colors.text : up ? colors.good : colors.record;
      const top = yFor(Math.max(item.open, item.close));
      const bottom = yFor(Math.min(item.open, item.close));
      const bodyHeight = Math.max(2, bottom - top);

      ctx.strokeStyle = color;
      ctx.lineWidth = hot ? 1.6 : 1;
      ctx.beginPath();
      ctx.moveTo(x, yFor(item.high));
      ctx.lineTo(x, yFor(item.low));
      ctx.stroke();

      if (hot) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 14;
      }
      ctx.fillStyle = color;
      ctx.fillRect(x - bodyWidth / 2, top, bodyWidth, bodyHeight);
      ctx.shadowBlur = 0;
    });

    ctx.strokeStyle = "rgba(255, 255, 255, 0.72)";
    ctx.lineWidth = 1.2;
    ctx.shadowColor = "rgba(167, 139, 250, 0.8)";
    ctx.shadowBlur = 9;
    ctx.beginPath();
    candles.forEach((item, index) => {
      const x = xFor(index);
      const y = yFor(item.close);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.shadowBlur = 0;

    const display = 18840 + (lastPrice - 100) * 4.25;
    const reference = candles[Math.max(0, candles.length - 7)].close;
    const change = Math.max(-1.2, Math.min(1.2, ((lastPrice - reference) / reference) * 100));
    if (priceVal) priceVal.textContent = display.toFixed(2);
    if (priceDelta) {
      priceDelta.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
      priceDelta.dataset.tone = change >= 0 ? "up" : "down";
    }

    positionBadge(badgeEntry, candles.length - 4, "entry");
    positionBadge(badgeR1, candles.length - 3, "target");
    positionBadge(badgeR2, candles.length - 2, "target");
  }

  function positionBadge(element, index, type) {
    if (!element || !element.classList.contains("on")) return;
    const rect = canvas.getBoundingClientRect();
    const parent = canvas.parentElement.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const item = candles[Math.max(0, Math.min(candles.length - 1, index))];
    const low = Math.min(...candles.map((candle) => candle.low));
    const high = Math.max(...candles.map((candle) => candle.high));
    const span = high - low || 1;
    const x = rect.left - parent.left + 18 + (index / (maxCandles - 1)) * (width - 36);
    const y = rect.top - parent.top + height - 20 - ((item.close - low) / span) * (height - 40);
    element.style.left = `${x + (type === "target" ? 18 : -28)}px`;
    element.style.top = `${y - 18}px`;
  }

  const pineSource = [
    "//@version=6",
    "strategy(\"AstraCore capture starter\", overlay=true)",
    "fast = ta.ema(close, 21)",
    "slow = ta.ema(close, 200)",
    "trendUp = close > slow",
    "pullback = low <= fast and close > fast",
    "trigger = trendUp and pullback and close > high[1]",
    "if trigger",
    "    strategy.entry(\"L\", strategy.long)",
    "    alert(\"ASTRACORE LONG {{ticker}}\", alert.freq_once_per_bar_close)",
  ];
  let lineIndex = 0;
  let charIndex = 0;
  let lastType = 0;

  function typePine(now) {
    if (!pineLines || now - lastType < 24) return;
    lastType = now;
    if (lineIndex >= pineSource.length) {
      window.setTimeout(() => {
        lineIndex = 0;
        charIndex = 0;
        pineLines.innerHTML = "";
      }, 900);
      return;
    }

    if (charIndex === 0) {
      const row = document.createElement("div");
      row.className = "pine-line";
      pineLines.appendChild(row);
      while (pineLines.children.length > 7) pineLines.firstChild.remove();
    }

    const line = pineSource[lineIndex];
    charIndex += 1;
    const row = pineLines.lastElementChild;
    row.textContent = line.slice(0, charIndex);
    if (charIndex >= line.length) {
      row.innerHTML = colorize(line);
      lineIndex += 1;
      charIndex = 0;
    }
  }

  function colorize(raw) {
    const escaped = raw.replace(/[&<>]/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
    })[character]);
    return escaped.replace(/(\/\/.*)|("[^"]*")|\b(strategy|ta|if|and|alert|close|low|high|overlay)\b|\b(\d+)\b/g, (match, comment, stringValue, keyword, number) => {
      if (comment) return `<span class="c">${comment}</span>`;
      if (stringValue) return `<span class="s">${stringValue}</span>`;
      if (keyword) return `<span class="k">${keyword}</span>`;
      if (number) return `<span class="n">${number}</span>`;
      return match;
    });
  }

  function animateVoice(now) {
    const t = now / 1000;
    voiceBars.forEach((bar, index) => {
      const value = Math.sin(t * 3.5 + index * 0.6) * 0.5 + 0.5;
      const second = Math.sin(t * 6.2 + index * 0.31) * 0.5 + 0.5;
      const height = 0.35 + (value * second) * 2.35;
      bar.style.height = `${height}rem`;
      bar.style.opacity = `${0.35 + value * 0.55}`;
    });
    if (recLed) recLed.style.opacity = `${0.55 + (Math.sin(now / 260) * 0.5 + 0.5) * 0.45}`;
  }

  function tick(now) {
    nextCandleIn -= 16;
    if (nextCandleIn <= 0) {
      addCandle();
      nextCandleIn = 520;
    }
    advanceState(now);
    draw();
    typePine(now);
    animateVoice(now);
    window.requestAnimationFrame(tick);
  }

  resize();
  seed();
  setState("WATCHING");
  window.addEventListener("resize", resize);
  window.requestAnimationFrame(tick);
})();
