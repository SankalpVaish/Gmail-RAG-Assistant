const els = {
  statusChips: document.getElementById("statusChips"),
  themeToggle: document.getElementById("themeToggle"),
  userSelect: document.getElementById("userSelect"),
  userStat: document.getElementById("userStat"),
  loadDemoBtn: document.getElementById("loadDemoBtn"),
  viewDemoBtn: document.getElementById("viewDemoBtn"),
  ingestGmailBtn: document.getElementById("ingestGmailBtn"),
  gmailHint: document.getElementById("gmailHint"),
  maxResults: document.getElementById("maxResults"),
  jobStatus: document.getElementById("jobStatus"),
  isolationBtn: document.getElementById("isolationBtn"),
  isolationResult: document.getElementById("isolationResult"),
  messages: document.getElementById("messages"),
  emptyState: document.getElementById("emptyState"),
  suggestions: document.getElementById("suggestions"),
  composer: document.getElementById("composer"),
  questionInput: document.getElementById("questionInput"),
  sendBtn: document.getElementById("sendBtn"),
  activeUserLabel: document.getElementById("activeUserLabel"),
  activeUserMeta: document.getElementById("activeUserMeta"),
  headAvatar: document.getElementById("headAvatar"),
  modelLabel: document.getElementById("modelLabel"),
  demoModal: document.getElementById("demoModal"),
  demoModalOverlay: document.getElementById("demoModalOverlay"),
  demoModalClose: document.getElementById("demoModalClose"),
  demoModalBody: document.getElementById("demoModalBody"),
};

const state = {
  users: [],
  userStats: {},
  ollama: null,
  busy: false,
  staticMode: false,  // Auto-detected: true when backend unavailable
  staticData: null,   // Loaded fake_emails.json for client-side demo
};

const SUGGESTIONS = [
  "How much is the API budget?",
  "When does benefit enrollment close?",
  "When is the product launch?",
  "Summarise my recent emails",
];

// ---------------------------------------------------------------- static mode detection

async function detectBackendMode() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

async function loadStaticData() {
  const response = await fetch("fake_emails.json");
  const emails = await response.json();
  state.staticData = emails;

  // Build user stats from emails
  const byUser = {};
  for (const email of emails) {
    if (!byUser[email.user_id]) byUser[email.user_id] = [];
    byUser[email.user_id].push(email);
  }

  state.users = Object.keys(byUser).sort();
  state.userStats = {};
  for (const user of state.users) {
    state.userStats[user] = {
      chunks: byUser[user].length,
      documents: byUser[user].length,
    };
  }

  return { loaded: true, total: emails.length, users: state.users.length };
}

function enableStaticMode() {
  state.staticMode = true;
  document.getElementById("demoBanner").style.display = "flex";
  els.modelLabel.textContent = "llama3 (simulated)";
  els.ingestGmailBtn.disabled = true;
  els.gmailHint.textContent = "Not available in static demo mode.";
}

// Mock streaming: split answer into tokens and yield with delays
async function* mockStream(answer) {
  const words = answer.split(" ");
  for (let i = 0; i < words.length; i++) {
    await new Promise((resolve) => setTimeout(resolve, 50 + Math.random() * 100));
    yield words[i] + (i < words.length - 1 ? " " : "");
  }
}

// Simple keyword-based "retrieval" from static data
function staticRetrieve(question, userId) {
  if (!state.staticData) return { documents: [], sources: [] };

  const userEmails = state.staticData.filter((e) => e.user_id === userId);
  const lowerQ = question.toLowerCase();

  // Score emails by keyword overlap
  const scored = userEmails.map((email) => {
    const text = `${email.subject} ${email.body}`.toLowerCase();
    const words = lowerQ.split(/\s+/).filter((w) => w.length > 3);
    let score = 0;
    for (const word of words) {
      if (text.includes(word)) score += 1;
    }
    return { email, score };
  });

  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, 3).filter((s) => s.score > 0);

  return {
    documents: top.map((s) => s.email.body),
    sources: top.map((s) => ({
      subject: s.email.subject,
      from: s.email.sender,
      date: s.email.timestamp,
      user_id: s.email.user_id,
      excerpt: s.email.body.substring(0, 200) + "...",
      score: (s.score / 5).toFixed(2),
    })),
  };
}

