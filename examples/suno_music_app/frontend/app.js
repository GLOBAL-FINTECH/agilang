const $ = (id) => document.getElementById(id);

let mediaRecorder = null;
let recordedChunks = [];
let recordedBlob = null;
let uploadedUrl = "";

function showError(target, error) {
  const message = error?.detail || error?.message || error;
  target.innerHTML = `<p class="error">${escapeHtml(typeof message === "string" ? message : JSON.stringify(message, null, 2))}</p>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fieldValue(id) {
  const el = $(id);
  return el ? el.value.trim() : "";
}

function optionalNumber(id) {
  const value = fieldValue(id);
  return value === "" ? null : Number(value);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function checkHealth() {
  try {
    const health = await requestJson("/api/health");
    $("healthDot").classList.add("ok");
    $("healthText").textContent = health.callbackConfigured ? "Backend ready + callbacks configured" : "Backend ready; polling mode available";
  } catch (error) {
    $("healthDot").classList.remove("ok");
    $("healthText").textContent = "Backend not reachable";
  }
}

function syncWorkflow() {
  const needsUpload = $("sourceMode").value !== "text";
  $("uploadPanel").classList.toggle("hidden", !needsUpload);
}

async function startRecording() {
  recordedChunks = [];
  recordedBlob = null;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordedChunks.push(event.data);
  };
  mediaRecorder.onstop = () => {
    recordedBlob = new Blob(recordedChunks, { type: "audio/webm" });
    const preview = $("recordPreview");
    preview.src = URL.createObjectURL(recordedBlob);
    preview.classList.remove("hidden");
    stream.getTracks().forEach((track) => track.stop());
  };
  mediaRecorder.start();
  $("recordBtn").disabled = true;
  $("stopBtn").disabled = false;
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  $("recordBtn").disabled = false;
  $("stopBtn").disabled = true;
}

async function uploadAudio() {
  const uploadResult = $("uploadResult");
  uploadResult.textContent = "Uploading…";

  if (!$("rightsConfirmed").checked) {
    uploadResult.innerHTML = '<span class="error">Confirm rights permission first.</span>';
    return;
  }

  const fileInput = $("audioFile");
  let file = fileInput.files?.[0];
  if (!file && recordedBlob) {
    file = new File([recordedBlob], `recording-${Date.now()}.webm`, { type: recordedBlob.type || "audio/webm" });
  }
  if (!file) {
    uploadResult.innerHTML = '<span class="error">Choose an audio file or record audio first.</span>';
    return;
  }

  const form = new FormData();
  form.append("file", file);
  form.append("rightsConfirmed", "true");

  try {
    const data = await requestJson("/api/upload", { method: "POST", body: form });
    uploadedUrl = data?.data?.downloadUrl || data?.downloadUrl || "";
    uploadResult.innerHTML = uploadedUrl
      ? `Uploaded: <a href="${escapeHtml(uploadedUrl)}" target="_blank" rel="noopener">temporary audio URL</a>`
      : `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  } catch (error) {
    showError(uploadResult, error);
  }
}

function generationPayload() {
  const sourceMode = fieldValue("sourceMode");
  const payload = {
    sourceMode,
    uploadUrl: sourceMode === "text" ? null : uploadedUrl,
    rightsConfirmed: $("rightsConfirmed").checked,
    customMode: $("customMode").checked,
    instrumental: $("instrumental").checked,
    model: fieldValue("model"),
    title: fieldValue("title"),
    genre: fieldValue("genre"),
    mood: fieldValue("mood") || null,
    prompt: fieldValue("prompt") || null,
    lyrics: fieldValue("lyrics") || null,
    negativeTags: fieldValue("negativeTags") || null,
    vocalGender: fieldValue("vocalGender") || null,
    styleWeight: optionalNumber("styleWeight"),
    weirdnessConstraint: optionalNumber("weirdnessConstraint"),
    audioWeight: optionalNumber("audioWeight"),
  };

  Object.keys(payload).forEach((key) => {
    if (payload[key] === null || payload[key] === "") delete payload[key];
  });
  return payload;
}

async function submitGeneration(event) {
  event.preventDefault();
  const results = $("results");
  results.textContent = "Submitting music generation task…";

  const payload = generationPayload();
  if (payload.sourceMode !== "text" && !payload.uploadUrl) {
    results.innerHTML = '<p class="error">Upload or record audio first, then click “Upload to temporary file API”.</p>';
    return;
  }

  try {
    const data = await requestJson("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const taskId = data?.upstream?.data?.taskId || data?.data?.taskId || "";
    if (taskId) $("taskId").value = taskId;
    renderRaw(results, data, "Generation task created. Poll until SUCCESS.");
  } catch (error) {
    showError(results, error);
  }
}

async function pollGeneration() {
  const taskId = fieldValue("taskId");
  if (!taskId) return;
  const results = $("results");
  results.textContent = "Polling generation status…";
  try {
    const data = await requestJson(`/api/generation/${encodeURIComponent(taskId)}`);
    renderGeneration(data);
  } catch (error) {
    showError(results, error);
  }
}

function renderGeneration(data) {
  const results = $("results");
  const status = data?.data?.status || data?.data?.successFlag || "UNKNOWN";
  const tracks = data?.data?.response?.sunoData || data?.response?.sunoData || [];

  if (!Array.isArray(tracks) || tracks.length === 0) {
    renderRaw(results, data, `Status: ${status}`);
    return;
  }

  const html = tracks.map((track, index) => {
    if (index === 0 && track.id) $("audioId").value = track.id;
    const audio = track.audioUrl || track.audio_url || track.streamAudioUrl || "";
    const stream = track.streamAudioUrl || "";
    const image = track.imageUrl || "";
    return `
      <article class="track">
        <h4>${escapeHtml(track.title || `Track ${index + 1}`)}</h4>
        <p class="mini">Status: ${escapeHtml(status)} · Audio ID: <code>${escapeHtml(track.id || "")}</code></p>
        ${image ? `<img src="${escapeHtml(image)}" alt="cover art" />` : ""}
        ${audio ? `<audio controls src="${escapeHtml(audio)}"></audio>` : ""}
        <p class="mini">${escapeHtml(track.tags || track.modelName || "")}</p>
        <div class="links">
          ${audio ? `<a href="${escapeHtml(audio)}" download target="_blank" rel="noopener">Download MP3</a>` : ""}
          ${stream ? `<a href="${escapeHtml(stream)}" target="_blank" rel="noopener">Stream URL</a>` : ""}
          ${track.id ? `<a href="#" data-audio-id="${escapeHtml(track.id)}">Use audio ID</a>` : ""}
        </div>
      </article>`;
  }).join("");

  results.innerHTML = `<p><strong>Status:</strong> ${escapeHtml(status)}</p>${html}`;
  results.querySelectorAll("[data-audio-id]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      $("audioId").value = link.getAttribute("data-audio-id") || "";
    });
  });
}

