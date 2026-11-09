document.addEventListener("DOMContentLoaded", () => {
  const engineStatus = document.getElementById("engineStatus");
  const voiceSelect = document.getElementById("voiceSelect");
  const btnPreviewVoice = document.getElementById("btnPreviewVoice");
  const dropZone = document.getElementById("dropZone");
  const voiceUploadInput = document.getElementById("voiceUploadInput");
  const languageSelect = document.getElementById("languageSelect");
  const scriptText = document.getElementById("scriptText");
  const btnClearText = document.getElementById("btnClearText");
  const wordCount = document.getElementById("wordCount");
  const charCount = document.getElementById("charCount");
  const estDuration = document.getElementById("estDuration");
  const btnSynthesize = document.getElementById("btnSynthesize");
  const btnSynthesizeText = document.getElementById("btnSynthesizeText");
  const btnOpenFolder = document.getElementById("btnOpenFolder");
  const btnQuit = document.getElementById("btnQuit");

  const audioElement = document.getElementById("audioElement");
  const btnPlayPause = document.getElementById("btnPlayPause");
  const playIcon = document.getElementById("playIcon");
  const pauseIcon = document.getElementById("pauseIcon");
  const audioScrubber = document.getElementById("audioScrubber");
  const timeCurrent = document.getElementById("timeCurrent");
  const timeTotal = document.getElementById("timeTotal");
  const trackTitle = document.getElementById("trackTitle");
  const trackMeta = document.getElementById("trackMeta");
  const historyList = document.getElementById("historyList");
  const historyCount = document.getElementById("historyCount");

  const JSON_POST = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  };

  let isSynthesizing = false;
  let synthTimerInterval = null;
  let synthStartTime = 0;
  let currentAudioUrl = null;

  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  }

  // Heartbeat loop - informs backend server that UI is active
  function sendHeartbeat() {
    fetch("/api/heartbeat", JSON_POST).catch(() => {});
  }
  sendHeartbeat();
  setInterval(sendHeartbeat, 3000);

  // Engine status poller. Respects active synthesis so it never resets the
  // Synthesize button while a job is running.
  async function checkStatus() {
    try {
      const resp = await fetch("/api/status");
      const data = await resp.json();

      if (isSynthesizing || data.synthesizing) {
        engineStatus.classList.remove("offline");
        engineStatus.classList.add("online");
        const sec = isSynthesizing
          ? ((performance.now() - synthStartTime) / 1000).toFixed(1)
          : (data.synth_elapsed || 0).toFixed(1);
        engineStatus.querySelector(".status-text").textContent = `Synthesizing (${sec}s)...`;
        btnSynthesize.disabled = true;
        return;
      }

      if (data.ready && data.model_loaded) {
        engineStatus.classList.remove("offline");
        engineStatus.classList.add("online");
        engineStatus.querySelector(".status-text").textContent = "XTTS-v2 Ready";
        btnSynthesize.disabled = false;
        btnSynthesizeText.textContent = "Synthesize Voiceover";
      } else if (data.ready && data.model_loading) {
        engineStatus.classList.remove("online", "offline");
        engineStatus.querySelector(".status-text").textContent = "Warming Engine...";
        btnSynthesize.disabled = true;
        btnSynthesizeText.textContent = "Warming Engine in RAM...";
      } else {
        engineStatus.classList.remove("online");
        engineStatus.classList.add("offline");
        engineStatus.querySelector(".status-text").textContent = data.model_error ? "Engine Error" : "Venv Offline";
        btnSynthesize.disabled = true;
      }
    } catch (e) {
      if (!isSynthesizing) {
        engineStatus.classList.remove("online");
        engineStatus.classList.add("offline");
        engineStatus.querySelector(".status-text").textContent = "Offline";
      }
    }
  }
  checkStatus();
  setInterval(checkStatus, 3000);

  async function loadVoices() {
    try {
      const resp = await fetch("/api/voices");
      const data = await resp.json();
      const cur = voiceSelect.value;

      const myGroup = document.getElementById("myVoicesGroup");
      const builtinGroup = document.getElementById("builtinVoicesGroup");

      if (data.voices) {
        myGroup.innerHTML = "";
        data.voices.forEach(v => {
          const opt = document.createElement("option");
          opt.value = v.name;
          opt.textContent = v.name
            .replace(/\.(wav|mp3|flac)$/i, "")
            .replace(/_/g, " ");
          myGroup.appendChild(opt);
        });
      }

      if (data.builtin_speakers && builtinGroup.childElementCount <= 1) {
        builtinGroup.innerHTML = "";
        data.builtin_speakers.forEach(name => {
          const opt = document.createElement("option");
          opt.value = name;
          opt.textContent = name;
          builtinGroup.appendChild(opt);
        });
      }

      const allValues = Array.from(voiceSelect.options).map(o => o.value);
      if (allValues.includes(cur)) {
        voiceSelect.value = cur;
      } else if (allValues.includes("Vjollca Johnnie")) {
        voiceSelect.value = "Vjollca Johnnie";
      }
      updateVoiceSelectionState();
    } catch (e) {}
  }
  loadVoices();

  function isBuiltinVoice(value) {
    return document.getElementById("builtinVoicesGroup")
      .querySelector(`option[value="${CSS.escape(value)}"]`) !== null;
  }

  function updateVoiceSelectionState() {
    const val = voiceSelect.value;
    const builtin = isBuiltinVoice(val);
    btnPreviewVoice.disabled = builtin;
    btnPreviewVoice.title = builtin
      ? "Built-in voices have no reference sample to preview — synthesize to hear them"
      : "Listen to the reference voice recording";

    // Auto-pair language when picking a language-tagged voice
    const lower = val.toLowerCase();
    if (lower.includes("_tr.") || lower.endsWith("_tr")) {
      languageSelect.value = "tr";
    } else if (lower.includes("_en.") || lower.endsWith("_en") || builtin) {
      languageSelect.value = "en";
    }
  }
  voiceSelect.addEventListener("change", updateVoiceSelectionState);

  async function loadHistory() {
    try {
      const resp = await fetch("/api/history");
      const data = await resp.json();
      historyList.innerHTML = "";
      historyCount.textContent = `${data.count} recording${data.count === 1 ? "" : "s"}`;

      if (data.audios && data.audios.length > 0) {
        data.audios.forEach((audio) => {
          const item = document.createElement("div");
          item.className = "history-item" + (currentAudioUrl === audio.url ? " active" : "");

          const dateStr = new Date(audio.mtime * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
          const sizeKb = Math.round(audio.size / 1024);

          item.innerHTML = `
            <div class="item-left">
              <span class="item-icon">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                </svg>
              </span>
              <div class="item-info">
                <span class="item-name"></span>
                <span class="item-date"></span>
              </div>
            </div>
            <div class="item-actions">
              <span class="item-size">▶ Play</span>
              <button type="button" class="btn-trash-item" title="Move to Recycle Bin">✕</button>
            </div>
          `;
          item.querySelector(".item-name").textContent = audio.name;
          item.querySelector(".item-date").textContent = `${dateStr} • ${sizeKb} KB`;

          item.addEventListener("click", (ev) => {
            if (ev.target.closest(".btn-trash-item")) return;
            playTrack(audio.url, audio.name, `Saved file • ${sizeKb} KB`);
            document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
            item.classList.add("active");
          });

          const trashBtn = item.querySelector(".btn-trash-item");
          trashBtn.addEventListener("click", async (ev) => {
            ev.stopPropagation();
            try {
              const delResp = await fetch("/api/delete_audio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: audio.name })
              });
              const delData = await delResp.json();
              if (delData.success) {
                loadHistory();
              }
            } catch (err) {}
          });

          historyList.appendChild(item);
        });
      }
    } catch (e) {}
  }
  loadHistory();

  btnPreviewVoice.addEventListener("click", () => {
    const selectedVoice = voiceSelect.value;
    if (selectedVoice && !isBuiltinVoice(selectedVoice)) {
      const previewUrl = `/api/voice_preview/${encodeURIComponent(selectedVoice)}`;
      playTrack(previewUrl, `Speaker Reference: ${selectedVoice}`, "Reference Voice Sample");
    }
  });

  function playTrack(url, title, meta) {
    currentAudioUrl = url;
    trackTitle.textContent = title;
    trackMeta.textContent = meta;

    audioElement.src = url;
    audioElement.load();

    btnPlayPause.disabled = false;
    audioScrubber.disabled = false;

    audioElement.play().then(() => {
      setPlayState(true);
    }).catch(() => {
      setPlayState(false);
    });
  }

  function setPlayState(playing) {
    if (playing) {
      playIcon.classList.add("hidden");
      pauseIcon.classList.remove("hidden");
    } else {
      playIcon.classList.remove("hidden");
      pauseIcon.classList.add("hidden");
    }
  }

  btnPlayPause.addEventListener("click", () => {
    if (audioElement.paused) {
      audioElement.play();
      setPlayState(true);
    } else {
      audioElement.pause();
      setPlayState(false);
    }
  });

  audioElement.addEventListener("timeupdate", () => {
    if (!isNaN(audioElement.duration) && audioElement.duration > 0) {
      const pct = (audioElement.currentTime / audioElement.duration) * 100;
      audioScrubber.value = pct;
      timeCurrent.textContent = formatTime(audioElement.currentTime);
      timeTotal.textContent = formatTime(audioElement.duration);
    }
  });

  audioElement.addEventListener("loadedmetadata", () => {
    if (!isNaN(audioElement.duration)) {
      timeTotal.textContent = formatTime(audioElement.duration);
    }
  });

  audioElement.addEventListener("ended", () => {
    setPlayState(false);
    audioScrubber.value = 0;
  });

  audioScrubber.addEventListener("input", () => {
    if (!isNaN(audioElement.duration)) {
      audioElement.currentTime = (audioScrubber.value / 100) * audioElement.duration;
    }
  });

  function updateScriptStats() {
    const text = scriptText.value.trim();
    const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
    const chars = text.length;
    const est = (words / 2.3).toFixed(1);

    wordCount.textContent = `${words} word${words === 1 ? "" : "s"}`;
    charCount.textContent = `${chars} char${chars === 1 ? "" : "s"}`;
    estDuration.textContent = `~${est}s audio`;
  }

  scriptText.addEventListener("input", updateScriptStats);
  scriptText.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (!btnSynthesize.disabled && !isSynthesizing) {
        btnSynthesize.click();
      }
    }
  });

  btnClearText.addEventListener("click", () => {
    scriptText.value = "";
    updateScriptStats();
    scriptText.focus();
  });

  dropZone.addEventListener("click", () => voiceUploadInput.click());
  voiceUploadInput.addEventListener("change", async () => {
    if (voiceUploadInput.files && voiceUploadInput.files[0]) {
      uploadFile(voiceUploadInput.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--accent-primary)";
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "var(--border-subtle)";
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--border-subtle)";
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file, file.name);

    try {
      const resp = await fetch("/api/upload_voice", {
        method: "POST",
        body: formData
      });
      const data = await resp.json();
      if (data.success) {
        await loadVoices();
        voiceSelect.value = data.name;
        updateVoiceSelectionState();
      } else {
        alert("Upload error: " + data.error);
      }
    } catch (e) {
      alert("Upload failed: " + e.message);
    }
  }

  btnSynthesize.addEventListener("click", async () => {
    if (isSynthesizing) return;
    const text = scriptText.value.trim();
    if (!text) {
      scriptText.focus();
      return;
    }

    isSynthesizing = true;
    synthStartTime = performance.now();
    btnSynthesize.disabled = true;
    btnSynthesizeText.textContent = "Synthesizing... (0.0s)";
    trackTitle.textContent = "Synthesizing Voiceover...";
    trackMeta.textContent = `Voice: ${voiceSelect.selectedOptions[0]?.textContent || voiceSelect.value} (${languageSelect.value.toUpperCase()})`;

    synthTimerInterval = setInterval(() => {
      const sec = ((performance.now() - synthStartTime) / 1000).toFixed(1);
      btnSynthesizeText.textContent = `Synthesizing... (${sec}s)`;
      engineStatus.querySelector(".status-text").textContent = `Synthesizing (${sec}s)...`;
    }, 100);

    const payload = {
      text: text,
      voice: voiceSelect.value,
      language: languageSelect.value
    };

    try {
      const resp = await fetch("/api/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (data.success) {
        playTrack(data.audio_url, data.filename, `Generated in ${data.elapsed}s • Coqui XTTS-v2`);
        await loadHistory();
      } else {
        trackTitle.textContent = "Synthesis Failed";
        trackMeta.textContent = data.error || "Unknown error";
        alert("Synthesis failed: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      trackTitle.textContent = "Network Error";
      trackMeta.textContent = e.message;
      alert("Network error: " + e.message);
    } finally {
      clearInterval(synthTimerInterval);
      synthTimerInterval = null;
      isSynthesizing = false;
      btnSynthesize.disabled = false;
      btnSynthesizeText.textContent = "Synthesize Voiceover";
      engineStatus.querySelector(".status-text").textContent = "XTTS-v2 Ready";
    }
  });

  btnOpenFolder.addEventListener("click", async () => {
    try { await fetch("/api/open_folder", JSON_POST); } catch (e) {}
  });

  btnQuit.addEventListener("click", async () => {
    try { await fetch("/api/shutdown", JSON_POST); } catch (e) {}
    window.close();
  });
});