// Hardcoded answers for common demo questions
const MOCK_ANSWERS = {
  "api budget": "The API integration project has been allocated $50,000 for Q4.",
  "benefit enrollment": "The health insurance enrollment window closes on Friday, October 20th at 5 PM EST. You can choose between the PPO plan ($250/month) or the HMO plan ($180/month).",
  "product launch": "The new product launch is scheduled for December 12th, 2025.",
  "stripe payout": "Your Stripe payout of $12,847.50 is on the way, scheduled to arrive by October 24, 2025.",
  "flight": "Your United Airlines flight UA 1847 departs San Francisco (SFO) on November 15, 2025 at 6:45 AM, arriving in Austin (AUS) at 12:10 PM CST.",
  "default": "Based on the retrieved emails, I can provide information about budgets, benefit enrollment, product launches, payments, and travel arrangements. The answer depends on the specific emails available for this user.",
};

// ---------------------------------------------------------------- theme

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("theme", theme);
}

applyTheme(
  localStorage.getItem("theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
);

els.themeToggle.addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

// ---------------------------------------------------------------- utilities

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

/** Minimal, escape-first renderer for the small subset of markdown LLMs emit. */
function renderMarkdown(text) {
  const inline = (line) =>
    escapeHtml(line)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  return text
    .trim()
    .split(/\n{2,}/)
    .map((block) => {
      const lines = block.split("\n").filter((l) => l.trim());
      const bulleted = lines.every((l) => /^\s*[-*•]\s+/.test(l));
      const numbered = lines.length > 0 && lines.every((l) => /^\s*\d+[.)]\s+/.test(l));

      if (bulleted && lines.length) {
        return `<ul>${lines.map((l) => `<li>${inline(l.replace(/^\s*[-*•]\s+/, ""))}</li>`).join("")}</ul>`;
      }
      if (numbered) {
        return `<ol>${lines.map((l) => `<li>${inline(l.replace(/^\s*\d+[.)]\s+/, ""))}</li>`).join("")}</ol>`;
      }
      return `<p>${lines.map(inline).join("<br />")}</p>`;
    })
    .join("");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(data.detail || response.statusText);
  return data;
}

function scrollToBottom() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function initial(value) {
  return (value || "?").trim().charAt(0).toUpperCase() || "?";
}

function setJobStatus(message, kind = "busy") {
  if (!message) {
    els.jobStatus.innerHTML = "";
    return;
  }
  const spinner = kind === "busy" ? `<span class="spinner"></span>` : "";
  els.jobStatus.className = `job-status${kind === "busy" ? "" : ` ${kind}`}`;
  els.jobStatus.innerHTML = `${spinner}<span>${escapeHtml(message)}</span>`;
}

// ---------------------------------------------------------------- status

function chip(kind, html) {
  return `<span class="chip ${kind}"><span class="dot"></span>${html}</span>`;
}

async function refreshStatus() {
  // Check if backend is available
  const backendAvailable = await detectBackendMode();

  if (!backendAvailable && !state.staticMode) {
    enableStaticMode();
    await loadStaticData();
  }

  // Static mode: show mock status
  if (state.staticMode) {
    const chips = [
      chip("ok", "Static demo"),
      state.users.length > 0
        ? chip("", `${state.staticData.length} emails · ${state.users.length} users`)
        : chip("warn", "No data loaded"),
    ];
    els.statusChips.innerHTML = chips.join("");
    renderUsers();
    return;
  }

  // Backend mode: fetch real status
  let status;
  try {
    status = await api("/api/status");
  } catch (err) {
    els.statusChips.innerHTML = chip("bad", "Backend unreachable");
    return;
  }

  state.users = status.users;
  state.userStats = status.user_stats;
  state.ollama = status.ollama;

  const { ollama } = status;
  const chips = [];

  if (!ollama.available) {
    chips.push(chip("bad", "Ollama offline"));
  } else if (!ollama.model_pulled) {
    chips.push(chip("warn", `Pull <code>${escapeHtml(ollama.model)}</code>`));
  } else {
    chips.push(chip("ok", "Ollama ready"));
  }

  chips.push(
    status.total_chunks > 0
      ? chip("", `${status.total_chunks} chunks · ${status.users.length} user${status.users.length === 1 ? "" : "s"}`)
      : chip("warn", "No data indexed")
  );

  chips.push(status.gmail_credentials_present ? chip("", "Gmail linked") : chip("", "Demo mode"));

  els.statusChips.innerHTML = chips.join("");
  els.modelLabel.textContent = ollama.available ? ollama.model : "";

  els.ingestGmailBtn.disabled = !status.gmail_credentials_present;
  els.gmailHint.innerHTML = status.gmail_credentials_present
    ? "Opens an OAuth window on this machine."
    : "Add <code>credentials.json</code> to the project folder to enable this.";

  renderUsers();
}