async function splitStems() {
  const results = $("stemResults");
  const payload = {
    taskId: fieldValue("taskId"),
    audioId: fieldValue("audioId"),
    type: fieldValue("stemType"),
  };
  if (payload.type === "split_stem_advanced") {
    payload.stemName = fieldValue("stemName");
  }

  results.textContent = "Submitting stem separation…";
  try {
    const data = await requestJson("/api/stems", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const taskId = data?.data?.taskId || "";
    if (taskId) $("stemTaskId").value = taskId;
    renderRaw(results, data, "Stem task created. Poll until SUCCESS.");
  } catch (error) {
    showError(results, error);
  }
}

async function pollStems() {
  const taskId = fieldValue("stemTaskId");
  if (!taskId) return;
  const results = $("stemResults");
  results.textContent = "Polling stem status…";
  try {
    const data = await requestJson(`/api/stems/${encodeURIComponent(taskId)}`);
    renderStemResults(data);
  } catch (error) {
    showError(results, error);
  }
}

function renderStemResults(data) {
  const results = $("stemResults");
  const response = data?.data?.response || {};
  const urls = Object.entries(response)
    .filter(([key, value]) => key.endsWith("Url") && typeof value === "string" && value)
    .map(([key, value]) => `<a href="${escapeHtml(value)}" target="_blank" rel="noopener" download>${escapeHtml(key)}</a>`)
    .join("");

  const originData = Array.isArray(response.originData)
    ? response.originData.map((item) => `
      <article class="track">
        <h4>${escapeHtml(item.stem_type_group_name || "Stem")}</h4>
        <audio controls src="${escapeHtml(item.audio_url)}"></audio>
        <div class="links"><a href="${escapeHtml(item.audio_url)}" download target="_blank" rel="noopener">Download</a></div>
      </article>`).join("")
    : "";

  if (urls || originData) {
    results.innerHTML = `<p><strong>Status:</strong> ${escapeHtml(data?.data?.successFlag || "UNKNOWN")}</p><div class="links">${urls}</div>${originData}`;
  } else {
    renderRaw(results, data, `Status: ${data?.data?.successFlag || "UNKNOWN"}`);
  }
}

async function getTimestampedLyrics() {
  const results = $("stemResults");
  results.textContent = "Requesting timestamped lyrics…";
  try {
    const data = await requestJson("/api/timestamped-lyrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ taskId: fieldValue("taskId"), audioId: fieldValue("audioId") }),
    });
    renderRaw(results, data, "Timestamped lyrics response");
  } catch (error) {
    showError(results, error);
  }
}

async function generateMidi() {
  const results = $("stemResults");
  results.textContent = "Submitting MIDI generation…";
  try {
    const data = await requestJson("/api/midi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ taskId: fieldValue("taskId"), audioId: fieldValue("audioId") }),
    });
    const taskId = data?.data?.taskId || "";
    if (taskId) $("stemTaskId").value = taskId;
    renderRaw(results, data, "MIDI task created.");
  } catch (error) {
    showError(results, error);
  }
}

async function boostStyle() {
  const results = $("results");
  const content = [fieldValue("genre"), fieldValue("mood"), fieldValue("prompt")].filter(Boolean).join(", ");
  if (!content) return;
  results.textContent = "Boosting style prompt…";
  try {
    const data = await requestJson("/api/style/boost", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const boosted = data?.data?.result;
    if (boosted) $("genre").value = boosted;
    renderRaw(results, data, boosted ? "Style boosted and copied into Genre field." : "Style boost response");
  } catch (error) {
    showError(results, error);
  }
}

function renderRaw(target, data, title = "Response") {
  target.innerHTML = `<p><strong>${escapeHtml(title)}</strong></p><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}

$("sourceMode").addEventListener("change", syncWorkflow);
$("recordBtn").addEventListener("click", startRecording);
$("stopBtn").addEventListener("click", stopRecording);
$("uploadBtn").addEventListener("click", uploadAudio);
$("studioForm").addEventListener("submit", submitGeneration);
$("pollBtn").addEventListener("click", pollGeneration);
$("stemBtn").addEventListener("click", splitStems);
$("pollStemBtn").addEventListener("click", pollStems);
$("lyricsBtn").addEventListener("click", getTimestampedLyrics);
$("midiBtn").addEventListener("click", generateMidi);
$("boostStyleBtn").addEventListener("click", boostStyle);

syncWorkflow();
checkHealth();
