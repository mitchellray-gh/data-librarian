// Data Librarian — UI controller
const $ = (id) => document.getElementById(id);
const messages = $("messages");
const ticker = $("ticker");
const composer = $("composer");
const input = $("input");
const sendBtn = $("send");
const personaSel = $("persona");

const history = []; // {role, content}

function escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function currentPersona() {
  return personaSel ? personaSel.value : "librarian";
}

function personaLabel(p) {
  if (p === "scientist") return "Scientist";
  if (p === "analyst") return "Analyst";
  return "Librarian";
}

function addMessage(role, text, opts = {}) {
  const persona = opts.persona || currentPersona();
  const personaClass = role === "agent" && (persona === "scientist" || persona === "analyst")
    ? ` ${persona}` : "";
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}` + (opts.thinking ? " thinking" : "") + personaClass;
  const who = document.createElement("div");
  who.className = "who";
  who.textContent = role === "user" ? "You" : personaLabel(persona);
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(who);
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
  return { wrap, bubble };
}

function fmtUptime(s) {
  s = Math.floor(s || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${sec}s`;
  return `${sec}s`;
}

function setStatus(elId, label, on) {
  const el = $(elId);
  el.textContent = `${label}: ${on ? "online" : "stub"}`;
  el.classList.toggle("on", !!on);
  el.classList.toggle("off", !on);
}

async function refreshStatusOnce() {
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    setStatus("v-claude", "claude", s.claude_configured);
    setStatus("v-dbx", "databricks", s.databricks_configured);
  } catch (_) { /* swallow */ }
}

async function refreshNotebookOnce() {
  try {
    const r = await fetch("/api/scientist/doc");
    const d = await r.json();
    const doc = $("notebook-doc");
    const meta = $("notebook-meta");
    if (doc) doc.textContent = d.doc && d.doc.trim() ? d.doc : "(no scientist pass yet)";
    if (meta) meta.textContent = `${(d.hypotheses || []).length} hypotheses · ${(d.open_questions || []).length} questions · pass #${d.passes || 0}`;
  } catch (_) { /* swallow */ }
}

async function refreshBriefOnce() {
  try {
    const r = await fetch("/api/analyst/brief");
    const d = await r.json();
    const doc = $("brief-doc");
    const meta = $("brief-meta");
    if (doc) doc.textContent = d.brief && d.brief.trim() ? d.brief : "(no analyst pass yet)";
    if (meta) meta.textContent = `${(d.insights || []).length} insights · ${(d.trends || []).length} trends · pass #${d.passes || 0}`;
  } catch (_) { /* swallow */ }
}

function renderActivity(items) {
  for (const it of items) {
    const li = document.createElement("li");
    if (it.kind === "science" || it.kind === "hypothesis") li.classList.add("sci");
    if (it.kind === "insight") li.classList.add("ana");
    const k = document.createElement("span"); k.className = "kind"; k.textContent = it.kind;
    const m = document.createElement("span"); m.className = "msg"; m.textContent = it.message;
    li.appendChild(k); li.appendChild(m);
    ticker.prepend(li);
    while (ticker.children.length > 60) ticker.removeChild(ticker.lastChild);
  }
}

// SSE — keeps the UI feeling alive
function startStream() {
  const es = new EventSource("/api/stream");
  es.addEventListener("tick", (ev) => {
    try {
      const d = JSON.parse(ev.data);
      $("v-tables").textContent = d.tables_known;
      $("v-passes").textContent = d.passes;
      if ($("v-sci")) $("v-sci").textContent = d.scientist_passes ?? 0;
      if ($("v-ana")) $("v-ana").textContent = d.analyst_passes ?? 0;
      $("v-uptime").textContent = fmtUptime(d.uptime);
      if (d.last_target) $("now-target").textContent = d.last_target;
      if (d.new_activity && d.new_activity.length) {
        renderActivity(d.new_activity);
        // any science/hypothesis activity → refresh the notebook view
        if (d.new_activity.some((it) => it.kind === "science" || it.kind === "hypothesis")) {
          refreshNotebookOnce();
        }
        // any insight activity → refresh the analyst brief view
        if (d.new_activity.some((it) => it.kind === "insight")) {
          refreshBriefOnce();
        }
      }
    } catch (_) { /* ignore */ }
  });
  es.onerror = () => { /* browser auto-reconnects */ };
}

if (personaSel) {
  personaSel.addEventListener("change", () => {
    const p = currentPersona();
    if (p === "scientist") input.placeholder = "Ask the scientist about modeling, features, hypotheses…";
    else if (p === "analyst") input.placeholder = "Ask the analyst about trends, opportunities, business impact…";
    else input.placeholder = "Ask the librarian…";
  });
}

composer.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  const persona = currentPersona();
  addMessage("user", text);
  history.push({ role: "user", content: text });
  input.value = "";
  sendBtn.disabled = true;
  const thinking = addMessage(
    "agent",
    persona === "scientist" ? "interrogating the lab notebook"
      : persona === "analyst" ? "cross-referencing the briefing with the trend feed"
      : "consulting the catalog",
    { thinking: true, persona },
  );
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history, persona }),
    });
    const data = await resp.json();
    thinking.wrap.remove();
    addMessage("agent", data.reply || "(no reply)", { persona: data.persona || persona });
    history.push({ role: "assistant", content: data.reply || "" });
  } catch (e) {
    thinking.wrap.remove();
    addMessage("agent", `Hmm — request failed: ${e}`, { persona });
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

refreshStatusOnce();
setInterval(refreshStatusOnce, 15000);
refreshNotebookOnce();
setInterval(refreshNotebookOnce, 30000);
refreshBriefOnce();
setInterval(refreshBriefOnce, 60000);
startStream();
input.focus();