function renderUsers() {
  const previous = els.userSelect.value;

  if (state.users.length === 0) {
    els.userSelect.innerHTML = `<option value="">No data indexed</option>`;
    els.userSelect.disabled = true;
    els.userStat.textContent = "";
    els.isolationBtn.disabled = true;
    els.activeUserLabel.textContent = "No user selected";
    els.activeUserMeta.textContent = "Load the demo dataset to begin";
    els.headAvatar.textContent = "?";
    return;
  }

  els.userSelect.disabled = false;
  els.userSelect.innerHTML = state.users
    .map((user) => `<option value="${escapeHtml(user)}">${escapeHtml(user)}</option>`)
    .join("");

  if (state.users.includes(previous)) els.userSelect.value = previous;
  els.isolationBtn.disabled = state.users.length < 2;
  updateActiveUser();
  renderSuggestions();
}

function updateActiveUser() {
  const user = els.userSelect.value;
  const stats = state.userStats[user];
  const summary = stats
    ? `${stats.documents} document${stats.documents === 1 ? "" : "s"} · ${stats.chunks} chunk${stats.chunks === 1 ? "" : "s"}`
    : "";

  els.userStat.textContent = summary ? `${summary} indexed` : "";
  els.activeUserLabel.textContent = user;
  els.activeUserMeta.textContent = summary || "No data for this user";
  els.headAvatar.textContent = initial(user);
}

function renderSuggestions() {
  if (!els.suggestions.isConnected) return;
  els.suggestions.innerHTML = SUGGESTIONS.map(
    (text) => `<button type="button" class="suggestion">${escapeHtml(text)}</button>`
  ).join("");
  els.suggestions.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
      els.questionInput.value = button.textContent;
      els.composer.requestSubmit();
    });
  });
}

// ---------------------------------------------------------------- chat

function addMessage(role) {
  els.emptyState?.remove();

  const wrapper = document.createElement("div");
  wrapper.className = `msg ${role}`;

  const isUser = role === "user";
  const avatar = isUser
    ? `<span class="avatar avatar-user">${escapeHtml(initial(els.userSelect.value))}</span>`
    : `<span class="avatar avatar-assistant"><svg viewBox="0 0 24 24"><use href="#i-spark" /></svg></span>`;

  wrapper.innerHTML = `
    ${avatar}
    <div class="msg-main">
      <div class="msg-author">${isUser ? escapeHtml(els.userSelect.value || "You") : "Assistant"}</div>
      <div class="msg-body"></div>
    </div>`;

  els.messages.appendChild(wrapper);
  return wrapper;
}

function renderSources(container, sources, retrievalSeconds) {
  if (!sources.length) return;

  const details = document.createElement("details");
  details.className = "sources";
  details.innerHTML = `
    <summary>${sources.length} source${sources.length === 1 ? "" : "s"} · retrieved in ${retrievalSeconds}s</summary>
    <div class="sources-list"></div>`;

  const list = details.querySelector(".sources-list");
  sources.forEach((source) => {
    const card = document.createElement("div");
    card.className = "source-card";
    card.innerHTML = `
      <div class="source-head">
        <span class="source-subject">${escapeHtml(source.subject || "(no subject)")}</span>
        ${source.score !== null ? `<span class="source-score">${source.score}</span>` : ""}
      </div>
      <div class="source-from">${escapeHtml(source.from || "unknown sender")}${source.date ? ` · ${escapeHtml(source.date)}` : ""}</div>
      <div class="source-excerpt">${escapeHtml(source.excerpt)}</div>`;
    list.appendChild(card);
  });

  container.appendChild(details);
}

function setBusy(busy) {
  state.busy = busy;
  els.sendBtn.disabled = busy;
  els.sendBtn.classList.toggle("is-busy", busy);
  els.sendBtn.querySelector(".btn-send-label").textContent = busy ? "Asking" : "Ask";
}

