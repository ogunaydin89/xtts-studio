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
  const meterBadge = document.getElementById("meterBadge");
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
  const btnDownloadAudio = document.getElementById("btnDownloadAudio");
  const trackTitle = document.getElementById("trackTitle");
  const trackMeta = document.getElementById("trackMeta");
  const historyList = document.getElementById("historyList");
  const historyCount = document.getElementById("historyCount");

  let isPlaying = false;
  let currentAudioUrl = null;

  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  // Heartbeat loop - informs backend server that UI is active
  function sendHeartbeat() {
    fetch("/api/heartbeat", { method: "POST" }).catch(() => {});
  }
  sendHeartbeat();
  setInterval(sendHeartbeat, 3000);

  // Check Engine Status
  async function checkStatus() {
    try {
      const resp = await fetch("/api/status");
      const data = await resp.json();
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
        setTimeout(checkStatus, 1500);
      } else {
        engineStatus.classList.remove("online");
        engineStatus.classList.add("offline");
        engineStatus.querySelector(".status-text").textContent = data.model_error ? "Engine Error" : "Venv Offline";
        btnSynthesize.disabled = true;
      }
    } catch (e) {
      engineStatus.classList.remove("online");
      engineStatus.classList.add("offline");
      engineStatus.querySelector(".status-text").textContent = "Offline";
    }
  }
  checkStatus();

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
          opt.textContent = v.name.replace(".wav", "").replace(/_/g, " ");
          myGroup.appendChild(opt);
        });
      }

      if (data.builtin_speakers && builtinGroup.childElementCount === 0) {
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
      }
      updatePreviewAvailability();
    } catch (e) {}
  }
  loadVoices();

  function isBuiltinVoice(value) {
    return document.getElementById("builtinVoicesGroup")
      .querySelector(`option[value="${CSS.escape(value)}"]`) !== null;
  }

  function updatePreviewAvailability() {
    const builtin = isBuiltinVoice(voiceSelect.value);
    btnPreviewVoice.disabled = builtin;
    btnPreviewVoice.title = builtin
      ? "Built-in voices have no reference sample to preview — synthesize to hear them"
      : "";
  }
  voiceSelect.addEventListener("change", updatePreviewAvailability);

  async function loadHistory() {
    try {
      const resp = await fetch("/api/history");
      const data = await resp.json();
      historyList.innerHTML = "";
      historyCount.textContent = `${data.count} recordings`;

      if (data.audios && data.audios.length > 0) {
        data.audios.forEach((audio) => {
          const item = document.createElement("div");
          item.className = "history-item" + (currentAudioUrl === audio.url ? " active" : "");
          
          const dateStr = new Date(audio.mtime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
                <span class="item-name">${audio.name}</span>
                <span class="item-date">${dateStr} • ${sizeKb} KB</span>
              </div>
            </div>
            <span class="item-size">▶ Play</span>
          `;

          item.addEventListener("click", () => {
            playTrack(audio.url, audio.name, `Saved file • ${sizeKb} KB`);
          });

          historyList.appendChild(item);
        });
      }
    } catch (e) {}
  }
  loadHistory();

  btnPreviewVoice.addEventListener("click", () => {
    const selectedVoice = voiceSelect.value;
    if (selectedVoice) {
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
    btnDownloadAudio.classList.remove("disabled");
    btnDownloadAudio.href = url;
    btnDownloadAudio.download = title.endsWith(".wav") ? title : title + ".wav";

    audioElement.play().then(() => {
      setPlayState(true);
    }).catch(() => {
      setPlayState(false);
    });

    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
  }

  function setPlayState(playing) {
    isPlaying = playing;
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
    if (!isNaN(audioElement.duration)) {
      const pct = (audioElement.currentTime / audioElement.duration) * 100;
      audioScrubber.value = pct;
      timeCurrent.textContent = formatTime(audioElement.currentTime);
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

  function updateScriptMeter() {
    const text = scriptText.value.trim();
    const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
    const chars = text.length;
    const est = (words / 1.9).toFixed(1);

    wordCount.textContent = `${words} words`;
    charCount.textContent = `${chars} chars`;
    estDuration.textContent = `~${est}s est.`;

    if (words === 0) {
      meterBadge.className = "meter-badge";
      meterBadge.textContent = "Shorts Meter";
    } else if (words >= 16 && words <= 18) {
      meterBadge.className = "meter-badge badge-perfect";
      meterBadge.textContent = "✨ 16–18 Words (Perfect 10s Short!)";
    } else if (words > 18) {
      meterBadge.className = "meter-badge badge-warning";
      meterBadge.textContent = `⚠️ ${words} Words (Exceeds 10s Limit)`;
    } else {
      meterBadge.className = "meter-badge";
      meterBadge.textContent = `${16 - words} words to 16-word target`;
    }
  }

  scriptText.addEventListener("input", updateScriptMeter);
  btnClearText.addEventListener("click", () => {
    scriptText.value = "";
    updateScriptMeter();
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
        alert(`Voice sample "${data.name}" added successfully!`);
      } else {
        alert("Upload error: " + data.error);
      }
    } catch (e) {
      alert("Upload failed: " + e.message);
    }
  }

  btnSynthesize.addEventListener("click", async () => {
    const text = scriptText.value.trim();
    if (!text) {
      scriptText.focus();
      return;
    }

    btnSynthesize.disabled = true;
    btnSynthesizeText.textContent = "Synthesizing Voiceover (CPU)...";

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
        loadHistory();
      } else {
        alert("Synthesis failed: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      alert("Network error: " + e.message);
    } finally {
      btnSynthesize.disabled = false;
      btnSynthesizeText.textContent = "Synthesize Voiceover";
    }
  });

  btnOpenFolder.addEventListener("click", async () => {
    try { await fetch("/api/open_folder", { method: "POST" }); } catch (e) {}
  });

  btnQuit.addEventListener("click", async () => {
    if (confirm("Close XTTS Studio and shut down server?")) {
      try { await fetch("/api/shutdown", { method: "POST" }); } catch (e) {}
      setTimeout(() => { window.close(); }, 500);
    }
  });

  window.addEventListener("beforeunload", () => {
    navigator.sendBeacon("/api/shutdown");
  });
});