// Static mode: mock streaming with hardcoded answers
async function askStatic(question, userId, answerEl, bodyEl) {
  const startTime = Date.now();

  // "Retrieve" relevant emails
  const { documents, sources } = staticRetrieve(question, userId);
  const retrievalSeconds = ((Date.now() - startTime) / 1000).toFixed(3);

  // Pick an answer based on keywords
  const lowerQ = question.toLowerCase();
  let answer = MOCK_ANSWERS.default;
  for (const [key, value] of Object.entries(MOCK_ANSWERS)) {
    if (lowerQ.includes(key)) {
      answer = value;
      break;
    }
  }

  // If no match, return "I don't know"
  if (sources.length === 0) {
    answer = "I don't know — I couldn't find any relevant emails for this user.";
  }

  // Mock streaming: show cursor and type out answer
  bodyEl.innerHTML = "";
  bodyEl.classList.add("is-streaming");
  const cursor = document.createElement("span");
  cursor.className = "cursor";
  bodyEl.append(document.createTextNode(""), cursor);

  const genStart = Date.now();
  let fullText = "";
  for await (const token of mockStream(answer)) {
    fullText += token;
    bodyEl.firstChild.textContent = fullText;
    scrollToBottom();
  }

  cursor.remove();
  bodyEl.classList.remove("is-streaming");
  bodyEl.innerHTML = renderMarkdown(fullText);

  const generationSeconds = ((Date.now() - genStart) / 1000).toFixed(3);

  // Add metadata
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `
    <span class="badge">retrieval <b>${retrievalSeconds}s</b></span>
    <span class="badge">generation <b>${generationSeconds}s</b></span>
    ${
      sources.length > 0
        ? `<span class="badge ok">grounded in ${sources.length} chunk${sources.length === 1 ? "" : "s"}</span>`
        : `<span class="badge muted">no matching context</span>`
    }`;
  answerEl.querySelector(".msg-main").appendChild(meta);

  if (sources.length > 0) {
    renderSources(answerEl.querySelector(".msg-main"), sources, retrievalSeconds);
  }

  scrollToBottom();
  setBusy(false);
}

async function ask(question) {
  const userId = els.userSelect.value;
  if (!userId) {
    const notice = addMessage("assistant");
    notice.querySelector(".msg-body").innerHTML = renderMarkdown(
      "No data is indexed yet. Load the demo dataset from the sidebar to get started."
    );
    scrollToBottom();
    return;
  }

  const userMsg = addMessage("user");
  userMsg.querySelector(".msg-body").textContent = question;

  const answerEl = addMessage("assistant");
  const bodyEl = answerEl.querySelector(".msg-body");
  bodyEl.innerHTML = `<span class="thinking"><span></span><span></span><span></span></span>`;
  scrollToBottom();
  setBusy(true);

  if (state.staticMode) {
    await askStatic(question, userId, answerEl, bodyEl);
    return;
  }

  // Backend mode continues below

  const url = `/api/query/stream?question=${encodeURIComponent(question)}&user_id=${encodeURIComponent(userId)}`;
  const stream = new EventSource(url);

  let retrievalSeconds = 0;
  let sources = [];
  let text = "";
  let streaming = false;

  const cursor = document.createElement("span");
  cursor.className = "cursor";

  const finish = () => {
    stream.close();
    cursor.remove();
    setBusy(false);
  };

  stream.addEventListener("sources", (event) => {
    const data = JSON.parse(event.data);
    sources = data.sources;
    retrievalSeconds = data.retrieval_seconds;
  });

  stream.addEventListener("token", (event) => {
    const atBottom =
      els.messages.scrollHeight - els.messages.scrollTop - els.messages.clientHeight < 80;

    if (!streaming) {
      streaming = true;
      bodyEl.innerHTML = "";
      bodyEl.classList.add("is-streaming");
      bodyEl.append(document.createTextNode(""), cursor);
    }

    text += JSON.parse(event.data).text;
    bodyEl.firstChild.textContent = text;
    if (atBottom) scrollToBottom();
  });

  stream.addEventListener("done", (event) => {
    const data = JSON.parse(event.data);
    finish();

    bodyEl.classList.remove("is-streaming");
    bodyEl.innerHTML = renderMarkdown(text || "No response.");

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `
      <span class="badge">retrieval <b>${retrievalSeconds}s</b></span>
      <span class="badge">generation <b>${data.generation_seconds}s</b></span>
      ${
        data.grounded
          ? `<span class="badge ok">grounded in ${sources.length} chunk${sources.length === 1 ? "" : "s"}</span>`
          : `<span class="badge muted">no matching context</span>`
      }`;
    answerEl.querySelector(".msg-main").appendChild(meta);

    renderSources(answerEl.querySelector(".msg-main"), sources, retrievalSeconds);
    scrollToBottom();
  });

  stream.addEventListener("error", (event) => {
    finish();
    let message = "Connection to the server was lost.";
    try {
      message = JSON.parse(event.data).message;
    } catch (_) {
      /* transport-level error carries no payload */
    }

    bodyEl.classList.remove("is-streaming");
    bodyEl.innerHTML = text ? renderMarkdown(text) : "<p>Request failed.</p>";

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `<span class="badge error">${escapeHtml(message)}</span>`;
    answerEl.querySelector(".msg-main").appendChild(meta);
    scrollToBottom();
  });
}

// ---------------------------------------------------------------- ingestion

async function loadDemo() {
  els.loadDemoBtn.disabled = true;
  setJobStatus("Loading demo emails…");

  try {
    if (state.staticMode) {
      // Static mode: data already loaded by refreshStatus
      setJobStatus(`Loaded ${state.staticData.length} emails (${state.users.length} users).`, "ok");
      await refreshStatus();
    } else {
      // Backend mode: call API
      const result = await api("/api/ingest/demo", { method: "POST" });
      setJobStatus(`Indexed ${result.emails} emails (${result.chunks} chunks).`, "ok");
      await refreshStatus();
    }
  } catch (err) {
    setJobStatus(err.message, "err");
  } finally {
    els.loadDemoBtn.disabled = false;
  }
}

async function ingestGmail() {
  els.ingestGmailBtn.disabled = true;
  setJobStatus("Starting…");
  try {
    await api("/api/ingest/gmail", {
      method: "POST",
      body: JSON.stringify({ max_results: Number(els.maxResults.value) || 50 }),
    });
    pollIngest();
  } catch (err) {
    setJobStatus(err.message, "err");
    els.ingestGmailBtn.disabled = false;
  }
}

async function pollIngest() {
  const job = await api("/api/ingest/status");

  if (job.running) {
    setJobStatus(job.message || "Working…");
    setTimeout(pollIngest, 1200);
    return;
  }

  if (job.error) {
    setJobStatus(job.error, "err");
  } else if (job.result) {
    setJobStatus(
      `Indexed ${job.result.emails} emails (${job.result.chunks} chunks) for ${job.result.user_id}.`,
      "ok"
    );
  }

  els.ingestGmailBtn.disabled = false;
  await refreshStatus();
}

// ---------------------------------------------------------------- isolation

async function runIsolationTest() {
  const owner = els.userSelect.value;
  const intruder = state.users.find((user) => user !== owner);
  if (!owner || !intruder) return;

  els.isolationBtn.disabled = true;
  els.isolationResult.innerHTML = `<p class="iso-question">Running…</p>`;

  try {
    const question = els.questionInput.value.trim() || SUGGESTIONS[0];

    let result;
    if (state.staticMode) {
      // Static mode: run retrieval locally
      const ownerData = staticRetrieve(question, owner);
      const intruderData = staticRetrieve(question, intruder);

      // Check if intruder got any of owner's data
      const ownerIds = new Set(ownerData.sources.map(s => s.subject + s.from));
      const leaked = intruderData.sources.filter(s => ownerIds.has(s.subject + s.from));

      result = {
        question,
        owner: {
          user_id: owner,
          chunks_retrieved: ownerData.sources.length,
        },
        intruder: {
          user_id: intruder,
          chunks_retrieved: intruderData.sources.length,
          owner_chunks_retrieved: leaked.length,
        },
        isolation_held: leaked.length === 0,
      };
    } else {
      result = await api("/api/isolation-test", {
        method: "POST",
        body: JSON.stringify({ question, owner_id: owner, intruder_id: intruder }),
      });
    }

    const leaked = result.intruder.owner_chunks_retrieved;

    const row = (role, user, count, label, zeroIsGood) => `
      <div class="iso-row">
        <span class="iso-who">
          <span class="iso-role">${role}</span>
          ${escapeHtml(user)}
        </span>
        <span class="iso-count${zeroIsGood && count === 0 ? " zero" : ""}">
          ${count} ${label}
        </span>
      </div>`;

    els.isolationResult.innerHTML = `
      <p class="iso-question">“${escapeHtml(result.question)}”</p>
      ${row("Owner", result.owner.user_id, result.owner.chunks_retrieved, "own chunks", false)}
      ${row("Other user", result.intruder.user_id, leaked, "owner chunks", true)}
      <div class="iso-verdict ${result.isolation_held ? "pass" : "fail"}">
        <svg viewBox="0 0 24 24"><use href="#i-shield" /></svg>
        <span>${
          result.isolation_held
            ? `Isolation held — the other user retrieved ${result.intruder.chunks_retrieved} of their own chunk${result.intruder.chunks_retrieved === 1 ? "" : "s"} and none of the owner's.`
            : `Leak detected — ${leaked} of the owner's chunk${leaked === 1 ? "" : "s"} reached the other user.`
        }</span>
      </div>`;
  } catch (err) {
    els.isolationResult.innerHTML = `<p class="iso-question">Failed: ${escapeHtml(err.message)}</p>`;
  } finally {
    els.isolationBtn.disabled = false;
  }
}

// ---------------------------------------------------------------- demo viewer

function openDemoModal() {
  els.demoModal.classList.add("is-open");
  els.demoModal.setAttribute("aria-hidden", "false");
  els.demoModalBody.innerHTML = `
    <div class="modal-loading">
      <span class="spinner"></span>
      <span>Loading demo data...</span>
    </div>`;
  loadDemoPreview();
}

function closeDemoModal() {
  els.demoModal.classList.remove("is-open");
  els.demoModal.setAttribute("aria-hidden", "true");
}

async function loadDemoPreview() {
  try {
    let data;
    if (state.staticMode) {
      // Build preview from loaded static data
      if (!state.staticData) {
        await loadStaticData();
      }
      const byUser = {};
      for (const email of state.staticData) {
        if (!byUser[email.user_id]) byUser[email.user_id] = [];
        byUser[email.user_id].push({
          subject: email.subject,
          from: email.sender,
          date: email.timestamp,
          preview: email.body.substring(0, 200) + (email.body.length > 200 ? "..." : ""),
        });
      }
      data = {
        total_emails: state.staticData.length,
        users: Object.keys(byUser),
        by_user: byUser,
      };
    } else {
      data = await api("/api/demo/preview");
    }
    renderDemoPreview(data);
  } catch (err) {
    els.demoModalBody.innerHTML = `<p style="color: var(--bad); text-align: center;">Failed to load demo data: ${escapeHtml(err.message)}</p>`;
  }
}

function renderDemoPreview(data) {
  let html = `
    <div class="demo-summary">
      <div class="demo-summary-card">
        <div class="demo-summary-label">Total emails</div>
        <div class="demo-summary-value">${data.total_emails}</div>
      </div>
      <div class="demo-summary-card">
        <div class="demo-summary-label">Users</div>
        <div class="demo-summary-value">${data.users.length}</div>
      </div>
    </div>`;

  for (const user of data.users) {
    const emails = data.by_user[user];
    const initial = (user || "?").trim().charAt(0).toUpperCase() || "?";

    html += `
      <div class="demo-user-section">
        <div class="demo-user-header">
          <span class="avatar avatar-user">${escapeHtml(initial)}</span>
          <span class="demo-user-name">${escapeHtml(user)}</span>
          <span class="demo-user-count">${emails.length} email${emails.length === 1 ? "" : "s"}</span>
        </div>
        <div class="demo-email-list">`;

    for (const email of emails) {
      html += `
        <div class="demo-email-card">
          <div class="demo-email-subject">${escapeHtml(email.subject)}</div>
          <div class="demo-email-meta">
            From: ${escapeHtml(email.from)} · ${new Date(email.date).toLocaleDateString()}
          </div>
          <div class="demo-email-preview">${escapeHtml(email.preview)}</div>
        </div>`;
    }

    html += `
        </div>
      </div>`;
  }

  els.demoModalBody.innerHTML = html;
}

// ---------------------------------------------------------------- wiring

els.composer.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = els.questionInput.value.trim();
  if (!question || state.busy) return;
  els.questionInput.value = "";
  els.questionInput.style.height = "auto";
  ask(question);
});

els.questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    els.composer.requestSubmit();
  }
});

els.questionInput.addEventListener("input", () => {
  els.questionInput.style.height = "auto";
  els.questionInput.style.height = `${els.questionInput.scrollHeight}px`;
});

els.userSelect.addEventListener("change", updateActiveUser);
els.loadDemoBtn.addEventListener("click", loadDemo);
els.viewDemoBtn.addEventListener("click", openDemoModal);
els.demoModalClose.addEventListener("click", closeDemoModal);
els.demoModalOverlay.addEventListener("click", closeDemoModal);
els.ingestGmailBtn.addEventListener("click", ingestGmail);
els.isolationBtn.addEventListener("click", runIsolationTest);

// Close modal on Escape key
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && els.demoModal.classList.contains("is-open")) {
    closeDemoModal();
  }
});

renderSuggestions();
refreshStatus();
